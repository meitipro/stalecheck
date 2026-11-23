"""Deploy Stalecheck to StudioNet and put every path on the explorer.

    pip install genlayer-py==0.18.0
    python scripts/demo.py

The run deploys contracts/stalecheck.py exactly as it is in this repository,
then sends the steps in scripts/demo_data.py (STEPS), including the ones that
end in a refusal, and writes what happened to deployments/studionet.json:
every transaction hash, its sender and status, the refusal sentence where
there was one, every plan and every check as the chain holds them, and the
balance of every wallet that was paid, read before and again once every
payment had landed. Nothing in that file is typed by hand.

Three accounts: the funder, the maintainer and a stranger. They are made in
memory for this run and never written to disk; the funder is funded from the
StudioNet faucet to pay the two fees in.

The funder both pays in (at open) and is refunded (at close), so its balance
is snapshotted right after the last open, never from an earlier moment.
"""

import datetime
import hashlib
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent))
import demo_data as D                                       # noqa: E402
from payouts import collect                                 # noqa: E402
from studio import EXPLORER, Studio                         # noqa: E402

ROOT = pathlib.Path(__file__).absolute().parent.parent
SOURCE = ROOT / "contracts" / "stalecheck.py"
OUT = ROOT / "deployments" / "studionet.json"

ROLES = ("funder", "maintainer", "stranger")
PAID = ("funder", "maintainer")


def epoch(stamp):
    return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def wait_until(target, what):
    left = target - time.time()
    if left > 0:
        print(f"  waiting {int(left)}s for {what}")
        time.sleep(left)


def wait_for_balance(s, address, at_least, label, tries=24):
    """A payment can land a little after the transaction that sent it, so the
    balance is read until it has arrived rather than once."""
    for _ in range(tries):
        b = s.balance(address)
        if b >= at_least:
            return b
        time.sleep(5)
    print(f"  {label}: the payment had not landed after {tries * 5}s")
    return s.balance(address)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    code = SOURCE.read_text(encoding="utf-8")
    s = Studio()

    print("\naccounts (in memory, StudioNet test GEN only)")
    who = {name: s.account(name, gen=4 if name == "funder" else 1) for name in ROLES}
    before = {"maintainer": s.balance(who["maintainer"].address)}

    print("\ndeploy")
    address = s.deploy(who["funder"], code, [])

    print("\nthe demo")
    last_open = max(i for i, step in enumerate(D.STEPS) if step[1] == "open")
    for i, step in enumerate(D.STEPS):
        actor, method, spec, value, expect, label = step[:6]
        for tag in step[6:]:
            kind, *parts = tag.split(":")
            if kind == "at_window":
                pid, w = int(parts[0]), int(parts[1])
                plan = s.read(address, "plan", [pid])
                wait_until(epoch(plan["started_at"]) + w * plan["interval"] + 15, f"plan {pid}'s window {w}")
            elif kind == "after_close":
                pid = int(parts[0])
                wait_until(epoch(s.read(address, "plan", [pid])["ends_at"]) + 20, f"plan {pid}'s schedule to end")
        args = [who[a].address if a in who else a for a in spec]
        s.write(who[actor], address, method, args, value=value, step=label, expect=expect)
        if i == last_open:
            # Every plan is open now and every fee is paid in; nothing further
            # pays the funder back until a close: the right point to snapshot
            # its balance.
            before["funder"] = s.balance(who["funder"].address)

    n = int(s.read(address, "count"))
    plans = [s.read(address, "plan", [k]) for k in range(n)]
    checks = [s.read(address, "checks_of", [k]) for k in range(n)]

    owed = {"funder": 0, "maintainer": 0}
    for p in plans:
        owed["maintainer"] += int(p["paid_total"])
        owed["funder"] += int(p["returned"])
    # A wallet that sends transactions pays fees, so what it was paid is read from the
    # index (the contract's own transfers), not inferred from a balance.
    payouts, received = collect(s, address, {n: a.address for n, a in who.items()}, owed)
    after = {name: s.balance(who[name].address) for name in PAID}

    record = {
        "network": "studionet",
        "chain_id": 61999,
        "contract": address,
        "explorer": f"{EXPLORER}/address/{address}",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "constructor": {},
        "accounts": {name: a.address for name, a in who.items()},
        "balances": {f"{name}_{when}": str(v[name]) for when, v in (("before", before), ("after", after))
                     for name in PAID},
        "owed": {name: str(v) for name, v in owed.items()},
        "payouts": payouts,
        "received": received,
        "held_after": str(s.read(address, "held_total")),
        "steps": s.log,
        "plans": plans,
        "checks": checks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")

    print(f"\n  contract   {address}")
    print(f"  explorer   {EXPLORER}/address/{address}")
    for k, p in enumerate(plans):
        rows = checks[k]["checks"]
        print(f"  plan {k}  {p['status']}  windows paid {p['windows_paid']}  returned {p['returned']}  "
              f"checks {[(r['window'], r['as_of'], r['verdict']) for r in rows]}")
    for name in PAID:
        print(f"  {name:<10} received {received[name]}  owed {owed[name]}")
    print(f"  written    {OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
