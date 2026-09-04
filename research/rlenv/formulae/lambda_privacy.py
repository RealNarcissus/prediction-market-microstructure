"""Privacy-noise lambda — 2605.15746 adapted for binary venue.

Theory: Kyle lambda under privacy noise.
Proxy: lam = ofi_proxy / r24, standardized on train, logit blend.
Weight-aware sweep w∈{0,0.5,1.0} via loop_formula._lambda_augmented_predictions.
"""
from rlenv.loop_formula import _lambda_augmented_predictions as augmented  # re-export
