"""REINFORCE with learned linear baseline over a small tanh MLP policy.

Hand-derived backprop (numpy only, deterministic under seed):
  logits = W2 @ tanh(W1 @ s + b1) + b2
  pi     = softmax(logits)                     actions: 0=skip,1=up,2=down
  loss   = -log pi[a] * A   +  c_v * (v - R)^2 -  c_e * H(pi)
where A = R - v(s) is the advantage against the linear value baseline.
"""
from __future__ import annotations

import numpy as np


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


class PolicyAgent:
    def __init__(
        self,
        state_dim: int,
        hidden: int = 24,
        lr: float = 3e-3,
        value_lr: float = 3e-2,
        entropy_coef: float = 0.01,
        seed: int = 0,
    ):
        rng = np.random.default_rng(seed)
        self.rng = rng
        self.W1 = rng.normal(0, 0.3, size=(hidden, state_dim))
        self.b1 = np.zeros(hidden)
        self.W2 = rng.normal(0, 0.3, size=(3, hidden))
        self.b2 = np.zeros(3)
        self.v_w = np.zeros(state_dim + 1)  # linear value baseline (+bias)
        self.lr, self.value_lr, self.entropy_coef = lr, value_lr, entropy_coef

    def _forward(self, s: np.ndarray):
        h_pre = self.W1 @ s + self.b1
        h = np.tanh(h_pre)
        logits = self.W2 @ h + self.b2
        return h, h_pre, logits

    def act(self, s: np.ndarray, greedy: bool = False) -> int:
        _, _, logits = self._forward(np.asarray(s, dtype=float))
        if greedy:
            return int(np.argmax(logits))
        p = softmax(logits)
        return int(self.rng.choice(3, p=p))

    def value(self, s: np.ndarray) -> float:
        return float(self.v_w[: len(s)] @ s + self.v_w[-1])

    def update_episode(self, trajectory: list[dict]) -> dict:
        """trajectory: list of dicts with keys s, a, R (terminal reward on the
        entry step; 0 on skip steps). One gradient step per step."""
        stats = {"loss": 0.0, "entropy": 0.0}
        for t in trajectory:
            s, a, R = np.asarray(t["s"], dtype=float), t["a"], t["R"]
            h, h_pre, logits = self._forward(s)
            probs = softmax(logits)

            v_hat = float(self.v_w[: len(s)] @ s + self.v_w[-1])
            adv = R - v_hat

            # policy gradients
            dlogits = -probs.copy()
            dlogits[a] += 1.0
            dlogits *= adv                      # REINFORCE term
            ent = -(probs * np.log(probs + 1e-12)).sum()
            d_ent = probs * (-np.log(probs + 1e-12) - 1.0) * (-self.entropy_coef)
            dlogits -= d_ent                    # maximize entropy => minus coef
            loss_pi = -np.log(probs[a] + 1e-12) * adv

            # backprop through MLP
            dW2 = np.outer(dlogits, h)
            db2 = dlogits
            dh = self.W2.T @ dlogits
            dh_pre = dh * (1 - np.tanh(h_pre) ** 2)
            dW1 = np.outer(dh_pre, s)
            db1 = dh_pre

            self.W1 -= self.lr * dW1
            self.b1 -= self.lr * db1
            self.W2 -= self.lr * dW2
            self.b2 -= self.lr * db2

            # value regression toward realized R
            dv = v_hat - R
            self.v_w[: len(s)] -= self.value_lr * dv * s
            self.v_w[-1] -= self.value_lr * dv

            stats["loss"] += float(loss_pi)
            stats["entropy"] += float(ent)
        n = max(1, len(trajectory))
        return {"pi_loss": stats["loss"] / n, "entropy": stats["entropy"] / n}

    def update_fullinfo(self, steps: list[dict]) -> dict:
        """All-actions policy gradient (full-information contextual bandit).

        Each step exposes the EX-POST reward of every action:
          r_skip = 0, r_up, r_down (computable once the window settles).
        Gradient: dlogits[a] += probs[a] * (r_a - mean_r - v(s)) for all a,
        which pushes probability mass toward actions that beat the
        state-value expectation — the optimal-stopping contrast that
        single-sample REINFORCE lacks.
        """
        stats = {"loss": 0.0}
        for t in steps:
            s = np.asarray(t["s"], dtype=float)
            r = np.array([t["r_skip"], t["r_up"], t["r_down"]])
            r = np.clip(r, -1.5, 1.5)  # dollar rewards are bounded; clip kills
            # any residual explosion from extreme fair-value entries
            h, h_pre, logits = self._forward(s)
            probs = softmax(logits)
            v_hat = float(self.v_w[: len(s)] @ s + self.v_w[-1])
            adv = np.clip(r - (r.mean() + v_hat), -1.5, 1.5)
            dlogits = probs * adv
            nrm = float(np.abs(dlogits).max())
            if nrm > 1.0:
                dlogits /= nrm  # gradient clipping
            dW2 = np.outer(dlogits, h)
            db2 = dlogits
            dh = self.W2.T @ dlogits
            dh_pre = dh * (1 - np.tanh(h_pre) ** 2)
            self.W1 -= self.lr * np.outer(dh_pre, s)
            self.b1 -= self.lr * dh_pre
            self.W2 -= self.lr * dW2
            self.b2 -= self.lr * db2
            # value regresses toward expected reward under current policy
            ev = float(probs @ r)
            dv = np.clip(ev - v_hat, -1.5, 1.5)
            self.v_w[: len(s)] -= self.value_lr * dv * s / max(1e-6, np.abs(s).max())
            self.v_w[-1] -= self.value_lr * dv
            stats["loss"] += float(-(probs @ np.log(probs + 1e-12) * r).sum())
        return {"pi_loss": stats["loss"]}

    def snapshot(self) -> dict:
        return {k: v.copy() for k, v in self.__dict__.items()
                if isinstance(v, np.ndarray)}
