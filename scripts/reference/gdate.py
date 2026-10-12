"""Reference implementation of the game's date type, app.GregorianDate.

A date is a Julian Day number held in a float. Months count from 0. See
docs/value-helpers.md.

Run as a script to check it against Python's own calendar for every day
from 1800 to 2200:

    python -I scripts/reference/gdate.py
"""

import datetime
import math

# Days before each month, counting the year from 1 March (index 3 = March,
# index 14 = February of the next calendar year). Indexes 0 to 2 are unused.
M_LOOKUP = [0, -60, -30, 0, 31, 61, 92, 122, 153, 184, 214, 245, 275, 306, 337]

EPOCH = 1721118.5


def to_int(f: float) -> int:
    """GregorianDate.int: toward zero."""
    return math.floor(f) if f >= 0 else math.ceil(f)


def from_ymd(year: int, month0: int, day: int) -> float:
    m = month0 + 1
    if m < 3:
        m = month0 + 13
        year -= 1
    y = float(year)
    total = float(int(math.floor(y * 0.25)))
    total += M_LOOKUP[m] + day + 365 * year
    total -= int(math.floor(y / 100.0))
    total += int(math.floor(y / 400.0))
    return total + EPOCH


def split(jd: float) -> tuple[int, int, int]:
    """(year, month counting from 0, day)."""
    d = jd - EPOCH
    z = int(math.floor(d))
    a = z - 0.25
    century = int(math.floor(a / 36524.25))
    g = century - int(math.floor(century * 0.25))
    year = int(math.floor((g + a) / 365.25))
    doy = g - int(math.floor(year * 365.25)) + z
    m = to_int((doy * 5 + 456) / 153.0)
    before = to_int((m * 153 - 457) / 5.0)
    if m > 12:
        year += 1
        m -= 12
    day = to_int((d - z) + (doy - before))
    return year, m - 1, day


def after_days(jd: float, days: float) -> float:
    return jd + days


def after_years(jd: float, years: float) -> float:
    return jd + years * 365.242199


def format_date(jd: float, pattern: str) -> str:
    year, month0, day = split(jd)
    text = pattern.replace("%y", str(int(math.floor(year % 100))))
    text = text.replace("%Y", str(year))
    text = text.replace("%m", str(month0 + 1).rjust(2, "0"))
    return text.replace("%d", str(day).rjust(2, "0"))


def main() -> None:
    checked = 0
    day = datetime.date(1800, 1, 1)
    end = datetime.date(2200, 12, 31)
    while day <= end:
        jd = from_ymd(day.year, day.month - 1, day.day)
        expected = day.toordinal() + 1721424.5
        assert jd == expected, (day, jd, expected)
        for fraction in (0.0, 0.3, 0.999):
            assert split(jd + fraction) == (day.year, day.month - 1, day.day), (day, fraction)
        checked += 1
        day += datetime.timedelta(days=1)
    first = from_ymd(1982, 10, 23)
    print(f"checked {checked} days: from_ymd and split agree with Python's calendar")
    print(f"23 Nov 1982 = Julian Day {first}; formats: "
          f"{format_date(first, '%y.%m.%d')} {format_date(first, '%Y.%m.%d')} "
          f"{format_date(first, '%d.%m.%y')} {format_date(first, '%m.%d.%Y')}")


if __name__ == "__main__":
    main()
