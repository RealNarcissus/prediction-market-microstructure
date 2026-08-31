"""OFI proxy — Cont-Kukanov-Stoikov 1011.6402 adapted for binary venue.

Spot: ΔP = λ·OFI, OFI = Σ e_n (best bid/ask size changes).
Binary: logit(p) shift by standardized ofi_proxy = imb * range/mean_range.
Weight-aware sweep w∈{0,0.5,1.0} via loop_formula._ofi_augmented_predictions.
Depth-gated true OFI is DEFERRED; this minute_bar proxy is naive-port tagged.
"""
from rlenv.loop_formula import _ofi_augmented_predictions as augmented  # re-export
