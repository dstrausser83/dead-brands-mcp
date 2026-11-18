# The Web4 public node registry

Every Web4 node is a **key with a number**. This is the public registry —
the same data lives machine-readably in [nodes.json](nodes.json), and the
claimed nodes are named on the Dead Brands site.

**The offer:** the first **500** claimed nodes are named on the site,
permanently, in claim order. Claiming is free — a key, a proof, a
handshake. No fee, no token, no staking. See [NODE-CLAIM.md](NODE-CLAIM.md)
for the design and [HUMAN-SETUP.md](HUMAN-SETUP.md) /
[AGENT-SETUP.md](AGENT-SETUP.md) to claim yours with one command.

## Claimed

| Node # | Name | Fingerprint | Platform | Class | State | Claimed |
|---|---|---|---|---|---|---|
| 0 | Node 0 — Raspberry Pi 5, Pennsylvania | `8a0d8d0ae512b9da` | raspberry-pi | door | ACTIVE | 2026-11-17 |

Node 0 is the root: it runs the Underground front-end, the Tor door, and
the exit fetcher. Donated by David Strausser, CEO, Dead Brands, LLC.

## Open

**Node #1 through Node #500 are open.** The next verified claim takes
Node #1, the one after that takes Node #2, and so on — numbers are issued
sequentially in claim order, are never reused, and stay attached to their
key through address changes, moves, and reboots.

## How a claim lands here

1. Run the wrapper: `./claim-node.sh` — it generates your keypair locally
   (the private key never leaves your machine), proves possession to the
   registry, and assigns your route.
2. File a GitHub issue titled `Node claim: <your fingerprint>` with your
   node name, fingerprint, and route.
3. Your Node # is issued in claim order, added to `nodes.json` and this
   page, and — for the first 500 — named on the Dead Brands site.

## Honest bookkeeping

- The live node count is the number of nodes in `ACTIVE` state. It is
  derived from this registry — never hand-edited, never inflated.
- A node that goes dark leaves the live count while down; its entry
  records the gap. History is never silently rewritten.
- Fleet-internal nodes (the Dead Brands fleet's own machines) run under a
  separate internal numbering sequence and are **not** listed here. This
  registry is for public claims only.
- A retired or revoked number stays in the registry with its terminal
  state — numbers are never recycled onto a different key.

---

*Dead Brands, LLC — David Strausser & his AI workforce.*
