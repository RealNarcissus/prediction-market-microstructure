from quantbtc.backfill import missing_hours

HOUR_MS = 3600 * 1000
BOUNDARY = 1784772000000  # exactly 495770 * HOUR_MS (a true hour boundary)


def test_missing_hours_simple_range():
    have = {BOUNDARY, BOUNDARY + HOUR_MS}  # hours 0 and 1 present
    missing = missing_hours(BOUNDARY, BOUNDARY + 3 * HOUR_MS, have)
    assert missing == [BOUNDARY + 2 * HOUR_MS]


def test_missing_hours_empty_have():
    assert missing_hours(BOUNDARY, BOUNDARY + 2 * HOUR_MS, set()) == [
        BOUNDARY,
        BOUNDARY + HOUR_MS,
    ]


def test_missing_hours_excludes_before_start():
    # floor() bucket below start must not be reported
    missing = missing_hours(BOUNDARY + 1000, BOUNDARY + 2 * HOUR_MS, set())
    assert missing == [BOUNDARY + HOUR_MS]
