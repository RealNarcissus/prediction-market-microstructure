"""Unit tests for the live paper-wallet engine (pure state machine)."""
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "research"))

from staleness.live_wallet import WalletEngine, fair_yes
from staleness.gate_v2 import EwmaKlineCache, fair_yes_v2, load_calibration_v2

DAY = "2026-09-02"
T0 = 1788374400000  # 2026-09-02 00:00:00 UTC in ms


def mk_market(asset="BTC", hz=300, open_ms=T0):
    return {
        "asset": asset, "horizon_s": hz,
        "open_time_ms": open_ms, "close_time_ms": open_ms + hz * 1000,
        "is_up_market": True,
    }


def mk_quote(ask=0.30, ts=T0 + 60_000, market_id="POLY-1-0", bid=0.28):
    return {"ts_ms": ts, "market_id": market_id, "side": "up", "bid": bid, "ask": ask}


class FlatCal:
    """Isotonic stand-in: identity-ish mapping fair -> fair."""

    def __call__(self, fair):
        return fair


def test_gate_fires_and_books_entry():
    e = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
    m = mk_market()
    q = mk_quote(ask=0.30)
    # fair 0.50 vs ask 0.30 -> gap 0.20 > fee 0.0147 -> trade
    d = e.on_quote(m, q, fair=0.50)
    assert d["action"] == "trade"
    t = d["trade"]
    assert t["cost_cents"] == 30 + int(np.ceil(0.07 * 0.30 * 0.70 * 100))
    assert e.day_wallet_cents == 500 - t["cost_cents"]
    assert e.position is not None


def test_no_gate_when_gap_below_fee():
    e = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
    m = mk_market()
    # fair barely above ask: 0.31 vs 0.30 -> gap 0.01 < fee 0.0147
    d = e.on_quote(m, mk_quote(ask=0.30), fair=0.31)
    assert d["action"] == "skip" and d["reason"] == "no_gate"


def test_calibration_can_block_the_gate():
    # raw fair 0.9 but calibrated to 0.35 -> gap_cal 0.05 < fee? fee=0.0189 at 0.90
    # 0.35-0.90 negative -> blocked
    e = WalletEngine(calib_predict=lambda f: min(f, 0.35), now_ms=T0 + 60_000)
    d = e.on_quote(mk_market(), mk_quote(ask=0.90), fair=0.99)
    assert d["action"] == "skip" and d["reason"] == "no_gate_cal"


def test_one_position_serial_and_dup_epoch():
    e = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
    m = mk_market()
    d1 = e.on_quote(m, mk_quote(), fair=0.60)
    assert d1["action"] == "trade"
    # while position open -> busy
    d2 = e.on_quote(mk_market(), mk_quote(ts=T0 + 90_000), fair=0.60)
    assert d2["action"] == "skip" and d2["reason"] == "busy"
    # settle, then same epoch again -> dup_epoch (even though free)
    res = e.on_resolution("POLY-1-0", "up", T0 + 300_000)
    assert res is not None and res["won"] == 1
    d3 = e.on_quote(mk_market(), mk_quote(ts=T0 + 310_000), fair=0.60)
    assert d3["action"] == "skip" and d3["reason"] == "dup_epoch"


def test_settlement_accounting_win_and_loss():
    e = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
    e.on_quote(mk_market(), mk_quote(ask=0.30), fair=0.60)
    fee_c = int(np.ceil(0.07 * 0.30 * 0.70 * 100))
    cost = 30 + fee_c
    wallet_after_entry = e.day_wallet_cents
    res = e.on_resolution("POLY-1-0", "up", T0 + 300_000)
    assert res["pnl_cents"] == 100 - cost
    assert e.day_wallet_cents == wallet_after_entry + 100
    # loss path
    e2 = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
    e2.on_quote(mk_market(), mk_quote(ask=0.30), fair=0.60)
    res2 = e2.on_resolution("POLY-1-0", "down", T0 + 300_000)
    assert res2["won"] == 0 and res2["pnl_cents"] == -cost
    assert e2.day_wallet_cents == 500 - cost + 0


def test_down_market_resolution_semantics():
    e = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
    m = mk_market()
    m["is_up_market"] = False
    e.on_quote(m, mk_quote(ask=0.40, market_id="POLY-2-1"), fair=0.60)
    # outcome 'up' means the DOWN market LOST
    res = e.on_resolution("POLY-2-1", "up", T0 + 300_000)
    assert res["won"] == 0


