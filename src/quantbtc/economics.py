from __future__ import annotations

from quantbtc.fees import breakeven_win_prob, fee_per_contract

DEFAULT_PRICES = [0.05 * k for k in range(1, 20)]  # 0.05 .. 0.95


def breakeven_rows(
    prices: list[float], rate: float = 0.07
) -> list[dict[str, float]]:
    return [
        {
            "price": p,
            "fee_per_contract": fee_per_contract(p, rate),
            "breakeven_win_prob": breakeven_win_prob(
                p, fee_per_contract(p, rate)
            ),
        }
        for p in prices
    ]


def render_markdown(rows: list[dict[str, float]]) -> str:
    lines = [
        "# Breakeven table (rate=0.07, per-contract fees)",
        "",
        "| Buy price | Fee/contract | Breakeven win prob |",
        "|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| ${r['price']:.2f} | ${r['fee_per_contract']:.4f} "
            f"| {r['breakeven_win_prob']:.4f} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    from pathlib import Path

    out = Path("docs/breakeven.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text(render_markdown(breakeven_rows(DEFAULT_PRICES)))
    print(f"wrote {out}")
