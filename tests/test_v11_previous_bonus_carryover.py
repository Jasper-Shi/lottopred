from dataclasses import FrozenInstanceError, replace
from datetime import date
import math

import pytest

import lotto649.models.v11_previous_bonus_carryover as v11
from lotto649.domain import Draw
from lotto649.models.v11_previous_bonus_carryover import (
    CANDIDATE_MODEL_NAME,
    CONTROL_MODEL_NAME,
    MODEL_VERSION,
    V1BaseSnapshot,
    V11BetaFit,
    V11Forecast,
    V11ForecastBundle,
    V11Transition,
    anchor_log_gains,
    fit_beta,
    forecast_v11_bundle,
    make_transition,
    preflight_v11_model,
    select_pseudo_bonus,
    tilt_probabilities,
)


def _oracle_transitions() -> tuple[V11Transition, ...]:
    responses = (1, 0, 0, 1)
    transition_dates = (
        (date(2019, 5, 15), date(2019, 5, 18)),
        (date(2019, 5, 18), date(2019, 5, 22)),
        (date(2019, 5, 22), date(2019, 5, 25)),
        (date(2019, 5, 25), date(2019, 5, 29)),
    )
    return tuple(
        V11Transition(
            source_date=source_date,
            destination_date=destination_date,
            base_prefix_sha256=f"{index:x}" * 64,
            candidate_anchor=index,
            control_anchor=index + 10,
            candidate_q=6.0 / 49.0,
            control_q=6.0 / 49.0,
            candidate_y=response,
            control_y=response,
        )
        for index, ((source_date, destination_date), response) in enumerate(
            zip(transition_dates, responses),
            start=1,
        )
    )


def _uniform_base(
    *,
    target_date: date = date(2020, 1, 4),
    history_through: date = date(2020, 1, 1),
) -> V1BaseSnapshot:
    ranking = tuple(range(1, 50))
    return V1BaseSnapshot(
        target_date=target_date,
        history_draws=1,
        history_through=history_through,
        strict_prefix_sha256="a" * 64,
        probabilities=(6.0 / 49.0,) * 49,
        ranking=ranking,
        top6=ranking[:6],
        top12=ranking[:12],
        top18=ranking[:18],
        final6=ranking[:6],
    )


def test_v11_public_identity_is_the_frozen_registration() -> None:
    assert MODEL_VERSION == "v11.0.0"
    assert CANDIDATE_MODEL_NAME == "v11_previous_bonus_carryover"
    assert CONTROL_MODEL_NAME == "v11_previous_bonus_carryover_pseudo_bonus_control"


def test_v1_base_snapshot_is_immutable_and_locks_the_full_forecast() -> None:
    probabilities = (6.0 / 49.0,) * 49
    ranking = tuple(range(1, 50))

    base = V1BaseSnapshot(
        target_date=date(2020, 1, 4),
        history_draws=1,
        history_through=date(2020, 1, 1),
        strict_prefix_sha256="a" * 64,
        probabilities=probabilities,
        ranking=ranking,
        top6=ranking[:6],
        top12=ranking[:12],
        top18=ranking[:18],
        final6=ranking[:6],
    )

    assert base.probabilities is probabilities
    assert math.fsum(base.probabilities) == pytest.approx(6.0, abs=1.0e-12)
    with pytest.raises(FrozenInstanceError):
        base.history_draws = 2  # type: ignore[misc]


def test_v1_base_snapshot_rejects_a_non_strict_history_boundary() -> None:
    ranking = tuple(range(1, 50))

    with pytest.raises(ValueError, match="strictly before"):
        V1BaseSnapshot(
            target_date=date(2020, 1, 4),
            history_draws=1,
            history_through=date(2020, 1, 4),
            strict_prefix_sha256="a" * 64,
            probabilities=(6.0 / 49.0,) * 49,
            ranking=ranking,
            top6=ranking[:6],
            top12=ranking[:12],
            top18=ranking[:18],
            final6=ranking[:6],
        )


def test_v1_base_snapshot_rejects_invalid_probabilities_or_rankings() -> None:
    ranking = tuple(range(1, 50))
    base = V1BaseSnapshot(
        target_date=date(2020, 1, 4),
        history_draws=1,
        history_through=date(2020, 1, 1),
        strict_prefix_sha256="a" * 64,
        probabilities=(6.0 / 49.0,) * 49,
        ranking=ranking,
        top6=ranking[:6],
        top12=ranking[:12],
        top18=ranking[:18],
        final6=ranking[:6],
    )

    with pytest.raises(ValueError, match="49 probabilities"):
        replace(base, probabilities=base.probabilities[:-1])
    with pytest.raises(ValueError, match="open interval"):
        replace(base, probabilities=(0.0, *base.probabilities[1:]))
    with pytest.raises(ValueError, match="sum to six"):
        replace(base, probabilities=(0.1,) * 49)
    with pytest.raises(ValueError, match="ranking"):
        replace(base, ranking=tuple(reversed(ranking)))
    with pytest.raises(ValueError, match="prefix"):
        replace(base, top12=ranking[:11])
    with pytest.raises(ValueError, match="final6"):
        replace(base, final6=tuple(reversed(ranking[:6])))


