"""Quarter-Hour 10s VWAP at boundary — 2607.09426 epoch-limited reframe.

Paper's 10s VWAP at 00/15/30/45 with 4-12h horizon suits FUTURE swing, not
5m/15m epochs. Epoch-limited reframe: 10s VWAP at epoch open (from aggTrade)
as staleness feature. Candidate — minute_bar partial from aggTrade.
"""
# Candidate — requires aggTrade at boundaries; runnable as filter when available.
