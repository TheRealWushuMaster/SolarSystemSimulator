"""Config shared between the desktop app (app_ursina/) and the web backend
(server/). Renderer-only tuning lives in app_ursina/config.py instead."""

from __future__ import annotations

EPHEMERIS_FILE = "de440t.bsp"

# Points per orbit line, used both by the desktop app's orbit-line rendering
# and the server's /api/orbits endpoint.
ORBIT_SAMPLES: int = 180

# (label, seconds) pairs cycled through with the up/down keys / time-step UI.
simulation_steps: list[tuple[str, int]] = [
    ("1 second", 1),
    ("10 seconds", 10),
    ("1 minute", 60),
    ("15 minutes", 900),
    ("30 minutes", 1800),
    ("1 hour", 3600),
    ("12 hours", 43200),
    ("1 day", 86400),
    ("1 week", 604800),
    ("1 month", 2592000),
    ("1 year", 31536000),
]
