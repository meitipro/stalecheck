"""Mutation pass: break every defence on purpose, confirm a test notices.

Passing tests prove nothing on their own. Each entry below is a small edit to
the contract that removes a defence. The suite must fail for every one of them,
and this script records WHICH test caught it, so the table in the README is
measured rather than claimed.

    python scripts/mutate.py            # run them all, print what caught what
    python scripts/mutate.py --md       # emit the markdown table for the README

An escaping mutation is a finding, not a nuisance: either a missing test, or a
later defence strict enough that an earlier test can no longer fail. The script
exits non-zero if anything escapes, and refuses to run on a red baseline.

Three rules keep the harness honest:

  * the unmutated suite must be green before anything is mutated;
  * a find string that is missing, or matches more than once, is a failure of
    the harness, never a skip, so refactoring cannot quietly turn a row off;
  * scripts/lift.py runs inside every mutated copy before the suite, so the lib
    parity test can never stand in for the behavioural test a mutation deserves.
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).absolute().parent.parent
TARGET = "stalecheck.py"

FENCE = '    return str(raw).replace("<", "(").replace(">", ")").replace("[", "(").replace("]", ")")'

MUTATIONS = [
    # -- reading a date
    ("a date that is not a calendar date is read", '    if len(s) != 10 or s[4] != "-" or s[7] != "-":\n        return 0', "    if False:\n        return 0"),
    ("a date with letters in it is read", '    if not all(ch in "0123456789" for ch in digits):\n        return 0', "    if False:\n        return 0"),
    ("an impossible date is read", "    except ValueError:\n        return 0", "    except ValueError:\n        return 1"),
    ("the word none is not a sound reading", "    return reading == NONE or parse_day(reading) > 0", "    return parse_day(reading) > 0"),
    ("anything is a sound reading", "    return reading == NONE or parse_day(reading) > 0", "    return True"),
    ("prose around a date is tolerated", '    return s if parse_day(s) > 0 else ""', "    return s"),
    ("a model's answer that is not a string is read", '    if not isinstance(raw, str):\n        return ""\n', ""),

    # -- reading the model
    ("an unusable answer is not retried",
     "    for _ in range(2):\n        raw = gl.nondet.exec_prompt(", "    for _ in range(1):\n        raw = gl.nondet.exec_prompt("),
    ("an unusable answer is read as none",
     '    raise gl.vm.UserError(f"{ERR_LLM} the model gave neither a date nor none")', '    return NONE, ""'),
    ("an answer that is not an object crashes the block",
     "        if isinstance(raw, dict):\n            reading", "        if True:\n            reading"),

    # -- the fetch
    ("a fetch error is swallowed and read as an empty page",
     '    except Exception:\n        raise gl.vm.UserError(f"{ERR_FETCH} the page could not be read")', '    except Exception:\n        text = ""'),
    ("a short or empty page is still read", "    if len(body.strip()) < MIN_PAGE:", "    if False:"),
    ("the page is never actually fetched", "        text = gl.nondet.web.render(url)", "        text = url"),
    ("a long page is shown by its start only", "    return page[:half] + \"\\n...\\n\" + page[-half:]", "    return page[:MAX_SHOWN]"),
    ("a long page is shown whole", "    if len(page) <= MAX_SHOWN:\n        return page", "    if True:\n        return page"),

    # -- the validator
    ("the validator agrees with an error", "                return False\n            theirs", "                return True\n            theirs"),
    ("the validator skips the structural check",
     "            if not reading_sound(proposed):\n                return False", "            if False:\n                return False"),
    ("the validator agrees with anything sound", '            return stalecheck_agrees(mine["as_of"], proposed)', "            return True"),
    ("the validator agrees when its own fetch or model fails",
     "            except gl.vm.UserError:\n                return False", "            except gl.vm.UserError:\n                return True"),
    ("agreement ignores soundness",
     "    return reading_sound(mine) and reading_sound(theirs) and str(mine) == str(theirs)", "    return str(mine) == str(theirs)"),
    ("agreement is not exact",
     "    return reading_sound(mine) and reading_sound(theirs) and str(mine) == str(theirs)",
     "    return reading_sound(mine) and reading_sound(theirs) and str(mine)[:7] == str(theirs)[:7]"),

    # -- the arithmetic
    ("the contract's day is taken from the wrong clock", "    return int(secs) // 86400 + datetime.date(1970, 1, 1).toordinal()", "    return int(secs) // 86400 + datetime.date(1970, 1, 1).toordinal() + 1"),
    ("the age limit is exclusive", "    if age > max_age:\n        return STALE, age", "    if age >= max_age:\n        return STALE, age"),
    ("a stale page is fresh", "    if age > max_age:\n        return STALE, age", "    if age > max_age * 1000:\n        return STALE, age"),
    ("a page from the future is fresh", "    if age < -SLACK_DAYS:\n        return FUTURE, age", "    if age < -SLACK_DAYS * 10000:\n        return FUTURE, age"),
    ("no slack for a time zone ahead", "    if age < -SLACK_DAYS:\n        return FUTURE, age", "    if age < 0:\n        return FUTURE, age"),
    ("an undated page is fresh", "    if reading == NONE:\n        return UNDATED, 0", "    if reading == NONE:\n        return FRESH, 0"),
    ("the window is counted wrongly", "    return (int(now) - int(start)) // int(interval)", "    return (int(now) - int(start)) // int(interval) + 1"),
    ("the last installment does not take the remainder",
     "    if int(k) == int(n) - 1:\n        return int(total) - base * (int(n) - 1)\n    return base", "    return base"),
    ("the agreed reading is not checked again",
     "        if not reading_sound(reading):\n            raise", "        if False:\n            raise"),

    # -- paying
    ("every check pays, fresh or not", "        pay = installment(int(p.total), int(p.installments), w) if verdict == FRESH else 0",
     "        pay = installment(int(p.total), int(p.installments), w)"),
    ("a fresh page pays nothing", "        pay = installment(int(p.total), int(p.installments), w) if verdict == FRESH else 0", "        pay = 0"),
    ("a fresh page pays the first installment whatever the window",
     "        pay = installment(int(p.total), int(p.installments), w) if verdict == FRESH else 0",
     "        pay = installment(int(p.total), int(p.installments), 0) if verdict == FRESH else 0"),
    ("a paid window is not marked paid", "            self.paid_win[key] = u256(1)", "            pass"),
    ("the paid count is not raised", "            p.n_paid = u256(int(p.n_paid) + 1)", "            pass"),
    ("the paid total is not raised", "            p.paid_total = u256(int(p.paid_total) + pay)", "            pass"),
    ("the checks of a window are not counted", "        self.tries_win[key] = u256(int(self.tries_win.get(key, u256(0))) + 1)", "        pass"),
    ("a check is not linked to its plan", "            self.checks[int(p.last_check)].next = u256(cid)", "            pass"),
    ("the check count is not raised", "        p.n_checks = u256(int(p.n_checks) + 1)", "        pass"),
    ("every check is recorded as fresh", "age=u256(age if age > 0 else 0), verdict=verdict,", "age=u256(age if age > 0 else 0), verdict=FRESH,"),
    ("a leader's reason is stored as sent", "why=sanitise_reason(res.get(\"because\", \"\")),", "why=str(res.get(\"because\", \"\")),"),
    ("a leader's reason is stored uncapped", '    return " ".join("".join(out).split())[:limit]', '    return " ".join("".join(out).split())'),

    # -- the free refusals
    ("anyone may check", "        if gl.message.sender_address != p.maintainer:\n            raise", "        if False:\n            raise"),
    ("a check is taken on a closed plan",
     '        if str(p.status) != OPEN:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this plan is {p.status}; only an open one takes a check")',
     '        if False:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this plan is {p.status}; only an open one takes a check")'),
    ("a check is taken after the schedule", "        if now >= int(p.ends_at):\n            raise gl.vm.UserError(f\"{ERR_EXPECTED} the schedule ended", "        if False:\n            raise gl.vm.UserError(f\"{ERR_EXPECTED} the schedule ended"),
    ("a window pays twice", "        if int(self.paid_win.get(key, u256(0))) > 0:", "        if False:"),
    ("a window takes any number of checks", "        if int(self.tries_win.get(key, u256(0))) >= MAX_TRIES:", "        if False:"),
    ("a window takes one check too many", "MAX_TRIES = 2 ", "MAX_TRIES = 3 "),

    # -- close
    ("a plan closes while the schedule runs", "        if now < int(p.ends_at):\n            raise", "        if False:\n            raise"),
    ("a closed plan closes again",
     '        if str(p.status) != OPEN:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this plan is {p.status}; nothing to close")',
     '        if False:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this plan is {p.status}; nothing to close")'),
    ("close returns the whole fee even if installments were paid", "        rest = int(p.total) - int(p.paid_total)", "        rest = int(p.total)"),
    ("close returns less than the unpaid rest", "        rest = int(p.total) - int(p.paid_total)", "        rest = int(p.total) - int(p.paid_total) - 1"),
    ("the return is not recorded", "        p.returned = u256(rest)", "        pass"),
    ("the closing time is not recorded", "        p.closed_at = u256(now)", "        pass"),

    # -- money
    ("a fee below one wei an installment is accepted", "        if total < n or total > MAX_AMOUNT:", "        if total > MAX_AMOUNT:"),
    ("the held counter is not raised", "        self.held = u256(int(self.held) + total)", "        pass"),
    ("a payout beyond what is held is sent", "        if amount > int(self.held):", "        if False:"),
    ("the held counter is not lowered", "        self.held = u256(int(self.held) - amount)", "        pass"),

    # -- opening
    ("the funder may name itself as the maintainer", "        if who == gl.message.sender_address:\n            raise", "        if False:\n            raise"),
    ("the maintainer need not look like an address", "        if not looks_like_address(maintainer):", "        if False:"),
    ("the page is not checked", "        if not bounded(link, MIN_URL, MAX_URL) or not is_http_url(link):", "        if False:"),
    ("a page with angle brackets is accepted", '    if rest == "" or any(ch in s for ch in " <>\\"\'`\\\\"):', '    if rest == "":'),
    ("the allowed age is unbounded", "        if age < MIN_AGE_DAYS or age > MAX_AGE_DAYS:", "        if False:"),
    ("the installments are unbounded", "        if n < MIN_INSTALLMENTS or n > MAX_INSTALLMENTS:", "        if False:"),
    ("the window is unbounded", "        if step < MIN_INTERVAL or step > MAX_INTERVAL:", "        if False:"),
    ("the schedule does not end where it should", "ends_at=u256(now + n * step)", "ends_at=u256(now + step)"),
    ("the title is unbounded", "        if not bounded(t, MIN_TITLE, MAX_TITLE):", "        if False:"),

    # -- the prompt boundary
    ("the fence is removed", FENCE, "    return str(raw)"),
    ("the fence leaves square brackets", FENCE, '    return str(raw).replace("<", "(").replace(">", ")")'),
    ("the fetched page reaches the prompt unfenced", "{fence(excerpt(page))}", "{excerpt(page)}"),
    ("the title reaches the prompt unfenced", "{fence(title)}", "{title}"),
    ("the prompt lets the model use dates of events", "Do not use the date of an event the\npage describes,", "Use the date of an event the\npage describes,"),
    ("the prompt lets the model work out today's date", "Do not guess, and do not\nwork out what today's date is.", "Work out what today's date is."),
    ("control characters are stored", '            out.append(" ")\n        else:', "            out.append(ch)\n        else:"),
]

PYTEST = [sys.executable, "-m", "pytest", "tests/", "-x", "-q", "--no-header", "-p", "no:cacheprovider"]


def copy_repo(tmp):
    dst = pathlib.Path(tmp) / "repo"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", ".git", "artifacts", "*.pyc"))
    return dst


def run_one(label, find, replace):
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        target = dst / "contracts" / TARGET
        src = target.read_text(encoding="utf-8")
        hits = src.count(find)
        if hits == 0:
            return "PATTERN NOT FOUND", None
        if hits > 1:
            return "PATTERN NOT UNIQUE", None
        target.write_text(src.replace(find, replace, 1), encoding="utf-8", newline="\n")
        subprocess.run([sys.executable, "scripts/lift.py"], cwd=dst, capture_output=True)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
        if proc.returncode == 0:
            return "ESCAPED", None
        text = proc.stdout + proc.stderr
        m = re.search(r"^(?:FAILED|ERROR) (\S+?)::(\S+?)(?:\[|\s|$)", text, re.M)
        if m:
            return "caught", m.group(2).split("::")[-1]
        m = re.search(r"^E\s+(\w*(?:Error|Exception))", text, re.M)
        if m:
            return "caught", m.group(1) + " at import"
        return "caught", "unnamed failure"


def baseline_is_green():
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="emit the README table")
    args = ap.parse_args()

    green, tail = baseline_is_green()
    if not green:
        print("the unmutated suite is not green; every mutation would look caught:\n" + tail, file=sys.stderr)
        return 2

    rows, escaped = [], []
    for label, find, replace in MUTATIONS:
        status, test = run_one(label, find, replace)
        if status == "caught":
            rows.append((label, test))
            if not args.md:
                print("  caught   %-70s %s" % (label, test), flush=True)
        else:
            escaped.append((label, status))
            print("  %-8s %s" % (status, label), file=sys.stderr, flush=True)

    if args.md:
        print("| Mutation | Caught by |")
        print("|---|---|")
        for label, test in rows:
            print("| %s | `%s` |" % (label, test))
    else:
        print()
        print("  %d mutations, %d caught, %d escaped" % (len(MUTATIONS), len(rows), len(escaped)))
    return 1 if escaped else 0


if __name__ == "__main__":
    sys.exit(main())