def test_v11_map_beta_matches_the_registered_literal_oracle() -> None:
    fit = fit_beta(_oracle_transitions(), "candidate")

    assert fit == V11BetaFit(
        transition_count=4,
        beta=float.fromhex("0x1.e35d1e3820caep-1"),
    )
    assert fit.beta == 0.9440698092952482


def test_v11_beta_score_uses_one_fsum_with_negative_beta_first() -> None:
    calls: list[tuple[float, ...]] = []
    original_fsum = math.fsum

    def traced_fsum(values: object) -> float:
        materialized = tuple(values)  # type: ignore[arg-type]
        calls.append(materialized)
        return original_fsum(materialized)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(v11.math, "fsum", traced_fsum)
        fit = fit_beta(_oracle_transitions(), "candidate")

    assert fit.beta.hex() == "0x1.e35d1e3820caep-1"
    assert len(calls) == 259
    assert calls[0] == (
        -0.0,
        43.0 / 49.0,
        -6.0 / 49.0,
        -6.0 / 49.0,
        43.0 / 49.0,
    )
    assert all(len(call) == 5 for call in calls)


def test_v11_solver_takes_equality_upper_branch_and_never_exits_early() -> None:
    transition = V11Transition(
        source_date=date(2019, 5, 15),
        destination_date=date(2019, 5, 18),
        base_prefix_sha256="a" * 64,
        candidate_anchor=1,
        control_anchor=2,
        candidate_q=float.fromhex("0x1.793f300166212p-2"),
        control_q=0.5,
        candidate_y=1,
        control_y=0,
    )
    calls: list[tuple[float, ...]] = []
    original_fsum = math.fsum

    def traced_fsum(values: object) -> float:
        materialized = tuple(values)  # type: ignore[arg-type]
        calls.append(materialized)
        return original_fsum(materialized)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(v11.math, "fsum", traced_fsum)
        fit_beta((transition,), "candidate")

    midpoint_betas = tuple(-call[0] for call in calls[3:])
    assert len(midpoint_betas) == 256
    assert midpoint_betas[:7] == tuple(65.0 / 2**power for power in range(1, 8))
    assert original_fsum(calls[9]) == 0.0
    assert midpoint_betas[7].hex() == "0x1.0400000000000p-2"


def test_v11_empty_and_balanced_prefixes_return_positive_zero() -> None:
    first, second = _oracle_transitions()[:2]
    balanced = (
        replace(first, candidate_q=0.5, candidate_y=1),
        replace(second, candidate_q=0.5, candidate_y=0),
    )

    empty_fit = fit_beta((), "candidate")
    balanced_fit = fit_beta(balanced, "candidate")

    assert empty_fit == V11BetaFit(transition_count=0, beta=0.0)
    assert empty_fit.beta.hex() == "0x0.0p+0"
    assert balanced_fit == V11BetaFit(transition_count=2, beta=0.0)
    assert balanced_fit.beta.hex() == "0x0.0p+0"


def test_v11_pseudo_bonus_matches_the_registered_full_digest_oracle() -> None:
    source = Draw(date(2020, 1, 1), (1, 2, 3, 5, 6, 7), 4)

    selected, digest = select_pseudo_bonus(source)

    assert selected == 4
    assert digest == (
        "1052da1f3ebf9c1bfe2f06998f13ebc812c01dd08fd9b0b21cc20fd35d0840c8"
    )


def test_v11_transition_uses_one_shared_original_v1_base_for_both_roles() -> None:
    source = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    destination = Draw(date(2020, 1, 4), (7, 8, 9, 10, 11, 12), 13)
    base = _uniform_base()

    transition = make_transition(base, source, destination)

    assert transition == V11Transition(
        source_date=source.draw_date,
        destination_date=destination.draw_date,
        base_prefix_sha256=base.strict_prefix_sha256,
        candidate_anchor=7,
        control_anchor=4,
        candidate_q=6.0 / 49.0,
        control_q=6.0 / 49.0,
        candidate_y=1,
        control_y=0,
    )


def test_v11_capacity_transfer_matches_both_registered_hex_oracles() -> None:
    base = (0.2, *((29.0 / 240.0,) * 48))

    positive = tilt_probabilities(base, anchor=1, beta=math.log(2.0))
    negative = tilt_probabilities(base, anchor=1, beta=-math.log(2.0))

    assert positive[0].hex() == "0x1.5555555555555p-2"
    assert {value.hex() for value in positive[1:]} == {"0x1.e38e38e38e38fp-4"}
    assert math.fsum(positive) == 6.000000000000001
    assert negative[0].hex() == "0x1.c71c71c71c71ep-4"
    assert {value.hex() for value in negative[1:]} == {"0x1.f684bda12f685p-4"}
    assert math.fsum(negative) == 6.0


