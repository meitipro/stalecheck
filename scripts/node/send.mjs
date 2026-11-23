// Send ONE transaction to StudioNet and print its hash.
//
//   echo {json} | node send.mjs
//
// StudioNet now asks for a fee on every write and deploy, and genlayer-py 0.18
// cannot attach one, so scripts/studio.py sends through this file with
// genlayer-js 2.x, whose estimateTransactionFees() returns the fee to attach.
// Everything else (reads, receipts, balances, the faucet) stays in genlayer-py.
//
// stdin:  {"key": "0x..", "op": "deploy"|"write", "code": "..", "address": "0x..",
//          "function": "..", "args": [..], "value": "123"}
//         an integer argument is {"$int": "123"} so it survives JSON as a bigint.
// stdout: one line  HASH 0x...   (a failure prints ERROR ... and exits 1)

import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

const revive = (v) => (v && typeof v === "object" && "$int" in v ? BigInt(v.$int) : Array.isArray(v) ? v.map(revive) : v);

const chunks = [];
for await (const c of process.stdin) chunks.push(c);
const req = JSON.parse(Buffer.concat(chunks).toString("utf8"));

try {
  const account = createAccount(req.key);
  const client = createClient({ chain: studionet, account });
  const fees = await client.estimateTransactionFees();
  let hash;
  if (req.op === "deploy") {
    hash = await client.deployContract({ code: req.code, args: revive(req.args ?? []), fees });
  } else if (req.op === "write") {
    hash = await client.writeContract({
      address: req.address, functionName: req.function, args: revive(req.args ?? []),
      value: BigInt(req.value ?? "0"), fees,
    });
  } else {
    throw new Error(`unknown op ${req.op}`);
  }
  console.log(`HASH ${hash}`);
} catch (e) {
  console.log(`ERROR ${String(e?.shortMessage ?? e?.message ?? e).split("\n")[0]}`);
  process.exit(1);
}
