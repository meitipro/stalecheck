# Decisions

What was chosen, and what was rejected, with the reason.

## The model reads a date; the contract decides freshness

**Rejected:** asking the model whether a page is up to date. That is a question
about today's date, which a model does not know, and different models answer
differently on the same day. A validator panel that cannot agree on "is this
current" cannot agree on anything.
**Chosen:** the model extracts one string, the page's own last-updated date
(`YYYY-MM-DD` or `none`), and only that crosses consensus. The contract compares
it with its own clock. Age, slack and the allowed limit are arithmetic, tested
at every boundary, and the model is never told the date, the limit or the fee.

## One reading, one prompt

The coarse-answer rule says to ask both presentation orders whenever a model
compares two items. Here there is one item and nothing to order: the answer is
a string read off a page, not a choice among options. One prompt, retried once
if the answer is unusable.

## Exact agreement on the date

Two validators that read `2026-11-20` and `2026-11-19` from the same page do not
agree. There is no tolerance: a page with two plausible stamps is a page whose
reading is not settled, and an unsettled reading must not move money.

## `none` is a reading, not an error

A page with no last-updated line is `undated`: recorded, not paid, and the
maintainer may add the line and try again. **Rejected:** failing the whole call.
A refusal that leaves the maintainer nowhere to go is the wrong answer to
"your page has no date".

## Two checks per window

A window pays at most once and takes at most two checks. A maintainer who sees
`stale` can fix the page and ask again; one who is `stale` twice has to wait
for the next window. The cap bounds what each check costs the validators; it is
also what stops a maintainer from asking until the page happens to be read
favourably.

## A day of slack, and no more

A page stamped tomorrow is usually a time zone ahead of UTC, not a lie. One day
ahead is `fresh`; two or more is `future` and pays nothing. A date from the far
future cannot buy an installment.

## Installments add up exactly

Equal shares, and the last window takes the remainder. A fee that does not
divide evenly is never left behind in the contract. A fee below one wei an
installment is refused at open.

## Unclaimed windows are returned, not rolled over

A window nobody checked in is simply not paid. The funder gets it back at
`close()`. **Rejected:** rolling an unclaimed installment into the next window,
which would let a maintainer skip months and then collect them with one fresh
edit.

## The funder cannot be the maintainer

The same wallet on both sides would turn the schedule into a loop that pays
itself. Refused at open.