def test_v11_positive_transfer_uses_the_registered_literal_binary64_order() -> None:
    base = (0.2, 0.1, *((5.7 / 47.0,) * 47))

    positive = tilt_probabilities(base, anchor=1, beta=math.log(2.0))

    assert positive[1].hex() == "0x1.902f149902f16p-4"


def test_v11_transfer_fails_closed_if_rounding_changes_nonanchor_order() -> None:
    lower = float.fromhex("0x1.eb851eb851eb8p-4")
    higher = float.fromhex("0x1.eb851eb851eb9p-4")
    remainder = (6.0 - 0.2 - lower - higher) / 46.0
    base = (0.2, lower, higher, *((remainder,) * 46))
    assert math.nextafter(lower, math.inf) == higher

    with pytest.raises(RuntimeError, match="changed non-anchor ranking"):
        tilt_probabilities(base, anchor=1, beta=math.log(2.0))


def test_v11_feature_off_paths_return_the_original_tuple_bit_for_bit() -> None:
    base = (0.2, *((29.0 / 240.0,) * 48))

    beta_zero = tilt_probabilities(base, anchor=1, beta=0.0)
    rounded_identity = tilt_probabilities(
        base,
        anchor=1,
        beta=math.nextafter(0.0, math.inf),
    )

    assert beta_zero is base
    assert rounded_identity is base
    assert tuple(value.hex() for value in beta_zero) == tuple(
        value.hex() for value in base
    )


def test_v11_bundle_shares_one_base_and_freezes_both_complete_forecasts() -> None:
    base = _uniform_base()
    source = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)

    bundle = forecast_v11_bundle(base, (), source)

    assert isinstance(bundle, V11ForecastBundle)
    assert bundle.base is base
    assert isinstance(bundle.candidate, V11Forecast)
    assert bundle.candidate.model_name == CANDIDATE_MODEL_NAME
    assert bundle.control.model_name == CONTROL_MODEL_NAME
    assert bundle.candidate.anchor_kind == "published_bonus"
    assert bundle.control.anchor_kind == "deterministic_pseudo_bonus"
    assert bundle.candidate.anchor == 7
    assert bundle.control.anchor == 4
    assert bundle.candidate.anchor_source_date == source.draw_date
    assert bundle.control.anchor_source_date == source.draw_date
    assert bundle.candidate.beta.hex() == "0x0.0p+0"
    assert bundle.control.beta.hex() == "0x0.0p+0"
    assert bundle.candidate.q_b == bundle.candidate.r_b == 6.0 / 49.0
    assert bundle.control.q_b == bundle.control.r_b == 6.0 / 49.0
    assert bundle.candidate.probabilities is base.probabilities
    assert bundle.control.probabilities is base.probabilities
    assert bundle.candidate.ranking == base.ranking
    assert bundle.control.final6 == base.final6


@pytest.mark.parametrize(
    ("r_anchor_hex", "response", "expected_log_g_hex", "expected_d_hex"),
    [
        (
            "0x1.5555555555555p-2",
            0,
            "-0x1.1970f2bd42617p-2",
            "-0x1.7565011e49675p-3",
        ),
        (
            "0x1.5555555555555p-2",
            1,
            "0x1.005eee78d91a2p+0",
            "0x1.058aefa811451p-1",
        ),
        (
            "0x1.c71c71c71c71ep-4",
            0,
            "0x1.a4a5cac16aef2p-7",
            "0x1.af8e8210a4152p-4",
        ),
        (
            "0x1.c71c71c71c71ep-4",
            1,
            "-0x1.8dfb931f71680p-4",
            "-0x1.2cf25fad8f1c3p-1",
        ),
    ],
)
def test_v11_anchor_log_gains_use_only_the_observed_branch(
    r_anchor_hex: str,
    response: int,
    expected_log_g_hex: str,
    expected_d_hex: str,
) -> None:
    q_anchor = 0.2
    r_anchor = float.fromhex(r_anchor_hex)

    log_g, relative_v1 = anchor_log_gains(q_anchor, r_anchor, response)

    assert log_g.hex() == expected_log_g_hex
    assert relative_v1.hex() == expected_d_hex


def test_v11_transition_rejects_invalid_chronology_or_values() -> None:
    transition = _oracle_transitions()[0]

    invalid_changes = (
        {"source_date": date(2019, 5, 14)},
        {"destination_date": transition.source_date},
        {"base_prefix_sha256": "abc"},
        {"candidate_anchor": 0},
        {"control_anchor": 50},
        {"candidate_q": 0.0},
        {"control_q": math.inf},
        {"candidate_y": True},
        {"control_y": 2},
    )
    for changes in invalid_changes:
        with pytest.raises(ValueError):
            replace(transition, **changes)


