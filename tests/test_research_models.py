from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from lotto649.config import load_config
from lotto649.domain import Draw
from lotto649.models.base import normalize_expected_six
from lotto649.models.factory import build_models
from lotto649.research_features import rich_number_feature_frame
from lotto649.models.v2_statistical import V2StatisticalModel
from lotto649.models.v3_boosting import FEATURES, V3BoostingModel
from lotto649.models.v4_ensemble import V4EnsembleModel


def synthetic_history(count=420):
    out = []
    d = date(2018, 1, 3)
    for i in range(count):
        # Deterministic valid pseudo-history for shape/safety tests only.
        vals = []
        x = (i * 7 + 3) % 49
        step = 0
        while len(vals) < 6:
            n = ((x + step * 11) % 49) + 1
            if n not in vals:
                vals.append(n)
            step += 1
        bonus = next(n for n in range(1, 50) if n not in vals)
        out.append(Draw(d, tuple(vals), bonus))
        d += timedelta(days=3 if d.weekday() == 2 else 4)
    return out


def assert_probability_contract(p):
    assert set(p) == set(range(1, 50))
    assert all(0 < v < 1 for v in p.values())
    assert abs(sum(p.values()) - 6.0) < 1e-6


def test_rich_features_are_finite():
    history = synthetic_history(360)
    f = rich_number_feature_frame(history, history[-1].draw_date + timedelta(days=3))
    assert len(f) == 49
    assert f.drop(columns=["number"]).notna().all().all()


def test_v2_probability_contract():
    history = synthetic_history(360)
    assert_probability_contract(V2StatisticalModel().predict(history, history[-1].draw_date + timedelta(days=3)))


def test_v3_probability_contract():
    history = synthetic_history(390)
    model = V3BoostingModel(training_draws=160, stride=16, min_history=300)
    assert_probability_contract(model.predict(history, history[-1].draw_date + timedelta(days=3)))


def test_v3_frozen_factory_parameters_and_ordered_features():
    cfg = load_config()
    model = build_models(cfg, requested=["v3_boosting"])["v3_boosting"]

    assert (model.training_draws, model.stride, model.min_history) == (280, 14, 300)
    assert FEATURES == [
        "number_scaled",
        "long_freq",
        "freq_10",
        "freq_25",
        "freq_50",
        "freq_100",
        "freq_250",
        "ema_12",
        "ema_35",
        "ema_90",
        "gap",
        "gap_ratio",
        "in_prev",
        "in_prev2",
        "weekday_freq",
        "month_freq",
        "transition_freq",
        "sum_prev_centered",
        "sum_ma5_centered",
        "sum_ma20_centered",
        "sum_slope5",
        "target_weekday",
        "target_month_sin",
        "target_month_cos",
    ]


def test_v3_frozen_estimator_and_probability_blend(monkeypatch):
    learned = np.linspace(0.05, 0.25, 49)
    observed = {}

    class FakeEstimator:
        def __init__(self, **kwargs):
            observed["kwargs"] = kwargs

        def fit(self, X, y):
            observed["fit_shape"] = (X.shape, y.shape)
            return self

        def predict_proba(self, X):
            assert len(X) == 49
            return np.column_stack((1.0 - learned, learned))

    monkeypatch.setattr(
        "lotto649.models.v3_boosting.HistGradientBoostingClassifier",
        FakeEstimator,
    )
    history = synthetic_history(300)
    target = history[-1].draw_date + timedelta(days=3)

    probabilities = V3BoostingModel(
        training_draws=280,
        stride=14,
        min_history=300,
    ).predict(history, target)

    assert observed["kwargs"] == {
        "learning_rate": 0.06,
        "max_iter": 45,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 35,
        "l2_regularization": 2.0,
        "random_state": 649,
    }
    assert observed["fit_shape"][0][1] == len(FEATURES)
    expected = normalize_expected_six(
        {
            number: float(0.72 * learned[number - 1] + 0.28 * (6 / 49))
            for number in range(1, 50)
        }
    )
    assert probabilities == pytest.approx(expected, abs=1e-15, rel=0.0)


