"""Entry-forced RL agent: binary choice (Up or Down), no skip option.

The policy network outputs 2 logits instead of 3. At every decision point
the agent MUST commit to a direction. This isolates directional skill from
timing/abstention skill.

Uses the same all-actions contextual-bandit trainer but with only two
actions and no skip baseline needed (both actions are entries).
"""
from __future__ import annotations

import numpy as np


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


class ForcedBinaryAgent:
    """2-action policy (up=0, down=1) with all-actions contextual bandit."""

    def __init__(self, state_dim: int, hidden: int = 24,
                 lr: float = 3e-4, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.rng = rng
        self.W1 = rng.normal(0, 0.3, size=(hidden, state_dim))
        self.b1 = np.zeros(hidden)
        self.W2 = rng.normal(0, 0.3, size=(2, hidden))  # 2 outputs: up, down
        self.b2 = np.zeros(2)
        self.lr = lr

    def _forward(self, s: np.ndarray):
        h_pre = self.W1 @ s + self.b1
        h = np.tanh(h_pre)
        logits = self.W2 @ h + self.b2
        return h, h_pre, logits

    def act(self, s: np.ndarray) -> int:
        """Always returns 0 (up) or 1 (down). Never skips."""
        _, _, logits = self._forward(np.asarray(s, dtype=float))
        return int(np.argmax(logits))

    def act_stochastic(self, s: np.ndarray) -> int:
        _, _, logits = self._forward(np.asarray(s, dtype=float))
        probs = self._softmax(logits)
        return int(self.rng.choice(2, p=probs))

    @staticmethod
    def _softmax(z):
        z = z - z.max()
        e = np.exp(z)
        return e / e.sum()

    def update_fullinfo_binary(self, steps: list[dict]) -> dict:
        """steps: [{s, r_up, r_down}] — ex-post rewards for both sides.
        All-actions gradient with per-episode group normalization."""
        cache = []
        for t in steps:
            s = np.asarray(t["s"], dtype=float)
            r = np.clip(np.array([t["r_up"], t["r_down"]]), -1.5, 1.5)
            h, h_pre, logits = self._forward(s)
            probs = self._softmax(logits)
            adv = r - r.mean()  # group-normalized within this step
            cache.append((s, h, h_pre, probs, adv))

        # episode-level normalization
        if len(cache) > 1:
            flat = np.concatenate([c[4] for c in cache])
            mu, sd = flat.mean(), flat.std()
            if sd > 1e-12:
                cache = [(s, h, hp, p, np.clip((a - mu) / (sd + 1e-8), -3, 3))
                         for (s, h, hp, p, a) in cache]

        for s, h, hp, probs, adv in cache:
            dlogits = probs * adv
            nrm = float(np.abs(dlogits).max())
            if nrm > 1.0:
                dlogits /= nrm
            dW2 = np.outer(dlogits, h)
            db2 = dlogits
            dh = self.W2.T @ dlogits
            dh_pre = dh * (1 - np.tanh(hp) ** 2)
            self.W1 -= self.lr * np.outer(dh_pre, s)
            self.b1 -= self.lr * dh_pre
            self.W2 -= self.lr * dW2
            self.b2 -= self.lr * db2
        return {"n_steps": len(steps)}

    def snapshot(self) -> dict:
        return {k: v.copy() for k, v in self.__dict__.items() if isinstance(v, np.ndarray)}

    def load_snapshot(self, snap: dict) -> None:
        for k, v in snap.items():
            setattr(self, k, v)