def test_v11_fit_rejects_unknown_roles_and_nonchronological_rows() -> None:
    transitions = _oracle_transitions()
    duplicate_destination = (
        replace(transitions[0], destination_date=transitions[1].destination_date),
        transitions[1],
    )

    with pytest.raises(ValueError, match="role"):
        fit_beta((), "result_chosen_rescue")
    with pytest.raises(ValueError, match="destination-date order"):
        fit_beta(tuple(reversed(transitions)), "candidate")
    with pytest.raises(ValueError, match="destination-date order"):
        fit_beta(duplicate_destination, "control")


def test_v11_bundle_rejects_a_transition_beyond_the_visible_prefix() -> None:
    base = _uniform_base()
    source = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)
    hidden_future = V11Transition(
        source_date=date(2020, 1, 1),
        destination_date=date(2020, 1, 3),
        base_prefix_sha256="b" * 64,
        candidate_anchor=7,
        control_anchor=4,
        candidate_q=6.0 / 49.0,
        control_q=6.0 / 49.0,
        candidate_y=1,
        control_y=0,
    )

    with pytest.raises(ValueError, match="visible strict prefix"):
        forecast_v11_bundle(base, (hidden_future,), source)


def test_v11_bundle_matches_the_registered_tilted_probability_oracle() -> None:
    base = _uniform_base()
    source = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)

    bundle = forecast_v11_bundle(base, _oracle_transitions(), source)

    assert bundle.candidate.beta.hex() == "0x1.e35d1e3820caep-1"
    assert bundle.control.beta.hex() == "0x1.e35d1e3820caep-1"
    assert bundle.candidate.r_b.hex() == "0x1.0e5170e3ef9a9p-2"
    assert bundle.control.r_b.hex() == "0x1.0e5170e3ef9a9p-2"
    for forecast in (bundle.candidate, bundle.control):
        assert len(forecast.probabilities) == 49
        assert all(0.0 < probability < 1.0 for probability in forecast.probabilities)
        assert math.fsum(forecast.probabilities) == pytest.approx(
            6.0,
            rel=0.0,
            abs=1.0e-12,
        )
        assert forecast.top6 == forecast.ranking[:6]
        assert forecast.top12 == forecast.ranking[:12]
        assert forecast.top18 == forecast.ranking[:18]
        assert forecast.final6 == tuple(sorted(forecast.top6))


def test_v1_base_snapshot_rejects_mutable_or_unbound_metadata() -> None:
    base = _uniform_base()

    invalid_changes = (
        {"history_draws": -1},
        {"history_draws": 0},
        {"history_through": None},
        {"strict_prefix_sha256": "A" * 64},
        {"strict_prefix_sha256": "a" * 63},
        {"probabilities": list(base.probabilities)},
    )
    for changes in invalid_changes:
        with pytest.raises(ValueError):
            replace(base, **changes)


def test_v11_transfer_preserves_nonanchor_order_and_changes_one_rank_slot() -> None:
    nonanchor = 29.0 / 240.0
    base = (
        0.2,
        nonanchor + 0.01,
        nonanchor - 0.01,
        nonanchor + 0.005,
        nonanchor - 0.005,
        *((nonanchor,) * 44),
    )
    base_ranking = tuple(
        sorted(range(1, 50), key=lambda number: (-base[number - 1], number))
    )
    base_nonanchor_order = tuple(number for number in base_ranking if number != 1)

    for beta in (math.log(2.0), -math.log(2.0)):
        tilted = tilt_probabilities(base, anchor=1, beta=beta)
        ranking = tuple(
            sorted(
                range(1, 50),
                key=lambda number: (-tilted[number - 1], number),
            )
        )
        assert tuple(number for number in ranking if number != 1) == (
            base_nonanchor_order
        )
        for size in (6, 12, 18):
            assert len(set(base_ranking[:size]) - set(ranking[:size])) <= 1
            assert len(set(ranking[:size]) - set(base_ranking[:size])) <= 1


def test_v11_preflight_verifies_every_registered_synthetic_oracle() -> None:
    assert preflight_v11_model() is None
    assert preflight_v11_model() is None


def test_v11_pseudo_bonus_digest_tie_uses_label_and_allows_identity() -> None:
    class EqualDigest:
        def digest(self) -> bytes:
            return bytes(32)

    source = Draw(date(2020, 1, 1), (2, 3, 4, 5, 6, 7), 1)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(v11, "sha256", lambda _payload: EqualDigest())
        selected, digest = select_pseudo_bonus(source)

    assert selected == source.bonus == 1
    assert digest == "00" * 32
