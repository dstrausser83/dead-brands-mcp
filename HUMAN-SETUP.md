# Set up your Web4 node — the human guide

You are about to claim a numbered spot in the Web4 mesh. It takes one
command and about a minute. Your computer generates a key, proves to the
registry that you hold it, and gets a route — your address on the mesh.
**The first 500 claimed nodes are named on the Dead Brands site.**

No account. No fee. No Tor required. Your private key never leaves your
machine — that's not a promise, it's how the math works: only a proof
travels, and a proof can't be turned back into a key.

---

## Before you start

You need three things, and you probably already have two of them:

- A computer that can stay on (a Raspberry Pi, an old laptop, a small
  cloud server — anything always-on is a good node).
- **Python 3.11 or newer.** Check: open a terminal and run
  `python3 --version`. No output or an error? Install it from
  [python.org](https://www.python.org/downloads/) (Windows/Mac) or your
  package manager (Linux: `sudo apt install python3 python3-venv`).
- **git.** Check: `git --version`. Missing? [git-scm.com](https://git-scm.com/downloads).

That's it. The setup installs its one remaining dependency by itself.

## Step 1 — Get the code

```bash
git clone https://github.com/dstrausser83/dead-brands-mcp.git
cd dead-brands-mcp
```

## Step 2 — Claim your node

```bash
./claim-node.sh --name "your-node-name"
```

Pick any name you like — it's the label your node is listed under.
The command will:

1. Create your keypair in `~/.web4-node/` (the private key file is
   locked down to owner-only, mode 0600).
2. Send your **public** key to the registry and answer its challenge —
   the proof-of-possession step.
3. Receive your **route** (your live mesh address) and a session.
4. Confirm you live with a REGISTER + HELLO exchange, and save your
   claim to `~/.web4-node/claim.json`.

First run only: if your Python is missing the `cryptography` package,
the launcher builds a small local virtualenv (`.venv/`) and installs it
there. Nothing on your system is changed.

## Step 3 — You're done when you see this

```
[claim] proof verified — route 123 assigned, session until ...
[claim] REGISTER ok — route 123, capabilities: HELLO, REGISTER, PING, ROOM, VISIT, EXIT, RETURN
[claim] claim saved to /home/you/.web4-node/claim.json (mode 0600)

====================================================================
  NODE CLAIMED — route 123 · fingerprint ab12cd34ef56ab78
====================================================================
```

(The route number and fingerprint will be yours, not these.)

## Step 4 — Get your name on the site

Public Node #s are issued in claim order. To take yours:

1. Open a GitHub issue on this repository titled
   **`Node claim: <your fingerprint>`** (the fingerprint is in your
   "NODE CLAIMED" banner and in `~/.web4-node/claim.json`).
2. Put three things in the issue: your **node name**, your
   **fingerprint**, and your **route**.
3. Your Node # is added to `nodes.json` / `NODES.md` in this repo and —
   for the first 500 — named on the Dead Brands site.

## Day to day

- **Prove you're live, anytime:** `./claim-node.sh --hello`
  (Sessions last about 2 hours; your key and route are permanent.
  Re-authenticating is free and instant.)
- **Back up your key.** Copy `~/.web4-node/static_key` somewhere safe
  and private. That file *is* your node. If you lose it, the identity
  is gone and the number retires with it — there is no password reset,
  by design.
- **Never share `static_key`.** Anyone holding it *is* your node.
  The public key (`static_pub`) and your fingerprint are safe to share.

## Troubleshooting

| What you see | What it means | Fix |
|---|---|---|
| `python3: command not found` | Python isn't installed | Install Python 3.11+ (see "Before you start"), open a fresh terminal, retry |
| `externally-managed-environment` or pip errors during setup | Your OS protects its system Python | Nothing to fix — the launcher's `.venv/` path handles this; if it didn't trigger, run `python3 -m venv .venv && ./.venv/bin/pip install cryptography` then `./claim-node.sh` again |
| `auth start refused: ... UNKNOWN_GUEST` | The registry didn't recognize the key presentation | Make sure you're on the current repo (`git pull`) — keys must be presented in hex, which the wrapper does for you; hand-rolled clients that send base64 get this refusal |
| `PROOF_FAILED` | The proof didn't verify | Almost always a stale or mismatched keypair: check that `static_key` and `static_pub` in `~/.web4-node/` belong together. If you copied keys between machines, copy both files. Then retry — challenges are single-use, and the wrapper always fetches a fresh one |
| `FP_COLLISION` | Your key's fingerprint already belongs to a *different* key | Stop. Do not retry with other keys. Open a GitHub issue with your fingerprint — the registry resolves collisions by hand |
| Timeouts / `transport dropped` | The network path hiccuped | The wrapper retries on its own; if it still fails, wait a minute and run the same command again. Claims are idempotent — re-running with the same key returns your existing route |
| `Permission denied` on `./claim-node.sh` | The execute bit got lost (some Windows/zip paths) | Run `bash claim-node.sh --name "your-node-name"` instead, or `chmod +x claim-node.sh` |
| It worked, but where's my Node #? | Node #s are issued in claim order when your listing issue is processed | File the Step 4 issue — name, fingerprint, route. Routes are live immediately; the public number follows the listing |

## Want the full picture?

- [INSTALL.md](INSTALL.md) — the complete install reference, including
  the advanced door-node path.
- [NODE-CLAIM.md](NODE-CLAIM.md) — the claim design: pinning, activation
  to full node status, key rotation, retirement.
- [SPEC.md](SPEC.md) — the Web4 / DarkWire protocol specification.
- [NODES.md](NODES.md) — the public registry.

---

*Dead Brands, LLC — David Strausser & his AI workforce.*
