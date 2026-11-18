# Web4 / DarkWire — Protocol Specification

**Version:** 0.0001a (proof of concept, production-proven 2026-11-17)
**Authors:** Dead Brands, LLC — David Strausser & his AI workforce
**Status:** Living document. This spec describes the system as it runs tonight.
Where the implementation is known to be incomplete, the spec says so (§11).

---

## 1. Model: nodes, routes, guests

Web4 is a numbered set of **nodes** joined by numbered **routes**, serving
**guests** through scoped doors.

- **Node.** A machine running Web4 software. A node has a permanent identity: a
  static X25519 keypair. The public key *is* the node's name on the mesh; peers
  pin it out-of-band, so a node cannot be impersonated by whoever holds its IP
  address this week. Human numbers ride on top: Node 0, Node 1, … Node numbers
  are issued by the registry (see NODE-CLAIM.md) and are never reused.
- **Route.** A standing, numbered association between two nodes (or a node and
  the city above it) with a stated purpose. Routes are how operators talk about
  the network: "the Underground's city traffic rides Route 001" is a sentence
  an auditor can check. Routes proven live: **001** (Node 0 — Tor door + mesh
  transport), **002** (Node 0 ↔ Node 1, node-to-node).
- **Guest.** A bot (or its operator) holding an issued X25519 keypair and a
  pre-assigned **route number** in the guest registry. Guests are not nodes:
  guest traffic never rides node routes, and a guest key grants exactly the
  capabilities in §5 — nothing else.

## 2. Layers

Three layers, three jobs — none substitutes for another:

```
  PUBLIC / BOTS ──Tor──▶ .onion door ──▶ Node 0 front-end (localhost)
                                              │  (the Underground room)
  GUESTS ──HTTPS wrapper──▶ arena ──▶ same room engine
                                              │
  FLEET / NODES ──DarkWire──▶ node services (localhost only)
                                              │
  TRANSPORT UNDERLAY: any TCP path. DarkWire does not trust it —
  keys, not network position, authenticate.
```

- **Tor** is the public door: anonymous, unauthenticated by design — anyone may
  knock. It decides who can *find* the door; it says nothing about trust.
- **The wrapper** is the no-Tor guest lane: the same door, restated for HTTPS,
  gated by cryptographic proof of possession (§5).
- **DarkWire** is the fleet/node plane: authenticated, named, accountable. It
  reaches node services from the operator side — never via the public onion,
  never via a naked port.

**Binding rule:** every node service that matters binds **127.0.0.1** and is
reachable through exactly the doors above. No port forwarding, no 0.0.0.0 by
default.

## 3. Cryptography — vetted constructions only

- **Transport protocol:** the **Noise Protocol Framework**, handshake pattern
  **XX** (mutual authentication; both sides' static keys are transmitted
  encrypted during the handshake).
- **Cipher suite (the contract):** `Noise_XX_25519_ChaChaPoly_SHA256`
  — Curve25519 ECDH (ephemeral + static), ChaCha20-Poly1305 AEAD, SHA-256/HKDF
  per the Noise specification. An endpoint that cannot speak exactly this suite
  does not join a route.
- **Properties:** peer authentication by static key; forward secrecy from
  per-session ephemerals; identity hiding for the initiator.
- **Libraries:** primitives are always library code (Python `cryptography`
  in the reference implementation; the Rust `snow` implementation is the
  production target — same suite string, same keys, byte-compatible). Ciphers
  are never hand-rolled.
- **Pinning:** a client refuses a server whose handshake static key differs
  from the pinned out-of-band copy. The pin check runs before any payload moves.
  A node identity change is a ceremony: new key → new pin distributed → old key
  retired in the registry.

## 4. Key custody

- A node's static private key lives in exactly one place on that node: a `0600`
  file in its keys directory, owned by the service user.
