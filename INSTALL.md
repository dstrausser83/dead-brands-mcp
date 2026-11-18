# Installing a Web4 node — the complete reference

> **The short path:** if you just want your node claimed and live, you
> don't need most of this document. Clone the repo and run
> `./claim-node.sh` — that's the install. This file is the complete
> reference behind that one command: prerequisites, verification,
> troubleshooting, and the advanced door-node path.
> Humans: [HUMAN-SETUP.md](HUMAN-SETUP.md) is the friendlier version of
> the same steps. Agents: [AGENT-SETUP.md](AGENT-SETUP.md).

---

## What "installing a node" means today

A Web4 node is a **key with a number**. Installing one means:

1. Your machine generates a static X25519 keypair — its permanent
   identity. The private key never leaves the machine.
2. The key is registered with the Web4 registry through the wrapper
   (proof of possession, SPEC.md §5) and assigned a **route**.
3. Your claim is published in the public registry ([nodes.json](nodes.json))
   with a sequential **Node #** — the first 500 claimed nodes are named
   on the Dead Brands site.

Two participation shapes build on that identity:

- **Node (claimed key + route):** what the one-command install gives
  you. You hold a mesh identity, can authenticate to the wrapper lane
  (HELLO / REGISTER / PING / ROOM / VISIT / EXIT / RETURN), and are
  listed in the registry.
- **Door node (Node 0-class):** additionally runs the front-end, a Tor
  hidden service, and the exit fetcher — serving the public door. This
  is the full stack Node 0 runs. It is a manual build today (see
  "Advanced: the door-node stack" below) and its activation is the
  fleet-assisted pinning step in [NODE-CLAIM.md](NODE-CLAIM.md).

Guests who only want to *visit* the Underground don't need either: any
keypair claimed through the wrapper is enough to enter as a guest.

## Prerequisites

| Requirement | Why | Check |
|---|---|---|
| Python 3.11+ | The wrapper and reference stack are Python | `python3 --version` |
| `cryptography` (pyca) | X25519 + HMAC primitives — the only crypto that touches keys | Installed automatically by the launcher if missing (local `.venv/`) |
| git | To fetch this repository | `git --version` |
| An always-on home | A node that sleeps is a door that closes — any always-on box works (Pi, old laptop, small VM) | — |
| Tor (door nodes only) | Serves the public door and fetches exits | `tor --version` |

No router port forwarding is ever required. No account, no fee.

## Install

```bash
git clone https://github.com/dstrausser83/dead-brands-mcp.git
cd dead-brands-mcp
./claim-node.sh --name "your-node-name"
```

What the launcher + wrapper do, in order:

1. **Runtime check.** If `cryptography` is importable, the wrapper runs
   directly. Otherwise a one-time virtualenv is created in `.venv/` and
   the package installed there — nothing system-wide is touched.
2. **Key generation.** A static X25519 keypair is written to the key
   directory (default `~/.web4-node/`, override with `--keydir` or
   `$WEB4_NODE_HOME`):
   - `static_key` — 32 raw bytes, mode `0600`. **The private key.**
   - `static_pub` — 32 raw bytes. The public key.
   If a keypair already exists there, it is reused — re-running the
   install never rotates your identity.
3. **Registration + proof.** The wrapper POSTs your public key (hex) to
   `https://mcp.deadbrands.co/underground/wrap/auth`, receives a
   one-time challenge (5-minute, single-use) and a server ephemeral key,
   computes the proof locally
   (`HMAC-SHA256(X25519(private, server_ephemeral), "underground-wrap-proof-v1." + fingerprint + "." + challenge_id)`),
   and returns only the proof. The registry verifies it and assigns
   your route (self-registered routes start at 110; the issued block
   101–109 predates the open registry).
4. **Confirmation.** REGISTER + HELLO are exchanged over the fresh
   ~2-hour session so you see the route and capabilities confirmed by
   the live registry, and the claim is saved to `claim.json` (mode
   `0600`) in the key directory.

Options: `./claim-node.sh --help` lists them all (`--name`, `--keydir`,
`--base`, `--hello`, `--dry-run`).

## Verify

You're installed when **all three** hold:

1. The claim run ends with the banner:
   `NODE CLAIMED — route <N> · fingerprint <FP>`
2. `./claim-node.sh --hello` prints `[claim] HELLO ok — route <N>` with
   the same route — a fresh session against the live registry.
3. `~/.web4-node/claim.json` exists, its `route` and `fingerprint`
   match the banner, and `static_key` has mode `600`
   (`stat -c '%a' ~/.web4-node/static_key`).

Pre-flight without claiming anything: `./claim-node.sh --dry-run`
generates a throwaway keypair in a temp directory, fabricates the
server side of the challenge, and verifies the proof transcript from
both sides. No network, nothing registered.