@pytest.mark.parametrize(
    "learned",
    [
        np.array([1.0, *([0.0] * 48)]),
        np.array([np.nan, *([0.1] * 48)]),
    ],
)
def test_v3_fails_closed_when_probability_contract_is_violated(
    monkeypatch,
    learned,
):
    class InvalidEstimator:
        def __init__(self, **kwargs):
            pass

        def fit(self, X, y):
            return self

        def predict_proba(self, X):
            return np.column_stack((1.0 - learned, learned))

    monkeypatch.setattr(
        "lotto649.models.v3_boosting.HistGradientBoostingClassifier",
        InvalidEstimator,
    )
    history = synthetic_history(300)
    target = history[-1].draw_date + timedelta(days=3)

    with pytest.raises(RuntimeError, match="probability contract"):
        V3BoostingModel(280, 14, 300).predict(history, target)


def test_v3_rejects_history_at_or_after_target():
    history = synthetic_history(300)

    with pytest.raises(ValueError, match="strictly before target"):
        V3BoostingModel(
            training_draws=280,
            stride=14,
            min_history=300,
        ).predict(history, history[-1].draw_date)


def test_v3_fair_fallback_does_not_fit_and_is_exact(monkeypatch):
    def unexpected_fit(*args, **kwargs):
        raise AssertionError("estimator must not be constructed below minimum history")

    monkeypatch.setattr(
        "lotto649.models.v3_boosting.HistGradientBoostingClassifier",
        unexpected_fit,
    )
    history = synthetic_history(299)
    target = history[-1].draw_date + timedelta(days=3)

    probabilities = V3BoostingModel(
        training_draws=280,
        stride=14,
        min_history=300,
    ).predict(history, target)

    assert probabilities == {number: 6 / 49 for number in range(1, 50)}


def test_v3_cached_uncached_and_bonus_role_invariance():
    history = synthetic_history(300)
    target = history[-1].draw_date + timedelta(days=3)
    changed_bonus = [
        Draw(
            draw.draw_date,
            draw.numbers,
            next(
                number
                for number in range(49, 0, -1)
                if number not in draw.numbers
            ),
        )
        for draw in history
    ]

    cached_model = V3BoostingModel(280, 14, 300)
    first = cached_model.predict(history, target)
    cached = cached_model.predict(history, target)
    uncached = V3BoostingModel(280, 14, 300).predict(history, target)
    changed_bonus_result = V3BoostingModel(280, 14, 300).predict(
        changed_bonus,
        target,
    )

    assert cached == first
    assert uncached == pytest.approx(first, abs=1e-15, rel=0.0)
    assert changed_bonus_result == pytest.approx(first, abs=1e-15, rel=0.0)


def test_v3_cache_does_not_alias_different_histories_with_same_length_and_tail(
    monkeypatch,
):
    class HistorySensitiveEstimator:
        def __init__(self, **kwargs):
            self.marker = None

        def fit(self, X, y):
            self.marker = float(X.iloc[0, 0])
            return self

        def predict_proba(self, X):
            learned = np.linspace(0.05, 0.25, 49) + self.marker / 1000
            return np.column_stack((1.0 - learned, learned))

    def training_frame(self, history):
        marker = history[0].numbers[0]
        frame = pd.DataFrame(
            np.zeros((2, len(FEATURES))),
            columns=FEATURES,
        )
        frame.iloc[0, 0] = marker
        return frame, np.array([0, 1])

    def current_frame(history, target_date):
        frame = pd.DataFrame(
            np.zeros((49, len(FEATURES))),
            columns=FEATURES,
        )
        frame.insert(0, "number", range(1, 50))
        return frame

    monkeypatch.setattr(
        "lotto649.models.v3_boosting.HistGradientBoostingClassifier",
        HistorySensitiveEstimator,
    )
    monkeypatch.setattr(V3BoostingModel, "_training_frame", training_frame)
    monkeypatch.setattr(
        "lotto649.models.v3_boosting.rich_number_feature_frame",
        current_frame,
    )
    first_history = synthetic_history(300)
    alternate_first = Draw(
        first_history[0].draw_date,
        (2, 10, 18, 26, 34, 42),
        1,
    )
    second_history = [alternate_first, *first_history[1:]]
    target = first_history[-1].draw_date + timedelta(days=3)
    model = V3BoostingModel(280, 14, 300)

    first = model.predict(first_history, target)
    second = model.predict(second_history, target)
    fresh_second = V3BoostingModel(280, 14, 300).predict(second_history, target)

    assert first != fresh_second
    assert second == fresh_second


def test_v4_probability_contract():
    history = synthetic_history(360)
    a = V2StatisticalModel()
    b = V2StatisticalModel()
    model = V4EnsembleModel([(a, 0.4), (b, 0.6)])
    assert_probability_contract(model.predict(history, history[-1].draw_date + timedelta(days=3)))
