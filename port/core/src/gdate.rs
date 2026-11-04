//! The game's date type (`app.GregorianDate`, docs/value-helpers.md): a
//! Julian Day number in a float, months counted from 0.
//! scripts/reference/gdate.py has the same arithmetic and checks it against
//! Python's own calendar.

const EPOCH: f64 = 1721118.5;

/// Story day 1: 23 November 1982 (docs/days-csv-format.md).
pub const DAY1: f64 = 2445296.5;

/// `GregorianDate.int`: toward zero.
fn to_int(f: f64) -> i64 {
    f.trunc() as i64
}

/// (year, month counting from 0, day).
pub fn split(jd: f64) -> (i64, i64, i64) {
    let d = jd - EPOCH;
    let z = d.floor() as i64;
    let a = z as f64 - 0.25;
    let century = (a / 36524.25).floor() as i64;
    let g = century - (century as f64 * 0.25).floor() as i64;
    let mut year = ((g as f64 + a) / 365.25).floor() as i64;
    let doy = g - (year as f64 * 365.25).floor() as i64 + z;
    let mut m = to_int((doy * 5 + 456) as f64 / 153.0);
    let before = to_int((m * 153 - 457) as f64 / 5.0);
    if m > 12 {
        year += 1;
        m -= 12;
    }
    let day = to_int((d - z as f64) + (doy - before) as f64);
    (year, m - 1, day)
}

/// `GregorianDate.format`: `%y` the year mod 100 without a leading zero,
/// `%Y` the year, `%m` and `%d` two digits.
pub fn format(jd: f64, pattern: &str) -> String {
    let (year, month0, day) = split(jd);
    pattern
        .replace("%y", &(year.rem_euclid(100)).to_string())
        .replace("%Y", &year.to_string())
        .replace("%m", &format!("{:02}", month0 + 1))
        .replace("%d", &format!("{day:02}"))
}

/// `Lang.formatVerboseDate` (docs/text-xml-format.md): `date_verbose` with
/// `month_<n>` (n from 1), `day_<d>` and the year, from the texts given.
pub fn verbose(jd: f64, text: impl Fn(&str) -> Option<String>) -> Result<String, String> {
    let (year, month0, day) = split(jd);
    let get = |id: String| text(&id).ok_or_else(|| format!("text {id} is missing"));
    Ok(get("date_verbose".into())?
        .replace("$month", &get(format!("month_{}", month0 + 1))?)
        .replace("$day", &get(format!("day_{day}"))?)
        .replace("$year", &year.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn day_one_is_the_23rd_of_november_1982() {
        assert_eq!(split(DAY1), (1982, 10, 23));
        assert_eq!(format(DAY1, "%y.%m.%d"), "82.11.23");
        assert_eq!(format(DAY1, "%d.%m.%Y"), "23.11.1982");
        // Later days, across a month and a year end.
        assert_eq!(split(DAY1 + 8.0), (1982, 11, 1));
        assert_eq!(split(DAY1 + 39.0), (1983, 0, 1));
    }

    #[test]
    fn the_long_date_fills_its_three_parts() {
        // Made-up texts: the game's own stay in the pack (CLAUDE.md, rule 1).
        let texts = |id: &str| match id {
            "date_verbose" => Some("[$day] of [$month] in [$year]".to_string()),
            "month_11" => Some("M11".to_string()),
            "day_23" => Some("D23".to_string()),
            _ => None,
        };
        assert_eq!(verbose(DAY1, texts).unwrap(), "[D23] of [M11] in [1982]");
        assert!(verbose(DAY1 + 1.0, texts).is_err());
    }
}
