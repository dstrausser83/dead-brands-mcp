# Installing a Web4 node

> **Read this first — honest scaffolding.** Web4 is a working proof of concept
> (v0.0001a). What exists **today** is the software that runs Node 0 and Node 1:
> a Python front-end, a Noise-protocol connector, and a guest companion client.
> What does **not** exist yet is a one-click installer. This guide documents the
> real manual path the fleet itself used, per platform, and marks clearly where
> the future installer will take over. If a step says "manual," that is the
> truth of tonight, not a placeholder for magic.

---

## What a node needs

| Requirement | Why |
|---|---|
| Python 3.11+ | Reference runtime on every platform |
| `cryptography` (pyca) | The only crypto that touches keys (Noise primitives, X25519) |
| Tor (daemon, SOCKS5 on localhost) | Node 0-class nodes serve the public door and fetch exits through Tor |
| A static X25519 keypair | The node's identity — generated locally, never transmitted (see NODE-CLAIM.md) |
| An always-on home (any always-on box works) | A node that sleeps is a door that closes |

Two node shapes:

- **Door node (Node 0-class):** runs the front-end + Tor hidden service + exit
  fetcher. This is the full stack.
- **Guest-only participation:** you don't need a node to *use* Web4 — the
  wrapper companion client plus an issued guest key is enough (see "Guests"
  below). Run a node when you want to *be* infrastructure.

---

## Raspberry Pi (the Node 0 path — proven)

Node 0 is a Raspberry Pi 5 running Debian 12. This is the exact shape that runs
in production tonight.

1. **Base system.** Raspberry Pi OS / Debian 12, updated. Give the Pi a stable
   address on your network (DHCP reservation is fine). No router port
   forwarding — a Web4 node never asks for one.
2. **Tor.** Install the `tor` package; enable a SOCKS5 listener on localhost
   (default `127.0.0.1:9050`) and, for a door node, a hidden service pointing
   at the front-end's localhost port. The hidden service keys Tor generates
   are node secrets — custody rules in SPEC.md §4 apply.
3. **Python environment.** `python3 -m venv` a dedicated environment; install
   `cryptography`. Pin versions in your own notes; the fleet's Pi runs
   cryptography 50.x.
4. **Node software.** Clone this repository; place the front-end, connector,
   and DarkWire endpoint under the node's service user. All services bind
   **127.0.0.1** (front-end, connector admin surfaces) or the node's mesh
   address (DarkWire listener) — never `0.0.0.0`.
5. **Keys.** Generate the node's static keypair into a `0600` keys directory.
   Back up a sealed copy with your organization. Never print private keys.
6. **Claim your spot.** Follow NODE-CLAIM.md: register the public key, receive
   your Node #, complete the pinning exchange.
7. **Run it.** Today: run the components under your init system of choice
   (the fleet uses systemd units with memory/CPU caps so a node can never
   starve the box's other jobs). The installer will generate these units for
   you when it lands.

## Linux (generic)

Identical to the Pi path — the reference stack is distribution-agnostic
Python. Notes:

- Any modern distro with Python 3.11+ and a Tor package works; a small cloud
  VM is a fine node (Node 1 is one).
- Prefer a dedicated unprivileged user for the node services.
- Keep the same binding rule: localhost for services, mesh address for the
  DarkWire listener, no public ports beyond what your hidden service needs
  (which is none — hidden services are outbound-only).

## Windows

**Honest status: manual/experimental tonight.** The components are pure Python
plus the pyca `cryptography` wheel, and Tor is available for Windows, so the
stack *can* run — but the fleet has not production-proven a Windows node, and
this guide will not pretend otherwise.

1. Install Python 3.11+ (python.org) and Tor (Tor Browser's bundled tor, or
   the standalone Windows expert bundle).
2. Create a venv; `pip install cryptography`.
3. Run the components from a checkout of this repository, binding to
   localhost as on every platform.
4. The future installer will ship a proper Windows service wrapper; until
   then, run under your own supervisor and expect rough edges. Reports from
   Windows testers are genuinely useful — file them as issues.

## Mac

**Honest status: manual/experimental tonight** (same caveat as Windows).

1. Install Python 3.11+ (Homebrew is fine) and Tor (`brew install tor`).
2. Create a venv; `pip install cryptography`.
3. Run the components from a checkout; localhost binding rules apply.
4. The future installer will ship a launchd plist; until then, run under your
   own supervisor.

---

## Guests (no node required)

To *visit* the Underground through the wrapper lane:

1. Generate an X25519 keypair locally (the companion client can do this).
2. Receive an issued guest route (the registry is closed — guest keys are
   issued, not self-minted; see SPEC.md §5).
3. Run the **wrapper companion client** (Python + `cryptography`, stdlib
   otherwise) with your key directory. It performs the proof-of-possession
   handshake — your private key never leaves your machine — and speaks the
   verbs: HELLO, ROOM, VISIT, EXIT, RETURN.
4. Present your key in **hex form** (v0.0001a registry matching is hex-only).

Tor-native guests can equally use the mesh-door connector over the onion with
the same keypair.

## What the installer will do (future build)

One command per platform that: creates the service user and venv, installs
dependencies, generates keys with correct custody permissions, writes the
init units, runs the NODE-CLAIM flow interactively, and finishes with a live
handshake proof against Node 0 — the same proof bar the fleet set for itself.
Until it ships, this document is the path, and it is the real one.

---

*Dead Brands, LLC — David Strausser & his AI workforce.*
