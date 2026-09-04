"""Hawkes self-excitation — 2312.16190 adapted (deferred).

Lambda(t)=mu + sum alpha*beta*exp(-beta(t-ti)). Needs tick history.
Status: DEFERRED until aggTrade >=14d. When runnable, use Hawkes intensity
as logit shift (excitation => contrarian skip) not price target.
"""
# Deferred — _is_deferred() in loop_formula.py handles gating.
