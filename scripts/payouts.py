"""Read what the contract actually sent each wallet, from StudioNet's own index.

    python scripts/payouts.py            # add "payouts" and "received" to deployments/studionet.json

StudioNet now charges a fee on every write, so a wallet that sends transactions
and is also paid by the contract cannot be checked by a balance alone: its
balance falls by the fees it paid while the payout lands. The payout itself is
a transaction in the index, from the contract to the wallet, with the amount as
its value. This reads those rows, so what the record says each wallet received
is what the chain says the contract sent it, whatever the wallet paid in fees.

scripts/demo.py calls collect() at the end of a run; running this file does the
same on a record that already exists.
"""

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent))
from studio import Studio                                   # noqa: E402

ROOT = pathlib.Path(__file__).absolute().parent.parent
RECORD = ROOT / "deployments" / "studionet.json"


def incoming(s, contract, address):
    """Finalized transfers from `contract` to `address`, oldest first."""
    rows = s.reader.provider.make_request(method="sim_getTransactionsForAddress", params=[address])
    rows = rows.get("result", rows) if isinstance(rows, dict) else rows
    mine = [r for r in rows
            if str(r.get("from_address") or "").lower() == contract.lower()
            and str(r.get("to_address") or "").lower() == address.lower()
            and str(r.get("status")) == "FINALIZED"]
    return sorted(mine, key=lambda r: str(r.get("created_at")))


def collect(s, contract, accounts, owed, tries=36):
    """For each wallet in `owed`, wait until the index shows the transfers the
    contract sent it, and return ({name: [rows]}, {name: total wei})."""
    payouts, received = {}, {}
    for name, want in owed.items():
        rows = []
        for _ in range(tries):
            rows = s._retry(lambda: incoming(s, contract, accounts[name]), f"payouts to {name}")
            if sum(int(r["value"]) for r in rows) >= int(want):
                break
            time.sleep(5)
        else:
            print(f"  {name}: the payment had not been indexed after {tries * 5}s")
        payouts[name] = [{"tx": r["hash"], "value": str(int(r["value"])), "created_at": str(r.get("created_at"))}
                         for r in rows]
        received[name] = str(sum(int(r["value"]) for r in rows))
    return payouts, received


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    payouts, received = collect(Studio(), rec["contract"], rec["accounts"], rec["owed"])
    rec["payouts"], rec["received"] = payouts, received
    RECORD.write_text(json.dumps(rec, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    for name in rec["owed"]:
        print(f"  {name:<10} received {received[name]}  owed {rec['owed'][name]}")


if __name__ == "__main__":
    main()
