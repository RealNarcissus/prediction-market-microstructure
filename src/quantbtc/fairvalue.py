"""Asian digital fair value for Jupiter Up/Down epochs.

Jupiter resolves on the Chainlink TWAP over the window vs the window-start
price (docs/RECON.md). The fair probability of "Up" mid-epoch is therefore
an ASIAN digital: P( A_done*t_e + A_future*(T-t_e) >= K*T ), where A_done is
the realized running average and A_future the average of the remaining path.

Under driftless GBM the continuous arithmetic average over remaining time
tau has exact first two moments (zero drift):
    M1 = S
    M2 = 2 S^2 (exp(sigma^2 tau) - 1 - sigma^2 tau) / (sigma^4 tau^2)
Levy's moment matching then approximates A_future as lognormal.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


def _cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


@dataclass(frozen=True)
class AsianDigital:
    strike: float     # K: window-start price (Jupiter's reference)
    total_s: float    # T: full window length in seconds
    sigma: float      # per-sqrt(second) vol of the underlying

    def prob_up(
        self, spot: float, elapsed_s: float, running_avg: float
    ) -> float:
        """P(window TWAP >= strike) with `elapsed_s` gone and the running
        average so far at `running_avg`."""
        T, K = self.total_s, self.strike
        tau = max(T - elapsed_s, 0.0)

        if tau <= 0.0:  # window complete: the average is known
            return 1.0 if running_avg >= K else 0.0
        need = K * T - running_avg * elapsed_s
        k_star = need / tau  # future average required to clear the strike
        if k_star <= 0.0:
            return 1.0

        s2t = self.sigma * self.sigma * tau
        if s2t <= 1e-18:
            return 1.0 if spot >= k_star else 0.0

        # CLT form for the arithmetic average (exact small-x limit of Levy;
        # numerically stable at our tenors where sigma^2*tau ~ 1e-6):
        #   A_future ~ N(S, S^2 sigma^2 tau / 3) under driftless GBM
        sd_A = spot * self.sigma * math.sqrt(tau / 3.0)
        if sd_A <= 1e-15:
            return 1.0 if spot >= k_star else 0.0
        return _cdf((spot - k_star) / sd_A)
