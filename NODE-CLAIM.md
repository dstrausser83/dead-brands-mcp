# Claiming a node spot — the NODE-CLAIM design

> **Status: design specification.** The flow below is the contract for how a
> machine becomes a numbered Web4 node. The **live registry endpoint is a
> later build** — tonight, claims are processed by the Dead Brands fleet
> against this design. Nothing in this document describes an endpoint that
> exists yet, and it is written so the endpoint, when built, implements
> exactly this.

---

## The idea

A Web4 node is not an IP address or a hostname. It is a **key with a number**.
Claiming a spot means: your public key enters the registry, the registry
issues you a **Node #**, and your node joins the **live node count** — the
public tally of machines carrying the mesh. Node numbers are issued
sequentially, are never reused, and stay attached to their key through
address changes, moves, and reboots. Node 0 is a Raspberry Pi in Pennsylvania
because it claimed first and proved it live. Node 1 followed. The next number
is whoever claims and proves next.

## The flow

```
 1. GENERATE   Node operator generates a static X25519 keypair locally.
               The private key never leaves the machine. Ever.
        │
 2. CLAIM      Operator submits a claim: public key + node metadata (§Fields).
        │
 3. ISSUE      Registry validates the claim (key well-formed, not already
               registered, name not squatting a fleet node) and issues the
               next sequential Node #. State: CLAIMED.
        │
 4. PROVE      Proof of possession: the claimant signs/answers a registry
               challenge with the claimed key (same proof-of-possession
               pattern as the guest wrapper, SPEC.md §5.1). A claim that
               cannot prove possession of the private key dies here.
               State: VERIFIED.
        │
 5. PIN        Pinning exchange: the new node's public key + fingerprint are
               distributed to existing nodes' pin lists, and the new node
               receives the current pin list. Mutual, out-of-band confirmed.
        │
 6. ACTIVATE   First live DarkWire handshake with Node 0 (pin check passing
               both directions). State: ACTIVE — the node joins the live
               node count and may be assigned routes.
```

## Registry fields

A claim carries exactly these fields — nothing more is asked, nothing else is
stored:

| Field | Meaning |
|---|---|
| `public_key` | The node's static X25519 public key (hex). Its fingerprint (first 16 hex of the key hash) is the node's short identity in reports. |
| `node_name` | Human label chosen by the operator (e.g. a handle or box name). Display only; the key is the identity. |
| `platform` | `raspberry-pi` / `linux` / `windows` / `mac` / `other` — used for install support and honest capability notes. |
| `node_class` | `door` (serves a public door / fetches exits) or `relay` (transport only). Door nodes accept the exit-verification duties in SPEC.md §6.4. |
| `contact` | A reachable operator contact for pinning ceremonies and outage notes. Never published. |
| `claimed_at` | Registry timestamp of the claim. |
| `node_number` | **Issued by the registry** at step 3 — sequential, never reused, never chosen by the claimant. |
| `state` | `CLAIMED` → `VERIFIED` → `ACTIVE`; terminal states `RETIRED` (operator withdrew; number stays retired with the key) and `REVOKED` (key compromise; pin lists drop it fleet-wide). |

## The live node count

The live node count is the number of nodes in `ACTIVE` state. It is derived
from the registry — never hand-edited, never inflated. A node that goes dark
does not silently vanish from history: it leaves the live count while down
and its registry entry records the gap. The count's honesty rule is the same
as the receipt chain's: the number is checkable or it is not published.

## Routes

An ACTIVE node may be assigned **routes** (numbered, purpose-stated
associations — SPEC.md §1). Route assignment is a registry act, recorded with
both endpoint node numbers and the route's purpose. Guest routes (the
100-series in the current registry) are a separate series from node numbers
and never collide with them.

## Key compromise & rotation

- Suspected compromise → operator notifies the registry → node moves to
  `REVOKED`, pins are dropped, routes re-issued.
- Planned rotation → new keypair, new claim referencing the old node number;
  the registry links them, the number carries over **only** through this
  ceremony (numbers follow proven continuity, not requests).
- Loss of a private key without backup = loss of the node identity. The
  number retires with it. Back up your keys (SPEC.md §4).

## What claiming is not

- Not a purchase. No fee, no token, no staking — a key, a proof, a handshake.
- Not anonymous. Nodes are named and accountable by design (SPEC.md §2);
  anonymity lives at the public Tor door, for guests, not for infrastructure.
- Not a promise of traffic. A node joins the count and becomes eligible for
  routes; the mesh grows by proof, not by press release.

---

*Dead Brands, LLC — David Strausser & his AI workforce.*
*Node 0 donated by David Strausser, CEO, Dead Brands, LLC.*
