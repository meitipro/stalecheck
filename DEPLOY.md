# Deploying Stalecheck

Everything here runs on StudioNet. It is gasless; the only GEN needed is each
plan's fee, and the funder gets it from the StudioNet faucet.
Nothing needs a private key in a file.

## 1 - Check the contract

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
python scripts/schema_check.py contracts/stalecheck.py
GENVM_VERSION=v0.3.0-rc7 python -m genvm_linter.cli check contracts/stalecheck.py
```

`schema_check.py` runs the file through the live studionet runtime with
`gen_getContractSchemaForCode`, without deploying it. On Windows, set
`PYTHONIOENCODING=utf-8` first, or the linter dies printing its own tick.

## 2 - The two real demo pages

The live demo needs the contract to fetch something real. [`demo/pages/guide_fresh.md`](demo/pages/guide_fresh.md)
and [`demo/pages/guide_stale.md`](demo/pages/guide_stale.md) are committed into
this repository and pushed ahead of the demo, so they are reachable at:

```
https://raw.githubusercontent.com/meitipro/stalecheck/master/demo/pages/guide_fresh.md
https://raw.githubusercontent.com/meitipro/stalecheck/master/demo/pages/guide_stale.md
```

`scripts/demo_data.py` points at exactly those URLs. The allowed age is 30 days,
so the demo is meant to be run within 30 days of the date on the fresh page
(2026-11-20). Run later and the fresh guide will honestly read as `stale`; move
its date line forward first. If you fork this repository, update `RAW` in
that file too.

## 3 - Run the demo

```bash
python scripts/demo.py
```

It makes three accounts in memory: the funder, the maintainer and a stranger.
The funder is funded with 4 GEN from the faucet. It deploys
`contracts/stalecheck.py` exactly as it is in this repository, then sends the
steps in [`scripts/demo_data.py`](scripts/demo_data.py); the same list drives
the demo and `tests/test_runbook.py`. Windows are 10 minutes, so the run takes
about half an hour.

| # | Plan | From | Call | Expected |
|---|---|---|---|---|
| 1 | 0 | funder | `open(maintainer, ..., 30 days, 3 windows, 600 s)` | ok |
| 2 | 1 | funder | `open(maintainer, ..., 30 days, 2 windows, 600 s)` | ok |
| 3 | 0 | stranger | `check(0)` | refused: not the maintainer |
| 4 | 0 | maintainer | `check(0)` | ok: date read, **fresh**, window 0 paid |
| 5 | 0 | maintainer | `check(0)` | refused: window 0 already paid |
| 6 | 1 | maintainer | `check(1)` | ok: **stale**, not paid |
| 7 | 1 | maintainer | `check(1)` | ok: **stale** again, not paid |
| 8 | 1 | maintainer | `check(1)` | refused: used its 2 checks |
| 9 | 0 | maintainer | `check(0)` in window 1 | ok: **fresh**, window 1 paid |
| 10 | 0 | stranger | `close(0)` | refused: schedule still running |
| 11 | 0 | maintainer | `check(0)` after the schedule | refused: late |
| 12 | 0 | stranger | `close(0)` | ok: the unclaimed window returns |
| 13 | 1 | stranger | `close(1)` | ok: the whole fee returns |

It writes `deployments/studionet.json`: every transaction, the refusal
sentences, every plan and check as the chain holds them, and every wallet's
balance before and after.

## 4 - Measure and verify

```bash
python scripts/measure.py --write
python scripts/verify_deployment.py <address>
```
