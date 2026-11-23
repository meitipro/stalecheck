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
Deployed on studionet at [`0x7c5a2f26EeC64Bf791b357a3AbE3Fc67f032E3fD`](https://explorer-studio.genlayer.com/address/0x7c5a2f26EeC64Bf791b357a3AbE3Fc67f032E3fD) (deploy [`0xecf67053...`](https://explorer-studio.genlayer.com/tx/0xecf670535d5269594f03757edf3060d0db7f10470276f6215002a952ca13fcbb)). Every value below was read back from the chain by `scripts/demo.py` and written to [`deployments/studionet.json`](deployments/studionet.json); none of it is typed by hand. The two pages the contract fetched are real, public files in this repository: [`guide_fresh.md`](demo/pages/guide_fresh.md) and [`guide_stale.md`](demo/pages/guide_stale.md).

| Plan | Page | Fee | Windows | Allowed age | Windows paid | Paid to the maintainer | Returned to the funder | Status |
|---|---|---|---|---|---|---|---|---|
| 0: Quickstart guide, kept current | [`demo/pages/guide_fresh.md`](https://raw.githubusercontent.com/meitipro/stalecheck/master/demo/pages/guide_fresh.md) | 0.09 GEN | 3 | 30 days | 2 | 0.06 GEN | 0.03 GEN | closed |
| 1: Quickstart guide, an old copy | [`demo/pages/guide_stale.md`](https://raw.githubusercontent.com/meitipro/stalecheck/master/demo/pages/guide_stale.md) | 0.06 GEN | 2 | 30 days | 0 | 0 GEN | 0.06 GEN | closed |

What the validators read off each page, what the contract's own clock made of it, and what was paid:

| Plan | Window | Date read off the page | Age (days) | Verdict | Paid |
|---|---|---|---|---|---|
| 0 | 0 | `2026-11-20` | 3 | **fresh** | 0.03 GEN |
| 0 | 1 | `2026-11-20` | 3 | **fresh** | 0.03 GEN |
| 1 | 0 | `2025-03-02` | 631 | **stale** | 0 GEN |
| 1 | 0 | `2025-03-02` | 631 | **stale** | 0 GEN |

What the leader's model said about the page (not consensus):

| Plan | Reason the leader gave |
|---|---|
| 0 | The page contains a line reading "Last updated: 2026-11-20", which is its own last-updated stamp; no other dates appear. |
| 0 | The page explicitly states “Last updated: 2026-11-20”. |
| 1 | The page includes the line "Last updated: 2025-03-02" indicating its own revision date. |
| 1 | The page explicitly says “Last updated: 2025-03-02,” which is its own revision stamp. |

StudioNet charges a fee on every write, so a wallet's balance alone cannot show what it was paid. What each wallet received is read from the chain's own index: the transfers the contract sent it, against what the contract says it sent:

| Wallet | Received from the contract | The contract sent | Transfer |
|---|---|---|---|
| funder | 0.09 GEN | 0.09 GEN | [`0xb7e8f6c8...`](https://explorer-studio.genlayer.com/tx/0xb7e8f6c80913e75642907d4fe771ebc6a52aac4feee5c1e53a306b9d6e8442da), [`0xa3681dea...`](https://explorer-studio.genlayer.com/tx/0xa3681deabc11af5ed072524dee82ea16cbd4e90588c8b888d4147248a78ee6bb) |
| maintainer | 0.06 GEN | 0.06 GEN | [`0xbab49e43...`](https://explorer-studio.genlayer.com/tx/0xbab49e43906b67a01e24b02f8a203ee478bce3f4171e80d754d07149b98f89b0), [`0xcf2107fa...`](https://explorer-studio.genlayer.com/tx/0xcf2107fa8d08f661c20e3b8863255f1070ffc6f3549c791b6dddc1b8c777dcfd) |

Held by the contract afterwards: 0 wei.

Every transaction, in order, refusals included, with the wallet that sent it:

| Step | From | Outcome | Transaction |
|---|---|---|---|
| plan 0 opened: a guide with a recent date, 3 windows, 0.09 GEN | funder | ok | [`0x4ceb31b3...`](https://explorer-studio.genlayer.com/tx/0x4ceb31b3990fdd43cf1588f38dd9207d8cc758af442814609647c05c1890d93d) |
| plan 1 opened: an old copy of the guide, 2 windows, 0.06 GEN | funder | ok | [`0xaf7c9fe0...`](https://explorer-studio.genlayer.com/tx/0xaf7c9fe035a70795883e1310c06a34bd16f9cecb52561c975dfb260e2426e603) |
| a check from someone who is not the maintainer | stranger | refused: only the named maintainer may check | [`0xd331487d...`](https://explorer-studio.genlayer.com/tx/0xd331487d0dccf7b7e71e1991fc6a87881185836fd5d4b249c02a24041d41f375) |
| plan 0, window 0: the date is read off the page and is fresh: paid | maintainer | ok | [`0x7b8cbe61...`](https://explorer-studio.genlayer.com/tx/0x7b8cbe61f971a0cc43195b5ef146c1a9257bbf0d4be84a74ee9d73f7893c704f) |
| a second check in a window that is already paid | maintainer | refused: window 0 is already paid | [`0xf108f2c3...`](https://explorer-studio.genlayer.com/tx/0xf108f2c33dc46f176f46052a142e06eaee0ab15a5fedc690688c736f5a6bc5c8) |
| plan 1, window 0: the date is read off the page and is stale: not paid | maintainer | ok | [`0xd3b3e56a...`](https://explorer-studio.genlayer.com/tx/0xd3b3e56a13ce440175617ca0a7d58fe2c762a06c53b236e847b7fa6ed645dcbc) |
| plan 1, window 0: a second try, still stale: not paid | maintainer | ok | [`0x899c191c...`](https://explorer-studio.genlayer.com/tx/0x899c191ca941a18f9f4f6d2ad1e310cb2b710b44e0dedc9af817a4959817cf0b) |
| a third check in a window that has used its two | maintainer | refused: window 0 has used its 2 checks | [`0x10f9a719...`](https://explorer-studio.genlayer.com/tx/0x10f9a71974e1e572ce1b4c7a2c428fa10b67494b364bea9212ee6b8246826a3a) |
| plan 0, window 1: fresh again: paid | maintainer | ok | [`0x8a282be7...`](https://explorer-studio.genlayer.com/tx/0x8a282be7703e4e1fbf15ed4921bfa55d4127d97a62a637a6a8df48763d1e9d81) |
| closing plan 0 while its schedule is still running | stranger | refused: the schedule runs until 2026-11-23T22:24:56Z | [`0x03fd3af4...`](https://explorer-studio.genlayer.com/tx/0x03fd3af4ab5cbc50d97372c74aa202867d4de9b1ef7eb7171984eba9d364141c) |
| a check after plan 0's schedule ended (window 2 was never claimed) | maintainer | refused: the schedule ended at 2026-11-23T22:24:56Z; a late check is never read | [`0xd6070eed...`](https://explorer-studio.genlayer.com/tx/0xd6070eed71100008e5bddc6a02da345d5454c38323edb7d470d1a4afd0c41561) |
| plan 0 closed: the unclaimed third installment returns to the funder | stranger | ok | [`0x66cde6a5...`](https://explorer-studio.genlayer.com/tx/0x66cde6a5ba9879e137de18b4b3f1a7017ff91f740fb6f8157106a8de496de8ad) |
| plan 1 closed: nothing was ever fresh, the whole fee returns to the funder | stranger | ok | [`0xbe2565f8...`](https://explorer-studio.genlayer.com/tx/0xbe2565f83328b8db05de50cc29ca226b9b4089c09a77375895d76accb553c8ef) |

`tests/test_runbook.py::TestTheRecord` replays these readings through this repository's contract and fails unless it pays exactly what the deployed one did, and unless every wallet gained on chain exactly what the contract sent it.
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
Measured: **145 passed**, 1 skipped. The skipped tests are the opt-in StudioNet integration tests, which run with `GENLAYER_STUDIO=1`.
<!-- measured:tests:end -->

The suite runs the real contract file in `tests/glsim.py`, a small GenVM
stand-in that gives the leader and each validator **their own pages and their
own model answers**, rolls storage and transfers back when a call raises, and
refuses what GenVM refuses (a collection inside a storage dataclass, a `bool`
or `int` in a block's return value).

### The tests have teeth

<!-- measured:mutations:start -->
Measured: **74 mutations, 74 caught, 0 escaped.**

| Mutation | Caught by |
|---|---|
| a date that is not a calendar date is read | `test_a_leader_that_sends_an_unsound_reading_is_refused_before_any_prompt` |
| a date with letters in it is read | `test_anything_else_is_not_a_date` |
| an impossible date is read | `test_an_unusable_answer_is_an_error_and_never_a_reading` |
| the word none is not a sound reading | `test_a_page_without_a_date_is_undated_and_pays_nothing` |
| anything is a sound reading | `test_a_leader_that_sends_an_unsound_reading_is_refused_before_any_prompt` |
| prose around a date is tolerated | `test_an_unusable_answer_is_an_error_and_never_a_reading` |
| a model's answer that is not a string is read | `test_an_unusable_answer_is_an_error_and_never_a_reading` |
| an unusable answer is not retried | `test_an_unusable_answer_is_an_error_and_never_a_reading` |
| an unusable answer is read as none | `test_an_unusable_answer_is_an_error_and_never_a_reading` |
| an answer that is not an object crashes the block | `test_an_unusable_answer_is_an_error_and_never_a_reading` |
| a fetch error is swallowed and read as an empty page | `test_fetch_wraps_a_non_user_error_as_fetch_error` |
| a short or empty page is still read | `test_fetch_refuses_a_page_shorter_than_min_page` |
| the page is never actually fetched | `test_the_model_is_asked_once_and_never_shown_the_date_the_age_the_fee_or_who` |
| a long page is shown by its start only | `test_a_long_page_is_read_by_its_start_and_its_end` |
| a long page is shown whole | `test_a_long_page_is_shown_by_its_start_and_its_end` |
| the validator agrees with an error | `test_an_unusable_answer_is_an_error_and_never_a_reading` |
| the validator skips the structural check | `test_a_leader_that_sends_an_unsound_reading_is_refused_before_any_prompt` |
| the validator agrees with anything sound | `test_nodes_that_read_different_dates_do_not_agree` |
| the validator agrees when its own fetch or model fails | `test_a_validator_whose_own_fetch_fails_does_not_agree` |
| agreement ignores soundness | `test_agreement_is_exact_symmetric_and_over_sound_readings` |
| agreement is not exact | `test_nodes_that_read_different_dates_do_not_agree` |
| the contract's day is taken from the wrong clock | `test_a_fresh_page_pays_the_window_s_installment_at_once` |
| the age limit is exclusive | `test_the_contract_compares_the_date_with_its_own_clock` |
| a stale page is fresh | `test_a_stale_page_is_recorded_with_its_age_and_pays_nothing` |
| a page from the future is fresh | `test_the_contract_compares_the_date_with_its_own_clock` |
| no slack for a time zone ahead | `test_the_contract_compares_the_date_with_its_own_clock` |
| an undated page is fresh | `test_a_page_without_a_date_is_undated_and_pays_nothing` |
| the window is counted wrongly | `test_a_fresh_page_pays_the_window_s_installment_at_once` |
| the last installment does not take the remainder | `test_a_plan_opens_with_its_page_and_schedule_frozen_and_the_fee_paid_in` |
| the agreed reading is not checked again | `test_the_contract_does_not_trust_a_consensus_value_it_cannot_read` |
| every check pays, fresh or not | `test_a_stale_page_is_recorded_with_its_age_and_pays_nothing` |
| a fresh page pays nothing | `test_a_fresh_page_pays_the_window_s_installment_at_once` |
| a fresh page pays the first installment whatever the window | `test_each_window_pays_its_own_installment_and_the_last_takes_the_remainder` |
| a paid window is not marked paid | `test_a_window_pays_once` |
| the paid count is not raised | `test_a_fresh_page_pays_the_window_s_installment_at_once` |
| the paid total is not raised | `test_a_fresh_page_pays_the_window_s_installment_at_once` |
| the checks of a window are not counted | `test_a_window_takes_a_bounded_number_of_checks` |
| a check is not linked to its plan | `test_the_maintainer_may_fix_the_page_and_check_again` |
| the check count is not raised | `test_a_fresh_page_pays_the_window_s_installment_at_once` |
| every check is recorded as fresh | `test_a_stale_page_is_recorded_with_its_age_and_pays_nothing` |
| a leader's reason is stored as sent | `test_a_leader_s_reason_is_stored_clean_and_capped_even_if_the_validator_never_saw_it` |
| a leader's reason is stored uncapped | `test_a_leader_s_reason_is_stored_clean_and_capped_even_if_the_validator_never_saw_it` |
| anyone may check | `test_only_the_maintainer_may_check` |
| a check is taken on a closed plan | `test_a_closed_plan_takes_no_more_checks` |
| a check is taken after the schedule | `test_nothing_is_taken_once_the_schedule_has_ended` |
| a window pays twice | `test_a_window_pays_once` |
| a window takes any number of checks | `test_a_window_takes_a_bounded_number_of_checks` |
| a window takes one check too many | `test_a_window_takes_a_bounded_number_of_checks` |
| a plan closes while the schedule runs | `test_nothing_closes_while_the_schedule_runs` |
| a closed plan closes again | `test_a_plan_closes_once` |
| close returns the whole fee even if installments were paid | `test_unpaid_installments_return_to_the_funder` |
| close returns less than the unpaid rest | `test_unpaid_installments_return_to_the_funder` |
| the return is not recorded | `test_unpaid_installments_return_to_the_funder` |
| the closing time is not recorded | `test_unpaid_installments_return_to_the_funder` |
| a fee below one wei an installment is accepted | `test_every_installment_is_at_least_one_wei` |
| the held counter is not raised | `test_a_plan_opens_with_its_page_and_schedule_frozen_and_the_fee_paid_in` |
| a payout beyond what is held is sent | `test_a_payout_beyond_what_is_held_is_refused` |
| the held counter is not lowered | `test_a_fresh_page_pays_the_window_s_installment_at_once` |
| the funder may name itself as the maintainer | `test_the_funder_cannot_name_itself` |
| the maintainer need not look like an address | `test_the_maintainer_must_be_an_address` |
| the page is not checked | `test_the_title_and_the_page_are_bounded` |
| a page with angle brackets is accepted | `test_the_title_and_the_page_are_bounded` |
| the allowed age is unbounded | `test_the_allowed_age_is_bounded` |
| the installments are unbounded | `test_the_number_of_installments_is_bounded` |
| the window is unbounded | `test_the_window_is_bounded` |
| the schedule does not end where it should | `test_a_plan_opens_with_its_page_and_schedule_frozen_and_the_fee_paid_in` |
| the title is unbounded | `test_the_title_and_the_page_are_bounded` |
| the fence is removed | `test_hostile_text_on_the_page_cannot_close_a_block` |
| the fence leaves square brackets | `test_the_fence_replaces_and_preserves_length` |
| the fetched page reaches the prompt unfenced | `test_hostile_text_on_the_page_cannot_close_a_block` |
| the title reaches the prompt unfenced | `test_every_prompt_value_is_fenced` |
| the prompt lets the model use dates of events | `test_the_prompt_asks_for_one_date_and_says_the_page_is_fetched_not_typed` |
| the prompt lets the model work out today's date | `test_the_prompt_asks_for_one_date_and_says_the_page_is_fetched_not_typed` |
| control characters are stored | `test_clean_text_collapses_whitespace_and_control_characters` |
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