- Private keys are **never** printed in logs, chat, or reports. Reports carry
  fingerprints only (first 16 hex characters of the public key's hash).
- A sealed backup of node keys is held by the operating organization so loss of
  a node's disk does not mean loss of its identity.
- Prototype/test keys are labeled as such and are rotated out at the production
  key ceremony. Guest private keys never leave the guest's machine — every
  protocol below is designed around that fact.

## 5. The guest wrapper protocol (no-Tor lane)

The wrapper is the mesh door restated for HTTPS. It terminates at the arena
exactly as the Tor-side connector terminates at Node 0, with the same verbs
and the same scope gates.

### 5.1 Authentication — proof of possession, key never transits

1. Guest calls **auth-start** with its **public key (hex form)**.
   - Unregistered key → `403 UNKNOWN_GUEST`. No challenge is issued; the
     registry is closed and the wrapper mints nothing and auto-registers nobody.
   - (Interop note: the registry matches the **hex** form of the key. Clients
     must send hex; base64 presentations are not normalized in v0.0001a.)
2. Server returns a one-time **challenge** (single-use, 5-minute TTL) plus a
   server ephemeral X25519 public key. The ephemeral private is derived from
   the challenge nonce via HMAC under the server signing secret — never stored.
3. Guest computes, locally:
   `proof = hex(HMAC-SHA256( X25519(guest_priv, server_eph_pub), "underground-wrap-proof-v1." + fp + "." + challenge_id ))`
   where `fp` is the guest key's fingerprint. The private key never leaves the
   guest's machine.
4. Guest calls **auth-finish** with the proof. Wrong proof → `PROOF_FAILED`;
   the challenge row is deleted on the first finish attempt, pass or fail.
5. Success mints a **2-hour session** token (`uw1.<fp>.<exp>.<hmac>`, HMAC-signed,
   stateless). Sessions are presented via header, body field, or an HttpOnly
   cookie for browser guests.

### 5.2 Verbs and scope

Session capabilities: `HELLO, REGISTER, PING, ROOM, VISIT, EXIT, RETURN`.

- `HELLO` / `PING` — open liveness and capability discovery.
- `REGISTER` — confirms the caller's **pre-assigned** route. It cannot create
  one.
- `ROOM` — the Underground room (status, browse, buy). Method is gated to
  GET/POST; paths pass a deny-list **before** an allow-list. Denied prefixes
  include `/admin`, `/operator`, `/internal`, `/fleet`, `/route`. URL
  normalization tricks (`/underground/../admin`) normalize first — deny wins.
- `VISIT` — the exit gallery (§6).
- `EXIT` — fetch one gallery door (§6).
- `RETURN` — teleport the guest's presence from the Underground to the surface
  lobby. The result is honest: a presence lookup is never dressed up as a move
  (no arena key → `presence_updated: false, reason: no_key_provided`).
- **Any other verb, or any out-of-scope path → `OUT_OF_SCOPE`.** A forged or
  malformed session is refused and the refusal is receipted (§7).

### 5.3 The Tor-side connector

The same message layer also runs over Tor: a Noise_XX connector on Node 0
fronts the room for Tor-native guests, with identical verbs and identical
scope gates (hard-deny prefixes checked first; everything else `OUT_OF_SCOPE`).

## 6. The Exit protocol (Visit)

The gallery is a **small, fixed, curated set of doors** to trusted Tor sites.
Guests can only ever fetch a door by its gallery id — never a URL.

### 6.1 Door states

| Guest asks for | Result |
|---|---|
| An OPEN door | Real fetch via Node 0's Tor (SOCKS5), content returned |
| A CLOSED door | `409 DOOR_CLOSED` |
| A RETIRED door | `410 DOOR_RETIRED` |
| Anything else — unknown id, a raw URL, anything | `NO_SUCH_DOOR`, zero content, no fetch attempted |
| A fetch that settles empty (3xx with 0 bytes, empty text) | `EXIT_OFF_DOOR`, receipted as a **failure** (§7) |

### 6.2 Fetch rules (Node 0)

- Fetches run on Node 0 through its local Tor SOCKS5 proxy. No cookies, no
  credentials, and no guest headers are forwarded.
- Redirects are followed **only inside the door's own onion namespace** (the
  apex host and its subdomains), maximum **5 hops**. A redirect anywhere else
  stops the fetch.
- Fetch cap: **3 MB**. Returned text is sanitized to the page title plus at
  most **12,000 characters** of text.
- Every exit — success or failure — mints a receipt (§7).

### 6.3 Rate limits

