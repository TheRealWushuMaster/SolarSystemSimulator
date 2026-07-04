from __future__ import annotations
from datetime import datetime

# The de440t.bsp ephemeris' valid range.
MIN_JULIAN_DATE = 2287184.5
MAX_JULIAN_DATE = 2688976.5


def convert_to_julian_date(
    date: datetime,
    seconds: float | None = None,
    minutes: float | None = None,
    hours: float | None = None,
    days: float | None = None,
    months: float | None = None,
    years: float | None = None,
) -> float:
    year = date.year
    month = date.month
    day = date.day
    hour = date.hour
    minute = date.minute
    second = date.second
    if seconds is not None: second += seconds
    if minutes is not None: minute += minutes
    if hours is not None: hour += hours
    if days is not None: day += days
    if months is not None: month += months
    if years is not None: year += years
    julian_date = 367 * year - (7 * (year + ((month + 9) // 12))) // 4 + (275 * month) // 9 + day + 1721013.5
    julian_date += (hour + (minute / 60) + (second / 3600)) / 24
    if julian_date < MIN_JULIAN_DATE:
        julian_date = MIN_JULIAN_DATE
    elif julian_date > MAX_JULIAN_DATE:
        julian_date = MAX_JULIAN_DATE
    return julian_date
