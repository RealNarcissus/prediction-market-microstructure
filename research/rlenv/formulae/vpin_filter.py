"""VPIN regime filter — 1306.6188 / 1912.10343 binary reframe.

VPIN predicts volatility/toxicity, not direction (s028 RESET). Venue reframe:
use VPIN as entry filter — high VPIN => skip or downsize, not side flip.
Minute_bar runnable; naive-port tag.
"""
