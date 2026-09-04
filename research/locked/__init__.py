"""Locked evaluation harness for the autoresearch loop.

NOTHING in research/locked/ may be modified by the loop. The guard
(research/guard.py) verifies the hash of this package before every run.
Changing folds, labels, metrics, or the sealed-holdout boundary here is a
human-only operation, done deliberately and committed with a new hash.
"""
