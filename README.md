# Stalecheck - maintenance paid in installments, each only while the page itself shows a fresh date

A GenLayer Intelligent Contract for maintenance fees, with the whole fee paid
in before the first check. A funder opens a plan naming the page that has to be
kept up to date, the maintainer, how old the page's own "last updated" date may
be, and a schedule of equal windows. In each window the maintainer may ask for
that window's installment. The contract **fetches the page itself** with
`gl.nondet.web.render`, and the validators read **one fact** off it: the date
the page says it was last updated. **The contract then does the arithmetic
against its own clock.** A date inside the allowed age pays the window's
installment at once; anything else is recorded and the maintainer may fix the
page and try again, twice per window. A window nobody claimed in time is never
paid, and when the schedule ends the unpaid installments go back to the funder.

- **Contract:** [`contracts/stalecheck.py`](contracts/stalecheck.py)
- **Tests:** `pip install pytest && pytest tests/ -q` - nothing else to install
- **Deployed:** see [It is live](#it-is-live-and-every-path-is-on-chain) below, and [`deployments/studionet.json`](deployments/studionet.json)
- **Run the demo yourself:** [DEPLOY.md](DEPLOY.md)
- **Verify a deployment:** `python scripts/verify_deployment.py 0x...` - compares the on-chain source with this file and lints it
- **Decisions:** [DECISIONS.md](DECISIONS.md)
- **License:** MIT

---

## It is live, and every path is on chain

<!-- measured:deployment:start -->
Run `python scripts/demo.py`, then `python scripts/measure.py --write`.
<!-- measured:deployment:end -->

## The problem

"Keep the docs current" is paid on trust: the maintainer says it was done and
the funder takes their word or checks by hand. The obvious automation asks a
model *is this page up to date*, which is a question about **today's date**,
something a model cannot know, answered differently by every model on every day.

Stalecheck never asks it. The model is asked to **read** a date off the page,
which is a fact on the page. The contract compares that date with its own
clock, which is a fact on the chain. The maintainer cannot pay themselves by
typing a date: the date has to be on the page the contract fetched.

## How consensus is used

### Before any page is fetched, and before any model

The contract refuses for free what no answer could change: a check from anyone
but the maintainer, a check after the schedule ended, a check in a window that
is already paid, and a check in a window that has used its two checks.

### The fetch, then one reading

The block fetches the page with `gl.nondet.web.render`, independently on the
leader and on each validator, and asks the model for **one string**: the date
the page gives as its own last-updated date, written `YYYY-MM-DD`, or the word
`none`. Dates of events the page describes, copyright years and dates in
examples do not count; neither does the model's idea of today (it is told not
to work it out, and is never given it). A long page is shown by its start and
its end, where a last-updated line usually is.

Only that string crosses consensus.

### The validator, in two layers

1. **Structural, and free.** The reading is a real calendar date or `none`. A payload that fails this is refused before the validator spends a prompt.
2. **Exact agreement**, after the validator has fetched the page and read the date itself.

A page that cannot be fetched, or a model answer that is unusable, is retried
once inside the block and then raised as `[FETCH_ERROR]` or `[LLM_ERROR]`, which
no validator agrees with: a broken fetch or a broken model can never move money
and never uses up a check.

## What the contract decides, not the model

Given the date the validators agreed on and its own day number:

| verdict | when | pays |
|---|---|---|
| `fresh` | `0 <= age <= max_age` (a day of slack for a time zone ahead) | that window's installment, once |
| `stale` | older than `max_age` | nothing; may try again |
| `future` | more than a day ahead of the contract's clock | nothing |
| `undated` | the page gives no last-updated date (`none`) | nothing |

Installments are equal shares of the fee; the last window takes the remainder,
so they always add up to exactly what was paid in.

## The state machine and its clock

```
open --(fresh check in a window)--> that window is paid
open --(schedule ends, close())--> closed, unpaid installments back to the funder
```

`window k = [start + k * interval, start + (k + 1) * interval)`;
`ends_at = start + installments * interval`. After it `check()` refuses for free
and `close()` is open to anyone.

## Who may write

| Method | Who | Why |
|---|---|---|
| `open(maintainer, title, url, max_age_days, installments, interval)` payable | anyone | the caller is the funder; the fee is theirs |
| `check(id)` | the named maintainer | the one who is paid |
| `close(id)` | anyone | the unpaid rest goes to the recorded funder whoever asks, only after the schedule ended; it reads no page and no model |

## The API

```
open(maintainer: str, title: str, url: str, max_age_days: u256, installments: u256, interval: u256)   payable
check(plan_id: u256)
close(plan_id: u256)

count() -> u256
held_total() -> u256
status(plan_id) -> "open" | "closed"
plan(plan_id) -> {title, url, funder, maintainer, total, installment_amounts[], interval, max_age_days, status, windows_paid, paid_total, returned, ...}
checks_of(plan_id) -> every check with the date read, the age the contract made of it and what it paid
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
python scripts/mutate.py          # break every defence, one at a time
GENLAYER_STUDIO=1 pytest tests/test_integration.py -v     # opt in, hits StudioNet
```

<!-- measured:tests:start -->
Run `python scripts/measure.py --write`.
<!-- measured:tests:end -->

The suite runs the real contract file in `tests/glsim.py`, a small GenVM
stand-in that gives the leader and each validator **their own pages and their
own model answers**, rolls storage and transfers back when a call raises, and
refuses what GenVM refuses (a collection inside a storage dataclass, a `bool`
or `int` in a block's return value).

### The tests have teeth

<!-- measured:mutations:start -->
Run `python scripts/measure.py --write`.
<!-- measured:mutations:end -->

## Design rules applied

- **The coarsest answer that carries the judgment.** One string crosses consensus, and it is a fact on the page, not an opinion about it.
- **Uncertainty goes in the value.** `none` is its own reading; a date the validators read differently is a disagreement, not a rounding.
- **The contract does the arithmetic.** Age, slack, windows and installments are pure functions of the reading and the contract's clock, tested at every boundary.
- **Every write is bound to an address**, and a test fails when a write is added without being classified.
- **Untrusted text is fenced** at the prompt boundary (replace, never delete), and a test fails when a prompt value is not.
- **The deployed bytes are the repository's bytes:** `scripts/verify_deployment.py`.

## Further reading in this repository

- [`lib/stalecheck_consensus.py`](lib/stalecheck_consensus.py) - the freshness rules lifted out to copy; generated by `scripts/lift.py`, compared function by function with the contract by a test.
- [`DECISIONS.md`](DECISIONS.md) - what was chosen and what was rejected.
- [`SUBMISSION.md`](SUBMISSION.md) - the submission text.

## Known limits

- The page's own date is the evidence. A maintainer who edits only the date line, without updating anything else, passes; Stalecheck proves the page claims to be fresh, not that its content is correct.
- A page that changes between the leader's fetch and a validator's can make the validators disagree; the check then fails without being recorded, and may be tried again.
- Dates are read as written, in the contract's calendar (UTC days). A page stamped a day ahead is accepted as a time zone; two or more days ahead is `future`.