## Get listed (your public Node #)

Routes are live the moment the claim verifies. Public Node #s are
issued sequentially in claim order and published in
[nodes.json](nodes.json) / [NODES.md](NODES.md):

1. Open a GitHub issue titled `Node claim: <your fingerprint>`.
2. Include your node name, fingerprint, and route.
3. Your Node # is added to the registry and — for the first 500 claimed
   nodes — your node is named on the Dead Brands site.

## Day-to-day operations

- **Re-authenticate:** `./claim-node.sh --hello` (sessions last ~2h;
  identity and route are permanent).
- **Speak the wrapper verbs:** the fleet's companion client
  (`underground_wrap_client.py`, described in SPEC.md §9) uses the same
  key directory format — keys claimed here work there unchanged.
- **Back up the key:** copy `static_key` to sealed storage. Loss of the
  private key without a backup is loss of the node identity; the number
  retires with it (NODE-CLAIM.md).
- **Rotate / retire:** planned rotation and retirement ceremonies are
  specified in NODE-CLAIM.md — numbers follow proven continuity, never
  requests.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `python3: command not found` | Install Python 3.11+ (python.org, or `sudo apt install python3 python3-venv` on Debian/Ubuntu), reopen the terminal |
| Wrapper self-test (`--dry-run`) fails | Local crypto/environment defect — do not attempt a live claim; report the full output as a GitHub issue |
| `UNKNOWN_GUEST` at auth start | Key presented in a non-hex encoding by a hand-rolled client; the wrapper always sends hex. If the *wrapper* gets this, `git pull` — you may be on a stale checkout |
| `PROOF_FAILED` | `static_key` / `static_pub` are not a matching pair (partial copy between machines). Restore both from the same source, or start fresh in a new keydir and file a listing note |
| `FP_COLLISION` | Fingerprint bound to a different key — stop and open a GitHub issue; never retry with generated keys to "get around" it |
| Timeouts, `transport dropped`, occasional HTTP 5xx at auth start | Transient network path. The wrapper retries whole auth rounds (challenges are single-use; it never re-sends a proof). Wait a minute and re-run — claims are idempotent per key |
| Route changed between runs | It shouldn't — routes are keyed to your public key. If it did, you're using a different keydir: check `--keydir` / `$WEB4_NODE_HOME` |
| Windows: script won't execute | Run `bash claim-node.sh ...` (Git Bash or WSL). Windows nodes are manual/experimental tonight — see below |

## Advanced: the door-node stack (Node 0-class)

A door node additionally runs: the front-end (the Underground room on
localhost), a Tor hidden service pointing at it, the DarkWire connector,
and the exit fetcher. Node 0 — a Raspberry Pi 5 on Debian 12 — is the
proven shape. Honest status: **this stack is assembled manually today**;
the one-command installer covers the claim + identity layer, and door
activation completes through the pinning exchange in NODE-CLAIM.md.

1. **Base system.** Debian 12 (Pi OS or generic). Stable LAN address
   (DHCP reservation is fine). No port forwarding.
2. **Tor.** Install `tor`; SOCKS5 on `127.0.0.1:9050`; a hidden service
   directed at the front-end's localhost port. Hidden-service keys are
   node secrets — custody rules in SPEC.md §4.
3. **Python environment.** Dedicated venv + service user; install
   `cryptography` (the fleet's Pi runs 50.x).
4. **Identity.** Claim first (this document, above) — the door serves
   under the same static keypair.
5. **Binding rule.** Every service binds `127.0.0.1` or the node's mesh
   address — never `0.0.0.0`. Hidden services are outbound-only; a door
   node opens no public ports.
6. **Run it.** Under your init system (the fleet uses systemd units
   with memory/CPU caps). Then complete NODE-CLAIM steps 5–6 (pin +
   activate) with the fleet: your key enters existing nodes' pin lists,
   you receive the current pin list, and the first live DarkWire
   handshake with Node 0 (fingerprint `8a0d8d0ae512b9da`) activates the
   node.

**Windows / Mac door nodes:** the components are pure Python + the pyca
wheel and Tor exists on both, so the stack *can* run — but the fleet
has not production-proven either, and this guide won't pretend
otherwise. Claiming a node (the install above) works on both today;
door duty is proven on Linux/Pi only. Reports from Windows/Mac testers
are genuinely useful — file them as issues.

## Uninstall

Delete the checkout and the key directory (`~/.web4-node/`). Understand
what that means: without a backup of `static_key`, your node identity
is unrecoverable and its number retires. To retire *on the record*
(number marked RETIRED in the registry instead of silently dark), open
a GitHub issue from the claim before deleting anything.

---

*Dead Brands, LLC — David Strausser & his AI workforce.*
