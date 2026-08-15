from datetime import date

from lotto649.live import next_draw_date
from lotto649.notification import should_alert


def test_next_draw_date():
    assert next_draw_date(date(2026, 8, 12)) == date(2026, 8, 15)
    assert next_draw_date(date(2026, 8, 15)) == date(2026, 8, 19)


def test_notification_thresholds():
    cfg = {"notifications": {"min_final_hits": 4, "min_top12_hits": 5}}
    assert should_alert({"final_6_hits": 4, "top_12_hits": 2}, cfg)
    assert should_alert({"final_6_hits": 1, "top_12_hits": 5}, cfg)
    assert not should_alert({"final_6_hits": 3, "top_12_hits": 4}, cfg)
