# Submission

One submission, under **Builder -> Intelligent Contracts**. This repository is
one standalone primitive.

---

## Before you submit, in order

1. **Measure, do not estimate.**

   ```bash
   python scripts/measure.py --write
   ```

2. **Prove the address is evidence for this repository.**

   ```bash
   python scripts/verify_deployment.py <address>
   ```

3. **Open the explorer page and check it.** It must show the deploy, two paid
   opens, a refusal for a check by a stranger, two paid windows of the fresh
   guide, a refusal for a second check in a paid window, two stale checks of the
   old copy, a refusal for a third, a refusal for a close while the schedule
   runs, a refusal for a late check, and two closes that return the unpaid
   installments.

---

## Title

Stalecheck

## Notes

Maintenance fees paid in installments, each only while the page itself shows a fresh date. A funder pays the whole fee in and names the page, the maintainer, the allowed age and a schedule of windows. In each window the maintainer asks for the installment. The contract fetches the page itself and the validators read one thing off it, the date the page gives as its own last update. The contract then compares that date with its own clock: fresh pays the window once, stale or undated records the check and lets the maintainer fix the page and try again, twice per window. Unclaimed windows are never paid and return to the funder when the schedule ends. The model never judges whether a page is current; it reads a date and the contract does the arithmetic.

## Known limits

The page's own date is the evidence, so it proves the page claims to be fresh, not that its content is correct. The demo is meant to be run within 30 days of the date on its fresh page.