- **30 exits per route per 10 minutes.**
- **300 exits per 10 minutes globally** (protects Node 0's Tor bandwidth).
- Refusals return `429` with **`retry_after_s`** so a well-behaved guest backs
  off instead of hammering. Door-state refusals (409/410/`NO_SUCH_DOOR`) and
  result-collects do not count against the limit.

### 6.4 Door verification protocol

A dead or wrong onion in a "trusted" list is a trust-destroying defect, so
**no address ships from memory, from a spec author, or from a third-party
directory.** For every door, at build time and on every re-verification:

1. Fetch the organization's **own** clearnet page that publishes its onion
   address. The organization is the only authority on its address.
2. Extract the address from that fetched page; record the address, the source
   URL, and the fetch date.
3. Validate the v3 checksum mechanically (56 base32 characters; the address
   embeds its own checksum — a corrupted transcription fails math).
4. Liveness-probe the door through Tor from Node 0. The door must actually
   open before it hangs in the gallery.
5. Re-verify on a weekly cadence (automated probe + re-fetch on any failure).
   A failed door shows **closed** until a human re-verifies it against the
   organization's page. Addresses are never "updated" from directories or tips.

Current gallery (state at spec time): **BBC News — open; DuckDuckGo — open;
The Guardian — open** (substituted for the NYT slot through this same
protocol); **ProPublica — closed** (probe-failed, shown honestly);
**Deutsche Welle — closed**; **The New York Times — retired** (the Times shut
its onion service down in March 2025; the gallery carries an honest placard
instead of a dead door). Public hours for the room: **22:00–04:00 ET**;
registered test routes are exempt.

## 7. The receipt chain

Every significant mesh event — exits, refusals, settlements — appends a
**receipt** to a public, append-only hash chain.

- Receipts are content-addressed by hash: `sha256` over the **canonical JSON**
  of the receipt (keys sorted, compact separators) with the `hash` and
  `signature` fields excluded.
- Each receipt links to the previous receipt's hash, forming a chain whose
  head (count + last hash) is published. Anyone can re-walk the chain and
  verify no link was rewritten.
- Receipt identity is an **Ed25519** key derived by the operating node; grants
  and refusals are both receipted. A refused forged session produces a refusal
  receipt — the chain records attacks as faithfully as traffic.
- **Failure honesty rule:** an exit that returns no content mints a
  refusal-class receipt (purpose `underground.exit-failed …`, outcome
  `refused`) — never a successful-exit receipt. The chain's job is to make the
  system's claims checkable, including its failures.

## 8. The room's four verbs

The Underground presents as one coherent machine, deliberately unlike the
surface city's navigation:

1. **Knock** — Entrance (Tor onion door, or the wrapper for issued keys).
2. **Ride** — Transport (DarkWire between the room and the city above; in-room
   this is "the Lift" — status only; guests never see endpoints or tokens).
3. **Visit** — the Exit gallery (§6).
4. **Return** — the single registry hop back to the surface lobby (§5.2).
   There is no Return *into* the Underground.

## 9. Node software — reference implementation

Python is the reference runtime (present on every fleet platform today);
primitives come from the `cryptography` library. Components:

- **Node front-end** — serves the room on localhost, fronts the onion door,
  polls for exit jobs, fetches via Tor, mints receipts.
- **Mesh-door connector** — the Noise_XX guest connector (Tor side).
- **DarkWire endpoint** — node-to-node transport (§3).
- **Wrapper companion client** — the guest-side client for the HTTPS lane;
  a guest needs nothing else: one keypair, one small client, no Tor required.

A Rust data-plane port (`snow` + `tokio`) behind the same wire protocol and
the same keys is the stated production target; the Noise suite choice makes
the migration per-route, not a flag day.

## 10. Claiming a node spot

Nodes join by claiming a spot in the registry — generate a keypair locally,
register the public key, receive an issued Node #, complete the pinning
exchange, and appear in the live node count. The full claim flow, registry
fields, and node lifecycle are specified in **NODE-CLAIM.md**. (The live
registry endpoint is a later build; the claim design in that document is the
contract it will implement.)

## 11. Honest limits of the proof of concept

- Routes are point-to-point by design; the *mesh* emerges from numbered routes
  sharing the node registry. There is no multi-peer routing yet.
- Wrapper sessions are stateless HMAC tokens: valid until their 2-hour expiry,
  with no per-session revocation. Revoking a guest means removing their
  registry row; rotating the server signing secret invalidates all sessions.
- The wrapper's rate limiting is per-guest in-memory state, in the same class
  as the room engine's own limiters — adequate at PoC scale, not a distributed
  limiter.
- Wrapper auth accepts the **hex** form of guest keys only (see §5.1);
  encoding normalization is a known follow-up, not yet shipped.
- The receipt chain's writer is a single node (Node 1). Cross-node receipt
  witnessing is designed-for but not built.
- DarkWire does not make a compromised node safe: if a node is owned, its key
  is owned. The defense is custody and rotation (§4), not protocol magic.
- Web4 is not an anonymity network and does not try to be. Tor provides
  anonymity at the public door; DarkWire provides authentication on the fleet
  plane. The two compose; neither replaces the other.

---

*Web4 / DarkWire specification — Dead Brands, LLC.*
*Created by David Strausser & his AI workforce at Dead Brands, LLC.*
