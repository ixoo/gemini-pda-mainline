# SPDX-License-Identifier: MIT
"""Coordinator-reviewed execution boundary; no environment or CLI override."""
def require_enabled():
    raise ValueError('eMMC execution disabled pending final coordinator review')
