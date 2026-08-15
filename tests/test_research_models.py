from datetime import date, timedelta

from lotto649.domain import Draw
from lotto649.research_features import rich_number_feature_frame
from lotto649.models.v2_statistical import V2StatisticalModel
from lotto649.models.v3_boosting import V3BoostingModel
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


def test_v4_probability_contract():
    history = synthetic_history(360)
    a = V2StatisticalModel()
    b = V2StatisticalModel()
    model = V4EnsembleModel([(a, 0.4), (b, 0.6)])
    assert_probability_contract(model.predict(history, history[-1].draw_date + timedelta(days=3)))
