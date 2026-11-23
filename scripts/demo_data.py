"""The demo's data, in one place.

scripts/demo.py sends exactly these values to StudioNet, and
tests/test_runbook.py replays them offline, so the demo on the explorer and the
demo the tests check cannot drift apart.

Two maintenance plans, each against a real page of this repository served from
raw.githubusercontent.com:

  0  a quickstart guide whose own last-updated line is recent. Three windows;
     the maintainer collects the first, is refused a second check in the same
     window, collects the second, and lets the third lapse. After the schedule
     ends the third installment goes back to the funder.
  1  the same guide, an old copy whose own last-updated line is from the
     previous year. The maintainer checks twice in the window and is not paid
     either time, is refused a third, and after the schedule ends the whole fee
     returns to the funder.

The contract reads the date off the page; the age is the contract's own
arithmetic against its own clock, so the two plans differ only in what the
page says about itself.
"""

GEN = 10 ** 18

RAW = "https://raw.githubusercontent.com/meitipro/stalecheck/master/demo/pages"
FRESH_URL = f"{RAW}/guide_fresh.md"
STALE_URL = f"{RAW}/guide_stale.md"

TITLE_0 = "Quickstart guide, kept current"
TITLE_1 = "Quickstart guide, an old copy"
MAX_AGE = 30                       # days
INTERVAL = 600                     # seconds per window
N_0 = 3
N_1 = 2
FEE_0 = 9 * GEN // 100             # 0.03 GEN an installment
FEE_1 = 6 * GEN // 100             # 0.03 GEN an installment

# The date of the day the demo is run, and the day the replay pretends it is
# when there is no record yet. It must be within MAX_AGE days of the date on
# the fresh page and further than MAX_AGE from the date on the stale one.
DEMO_START = "2026-11-23T18:00:00Z"

# The demo, step by step, exactly as scripts/demo.py sends it and
# tests/test_runbook.py replays it: (who, method, arguments, value, expected,
# label, tags...). A tag "at_window:P:W" waits until window W of plan P has
# begun; "after_close:P" waits until plan P's schedule has ended.
STEPS = [
    ("funder", "open", ("maintainer", TITLE_0, FRESH_URL, MAX_AGE, N_0, INTERVAL), FEE_0, "ok",
     "plan 0 opened: a guide with a recent date, 3 windows, 0.09 GEN"),
    ("funder", "open", ("maintainer", TITLE_1, STALE_URL, MAX_AGE, N_1, INTERVAL), FEE_1, "ok",
     "plan 1 opened: an old copy of the guide, 2 windows, 0.06 GEN"),

    ("stranger", "check", (0,), 0, "refused", "a check from someone who is not the maintainer"),
    ("maintainer", "check", (0,), 0, "ok", "plan 0, window 0: the date is read off the page and is fresh: paid"),
    ("maintainer", "check", (0,), 0, "refused", "a second check in a window that is already paid"),
    ("maintainer", "check", (1,), 0, "ok", "plan 1, window 0: the date is read off the page and is stale: not paid"),
    ("maintainer", "check", (1,), 0, "ok", "plan 1, window 0: a second try, still stale: not paid"),
    ("maintainer", "check", (1,), 0, "refused", "a third check in a window that has used its two"),

    ("maintainer", "check", (0,), 0, "ok", "plan 0, window 1: fresh again: paid", "at_window:0:1"),
    ("stranger", "close", (0,), 0, "refused", "closing plan 0 while its schedule is still running"),
    ("maintainer", "check", (0,), 0, "refused", "a check after plan 0's schedule ended (window 2 was never claimed)",
     "after_close:0"),
    ("stranger", "close", (0,), 0, "ok", "plan 0 closed: the unclaimed third installment returns to the funder",
     "after_close:0"),
    ("stranger", "close", (1,), 0, "ok", "plan 1 closed: nothing was ever fresh, the whole fee returns to the funder",
     "after_close:1"),
]

# What each ok check is expected to come back with, in order: the date the
# validators read off the page.
EXPECTED_READINGS = ["2026-11-20", "2025-03-02", "2025-03-02", "2026-11-20"]
EXPECTED_VERDICTS = ["fresh", "stale", "stale", "fresh"]
