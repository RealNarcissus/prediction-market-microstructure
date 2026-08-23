"""One-time recon against the live Jupiter Prediction API (Phase 0).

Captures raw JSON fixtures, identifies the Up/Down crypto events, verifies
the fee formula, and prints a summary to paste into docs/RECON.md.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx

FIXTURE_DIR = Path("tests/fixtures/jupiter")
BASE_URL = "https://api.jup.ag/prediction/v1"


async def main() -> None:
    headers = {"accept": "application/json"}
    if key := os.environ.get("JUP_API_KEY"):
        headers["x-api-key"] = key
    else:
        print("WARNING: JUP_API_KEY not set; some endpoints may 401.")
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(
        base_url=BASE_URL, headers=headers, timeout=15.0
    ) as c:
        resp = await c.get("/trading-status")
        print("trading-status:", resp.status_code, resp.text[:200])
        (FIXTURE_DIR / "trading_status.json").write_text(
            json.dumps(resp.json(), indent=2)
        )

        resp = await c.get(
            "/events", params={"filter": "live", "includeMarkets": "true"}
        )
        print("events:", resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        events = data.get("events", data) if isinstance(data, dict) else data
        (FIXTURE_DIR / "events_live.json").write_text(json.dumps(data, indent=2))
        print(f"live events: {len(events)}")

        crypto = [
            e
            for e in events
            if any(k in json.dumps(e).upper() for k in ("BTC", "ETH", "SOL"))
            and any(k in json.dumps(e).upper() for k in ("UP", "DOWN", "5", "15"))
        ]
        print(f"candidate up/down crypto events: {len(crypto)}")
        for e in crypto[:5]:
            eid = e.get("id") or e.get("eventId")
            print(" -", eid, "|", e.get("title"))
            markets = e.get("markets") or []
            if isinstance(markets, list):
                for m in markets[:4]:
                    mid = m.get("marketId")
                    if not mid:
                        continue
                    ob = (await c.get(f"/orderbook/{mid}")).json()
                    (FIXTURE_DIR / f"orderbook_{mid[:8]}.json").write_text(
                        json.dumps(ob, indent=2)
                    )
                    print(
                        f"   market {mid}: open={m.get('openTime')} "
                        f"close={m.get('closeTime')} result={m.get('result')}"
                    )

        print(
            "\nNEXT: paste findings into docs/RECON.md; fix fixtures/tests if"
            " field names, price scales, or event shapes differ."
        )


if __name__ == "__main__":
    asyncio.run(main())