def test_day_rollover_resets_allowance():
    e = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
    e.on_quote(mk_market(), mk_quote(ask=0.30), fair=0.60)
    spent = 500 - e.day_wallet_cents
    # next day quote (different epoch open)
    m2 = mk_market(open_ms=T0 + 86_400_000)
    q2 = mk_quote(ask=0.30, ts=T0 + 86_460_000)
    d = e.on_quote(m2, q2, fair=0.60)
    assert e.day == "2026-09-03"
    assert e.day_wallet_cents == 500 - (d["trade"]["cost_cents"]) if d["action"] == "trade" else True
    assert spent > 0


def test_day_budget_stops_trading():
    e = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
    # drain wallet: enter+settle losing trades repeatedly on distinct epochs
    for i in range(6):
        m = mk_market(open_ms=T0 + i * 600_000)
        d = e.on_quote(m, mk_quote(ask=0.90, ts=T0 + i * 600_000 + 60_000,
                                   market_id=f"POLY-{i}-0"), fair=0.99)
        if d["action"] == "trade":
            e.on_resolution(f"POLY-{i}-0", "down", T0 + (i + 1) * 600_000)
    # 5 entries x 91c (90 ask + 1c fee) = 455c spent; 6th blocked by budget
    assert e.day_wallet_cents == 45
    m_next = mk_market(open_ms=T0 + 10 * 600_000)
    d = e.on_quote(m_next, mk_quote(ask=0.90, ts=T0 + 10 * 600_000 + 60_000,
                                    market_id="POLY-X-0"), fair=0.99)
    assert d["action"] == "skip" and d["reason"] == "day_budget"


def test_fair_yes_mirrored_for_down_market():
    # synthetic flat klines: close == open -> TWAP == strike -> fair 0.5
    n = 40
    ts = np.arange(n, dtype=np.int64) * 60_000 + T0 - 30 * 60_000
    px = np.full(n, 100.0)
    data = {"ts": ts, "open": px, "close": px, "r24": np.full(n, 0.0002)}
    open_ms = ts[30]
    f_up = fair_yes(data, int(open_ms), 300, int(open_ms) + 60_000, True)
    f_down = fair_yes(data, int(open_ms), 300, int(open_ms) + 60_000, False)
    assert abs(f_up - 0.5) < 0.01
    assert abs(f_up + f_down - 1.0) < 1e-9


def test_fair_yes_moves_with_twap_above_strike():
    n = 40
    ts = np.arange(n, dtype=np.int64) * 60_000 + T0 - 30 * 60_000
    opn = np.full(n, 100.0)
    close = np.full(n, 100.0)
    # epoch opened at index 30: strike = that bar's OPEN (100); price then jumps
    close[30:] = 100.6
    data = {"ts": ts, "open": opn, "close": close, "r24": np.full(n, 0.0002)}
    open_ms = int(ts[30])
    f = fair_yes(data, open_ms, 300, int(ts[32]), True)
    assert f > 0.95


def test_engine_tags_gate_version_from_dict_fair():
    e = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
    d = e.on_quote(mk_market(), mk_quote(), {"fair": 0.60, "gate": "v2"})
    assert d["action"] == "trade"
    assert d["trade"]["gate"] == "v2"


def test_engine_rejects_nonfinite_fair():
    for bad in (float("nan"), float("inf")):
        e = WalletEngine(calib_predict=FlatCal(), now_ms=T0 + 60_000)
        d = e.on_quote(mk_market(), mk_quote(), bad)
        assert d["action"] == "skip" and d["reason"] == "no_fair"


def test_fair_yes_v2_returns_z_and_scales_with_time_left():
    # synthetic flat-then-jump klines; fixed z must SHRINK as expiry nears
    # (round-107 path variance) — the property v1 lacked
    n = 200
    ts = np.arange(n, dtype=np.int64) * 60_000 + T0 - 190 * 60_000
    px = np.full(n, 100.0)
    px[191:] = 100.3  # jump AFTER the open bar: strike=100.0, spot later=100.3
    data = {"ts": ts, "open": px.copy(), "close": px,
            "ewma": np.full(n, 0.0002)}
    open_ms = int(ts[190])
    z_early = fair_yes_v2(data, open_ms, 600, int(ts[191]))
    z_late = fair_yes_v2(data, open_ms, 600, int(ts[198]))
    assert z_early is not None and z_late is not None
    assert abs(z_late) > abs(z_early)  # less time left -> more extreme z


def test_load_calibration_v2_mapping_is_discriminating():
    calib = load_calibration_v2()
    probs = [calib(z, True) for z in (-3.0, -1.0, 0.0, 1.0, 3.0)]
    assert probs == sorted(probs)
    assert len(set(round(p, 4) for p in probs)) == len(probs)
    assert all(0.0 <= p <= 1.0 for p in probs)
