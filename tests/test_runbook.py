"""
The demo, replayed offline.

scripts/demo.py puts the demo on StudioNet from scripts/demo_data.py (STEPS).
This file replays the same steps against the real contract in the simulator,
serving the two real demo pages from the files of this repository, so the pure
logic is checked before a single transaction is spent on it.

When deployments/studionet.json exists, the replay goes further: it feeds the
simulator the dates the validators actually read off the pages, starts the
clock where the live run started, and checks that the contract in this
repository pays exactly what the deployed one did, and refuses exactly where
it refused.

    pytest tests/test_runbook.py -v
"""

import collections
import datetime
import hashlib
import importlib.util
import json
import pathlib

import pytest

import glsim as S

CONTRACT_PATH = "contracts/stalecheck.py"
M = S.load_contract(CONTRACT_PATH)
RECORD = pathlib.Path("deployments/studionet.json")

_spec = importlib.util.spec_from_file_location("demo_data", "scripts/demo_data.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

WHO = {"funder": "0x" + "a1" * 20, "maintainer": "0x" + "b2" * 20, "stranger": "0x" + "f6" * 20}

PAGES = {
    D.FRESH_URL: pathlib.Path("demo/pages/guide_fresh.md").read_text(encoding="utf-8"),
    D.STALE_URL: pathlib.Path("demo/pages/guide_stale.md").read_text(encoding="utf-8"),
}


def replay(readings, who=WHO, start=None):
    """Run STEPS. `readings` are what the ok checks come back with, in order:
    the date the validators read off the page."""
    S.reset_transfers()
    c = S.deploy(CONTRACT_PATH)
    queue = list(readings)
    outcomes = []
    clock = M.seconds(start or D.DEMO_START)
    for step in D.STEPS:
        actor, method, spec, value, expect, label = step[:6]
        clock += 30
        for tag in step[6:]:
            kind, *parts = tag.split(":")
            if kind == "at_window":
                plan = c.plan(int(parts[0]))
                clock = max(clock, M.seconds(plan["started_at"]) + int(parts[1]) * plan["interval"] + 30)
            elif kind == "after_close":
                clock = max(clock, M.seconds(c.plan(int(parts[0]))["ends_at"]) + 20)
        S.set_time(M.iso(clock))
        S.set_mocks()
        if method == "check" and expect == "ok":
            url = c.plan(spec[0])["url"]
            S.set_mocks(leader_pages={url: PAGES[url]},
                        leader_prompts={"<fetched_page>": {"as_of": queue.pop(0), "because": "replayed"}})
        S.set_sender(who[actor])
        args = [who[a] if a in who else a for a in spec]
        try:
            S.call(c, method, *args, value=value)
            outcomes.append(("ok", ""))
        except S.UserError as e:
            outcomes.append(("refused", e.message))
    return c, outcomes


def received():
    out = collections.Counter()
    for to, v in S.transfers():
        out[str(to).lower()] += v
    return out


class TestDemoData:
    def test_every_value_the_demo_sends_passes_the_bounds(self):
        assert M.MIN_TITLE <= len(D.TITLE_0) <= M.MAX_TITLE and M.MIN_TITLE <= len(D.TITLE_1) <= M.MAX_TITLE
        assert M.MIN_AGE_DAYS <= D.MAX_AGE <= M.MAX_AGE_DAYS
        assert M.MIN_INTERVAL <= D.INTERVAL <= M.MAX_INTERVAL
        for n, fee in ((D.N_0, D.FEE_0), (D.N_1, D.FEE_1)):
            assert M.MIN_INSTALLMENTS <= n <= M.MAX_INSTALLMENTS and n <= fee <= M.MAX_AMOUNT
        for url in (D.FRESH_URL, D.STALE_URL):
            assert M.is_http_url(url) and M.MIN_URL <= len(url) <= M.MAX_URL

    def test_the_two_demo_pages_are_real_files_in_this_repository(self):
        for url in (D.FRESH_URL, D.STALE_URL):
            assert len(PAGES[url].strip()) >= M.MIN_PAGE
        assert D.FRESH_URL.endswith("/demo/pages/guide_fresh.md") and D.STALE_URL.endswith("/demo/pages/guide_stale.md")

    def test_the_dates_on_the_pages_are_the_ones_the_demo_expects(self):
        assert "Last updated: " + D.EXPECTED_READINGS[0] in PAGES[D.FRESH_URL]
        assert "Last updated: " + D.EXPECTED_READINGS[1] in PAGES[D.STALE_URL]

    def test_the_demo_day_puts_one_page_inside_the_age_limit_and_the_other_outside_it(self):
        today = M.today_of(M.seconds(D.DEMO_START))
        assert M.verdict_of(D.EXPECTED_READINGS[0], today, D.MAX_AGE)[0] == "fresh"
        assert M.verdict_of(D.EXPECTED_READINGS[1], today, D.MAX_AGE)[0] == "stale"

    def test_the_window_outlasts_the_steps_meant_to_land_inside_it(self):
        """Window 0 of each plan holds, from the funder's second open: one
        refusal, one check that reads a page (up to 150 s) and two more (each
        up to 150 s) and one refusal. They must land before it closes."""
        assert D.INTERVAL >= 3 * 150 + 3 * 30


class TestReplay:
    def test_the_demo_succeeds_and_refuses_exactly_where_it_says(self):
        _, outcomes = replay(D.EXPECTED_READINGS)
        assert [o for o, _ in outcomes] == [s[4] for s in D.STEPS]

    def test_the_refusals_say_why(self):
        _, outcomes = replay(D.EXPECTED_READINGS)
        msgs = [m for o, m in outcomes if o == "refused"]
        wants = ["only the named maintainer may check", "window 0 is already paid", "window 0 has used its 2 checks",
                 "the schedule runs until", "a late check is never read"]
        assert len(msgs) == len(wants)
        for msg, want in zip(msgs, wants):
            assert want in msg, (want, msg)

    def test_the_fresh_guide_is_paid_twice_and_the_old_copy_never(self):
        c, _ = replay(D.EXPECTED_READINGS)
        p0, p1 = c.plan(0), c.plan(1)
        share = D.FEE_0 // D.N_0
        assert (p0["status"], p0["windows_paid"], p0["paid_total"], p0["returned"]) == \
            ("closed", 2, str(2 * share), str(D.FEE_0 - 2 * share))
        assert (p1["status"], p1["windows_paid"], p1["paid_total"], p1["returned"]) == ("closed", 0, "0", str(D.FEE_1))
        assert [(r["window"], r["as_of"], r["verdict"], int(r["paid"]) > 0) for r in c.checks_of(0)["checks"]] == [
            (0, "2026-11-20", "fresh", True), (1, "2026-11-20", "fresh", True)]
        assert [(r["window"], r["as_of"], r["verdict"], r["paid"]) for r in c.checks_of(1)["checks"]] == [
            (0, "2025-03-02", "stale", "0"), (0, "2025-03-02", "stale", "0")]
        got = received()
        assert got[WHO["maintainer"]] == 2 * share
        assert got[WHO["funder"]] == (D.FEE_0 - 2 * share) + D.FEE_1 and c.held_total() == 0


@pytest.mark.skipif(not RECORD.exists(), reason="no deployment recorded yet: python scripts/demo.py")
class TestTheRecord:
    """The live run, checked against this repository."""

    def _record(self):
        return json.loads(RECORD.read_text(encoding="utf-8"))

    def _readings(self, rec):
        rows = [r for block in rec["checks"] for r in block["checks"]]
        return [r["as_of"] for r in sorted(rows, key=lambda r: r["id"])]

    def test_the_record_is_of_this_source(self):
        here = hashlib.sha256(pathlib.Path(CONTRACT_PATH).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert self._record()["source_sha256"] == here, "the deployed contract is not this file; redeploy"

    def test_every_step_on_chain_did_what_the_demo_expected(self):
        steps = [s for s in self._record()["steps"] if s["step"] != "deploy"]
        assert [("ok" if s["ok"] else "refused") for s in steps] == [s[4] for s in D.STEPS]

    def test_the_dates_read_off_the_pages_are_the_dates_on_the_pages(self):
        assert self._readings(self._record()) == D.EXPECTED_READINGS

    def test_this_contract_pays_what_the_deployed_one_paid(self):
        rec = self._record()
        c, outcomes = replay(self._readings(rec), who=rec["accounts"], start=rec["plans"][0]["started_at"])
        assert [o for o, _ in outcomes] == [s[4] for s in D.STEPS]
        for k, theirs in enumerate(rec["plans"]):
            mine = c.plan(k)
            for field in ("status", "windows_paid", "paid_total", "returned", "checks"):
                assert str(mine[field]) == str(theirs[field]), (k, field)
            assert [(r["window"], r["as_of"], r["verdict"], r["paid"], r["age_days"]) for r in c.checks_of(k)["checks"]] == \
                [(r["window"], r["as_of"], r["verdict"], r["paid"], r["age_days"]) for r in rec["checks"][k]["checks"]]

    def test_every_wallet_received_on_chain_exactly_what_the_contract_sent(self):
        rec = self._record()
        replay(self._readings(rec), who=rec["accounts"], start=rec["plans"][0]["started_at"])
        got = received()
        for name in rec["owed"]:
            assert int(rec["received"][name]) == got[rec["accounts"][name].lower()] == int(rec["owed"][name]), name
            assert sum(int(x["value"]) for x in rec["payouts"][name]) == int(rec["received"][name]), name
        assert rec["held_after"] == "0"
