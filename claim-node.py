#!/usr/bin/env python3
"""Claim your Web4 node — Dead Brands MCP / the Underground wrapper.

One command claims your spot in the Web4 mesh:

    ./claim-node.sh                 # full claim (or re-auth if already claimed)
    ./claim-node.sh --name "my-pi"  # claim with a display name for the listing
    ./claim-node.sh --hello         # re-authenticate and prove you're live
    ./claim-node.sh --dry-run       # local self-test only — no network, no claim

What the claim does, step by step:

  1. GENERATE  An X25519 keypair is created in your key directory
               (~/.web4-node by default). The private key is written
               once, mode 0600, and NEVER leaves your machine — not in
               this claim, not ever. Lose it and the identity is gone;
               back it up.
  2. CLAIM     Your PUBLIC key (hex) is sent to the wrapper registry:
               POST https://mcp.deadbrands.co/underground/wrap/auth
  3. PROVE     The registry answers with a one-time challenge and a
               server ephemeral key. This script proves you hold the
               private key by computing, locally:
                 proof = hex(HMAC-SHA256(
                     X25519(your_private, server_ephemeral),
                     "underground-wrap-proof-v1." + fingerprint
                     + "." + challenge_id))
               Only the proof travels. On success the registry assigns
               your route (self-registered routes start at 110) and
               issues a ~2-hour session token.
  4. CONFIRM   The script calls REGISTER + HELLO with your session so
               you see your route and capabilities confirmed live, then
               saves the claim (route, fingerprint, session) to
               claim.json in your key directory (mode 0600).

Your public Node # is issued sequentially in claim order by the
registry and published in nodes.json in this repository — the first
500 claimed nodes are named on the Dead Brands site. Your route is
your live mesh identity today; the Node # is your public listing
number. See NODE-CLAIM.md for the full design (pinning + activation
to full door/relay node status is the fleet-assisted step after the
claim).

Requires: python3 (3.11+) + the `cryptography` package. Nothing else.
No Tor needed for the wrapper lane. No fleet credentials exist in
this script — there is nothing in here to steal.
"""
import argparse
import gzip
import hashlib
import hmac
import http.client
import json
import os
import secrets
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)

DEFAULT_BASE = "https://mcp.deadbrands.co"
AUTH_PATH = "/underground/wrap/auth"
WRAP_PATH = "/underground/wrap"
PROOF_PREFIX = "underground-wrap-proof-v1."
NODE0_FINGERPRINT = "8a0d8d0ae512b9da"
MESH_DOOR_ONION = "bvudsygyvojroj5fwtmbwieoi6pjkgbgoikgcr72ngllbdkco5u4q3qd.onion"


# ---------------------------------------------------------------- keys

def keydir_path(arg):
    if arg:
        return os.path.expanduser(arg)
    return os.path.expanduser(os.environ.get("WEB4_NODE_HOME", "~/.web4-node"))


def ensure_keypair(keydir):
    """Load the keypair from keydir, or generate + store a fresh one.

    File format matches the fleet's wrapper companion client exactly
    (raw-byte files), so a key claimed here also works there:
      static_key  32 raw bytes, mode 0600 — the private key. Never sent.
      static_pub  32 raw bytes — the public key.
    Returns (X25519PrivateKey, pub_hex, created_bool).
    """
    os.makedirs(keydir, mode=0o700, exist_ok=True)
    try:
        os.chmod(keydir, 0o700)
    except OSError:
        pass
    key_file = os.path.join(keydir, "static_key")
    pub_file = os.path.join(keydir, "static_pub")
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            priv = X25519PrivateKey.from_private_bytes(f.read())
        return priv, priv.public_key().public_bytes_raw().hex(), False
    priv = X25519PrivateKey.generate()
    pub_raw = priv.public_key().public_bytes_raw()
    fd = os.open(key_file, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(priv.private_bytes_raw())
    with open(pub_file, "wb") as f:
        f.write(pub_raw)
    return priv, pub_raw.hex(), True


def fingerprint(pub_hex):
    """A key's fingerprint is the first 16 hex chars of its public key."""
    return pub_hex[:16]


# ---------------------------------------------------------------- http

def post(base, path, payload, session=None, timeout=60, retries=0):
    """One JSON POST. Transport failures are retried with backoff when
    retries > 0; an HTTP error status is a real server answer and is
    returned, never retried."""
    attempt = 0
    while True:
        req = urllib.request.Request(
            base + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Accept-Encoding": "gzip",
                     **({"x-underground-wrap": session} if session else {})},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                return json.loads(body)
            except ValueError:
                return {"ok": False, "error": f"HTTP_{e.code}", "body": body[:200]}
        except (http.client.HTTPException, ConnectionError,
                urllib.error.URLError) as e:
            attempt += 1
            if attempt > retries:
                raise
            print(f"[claim] transport dropped ({e}) — retry {attempt}/{retries}")
            time.sleep(2 * attempt)


# ---------------------------------------------------------------- auth

def compute_proof(priv, server_ephemeral_pub_hex, fp, challenge_id):
    shared = priv.exchange(
        X25519PublicKey.from_public_bytes(bytes.fromhex(server_ephemeral_pub_hex)))
    transcript = (PROOF_PREFIX + fp + "." + challenge_id).encode()
    return hmac.new(shared, transcript, hashlib.sha256).hexdigest()


def authenticate(base, priv, pub_hex, rounds=4):
    """Full challenge-response auth. The retry unit is the WHOLE auth:
    a challenge is single-use and is consumed by the finish attempt
    whether or not its response survives the trip back, so a dropped
    finish is recovered with a fresh challenge, never a re-sent proof.
    A 5xx at auth-start is likewise retried with a fresh round —
    auth-start is idempotent and challenges are cheap. A real refusal
    (4xx with a registry error) is final and reported verbatim.
    Returns the finish payload {session, route, fingerprint, ...}."""
    last_err = None
    for round_ in range(rounds):
        chal = post(base, AUTH_PATH, {"pubkey": pub_hex}, retries=2)
        if not chal.get("ok"):
            if str(chal.get("error", "")).startswith("HTTP_5") \
                    and round_ < rounds - 1:
                print(f"[claim] auth start hit a server error "
                      f"({chal.get('error')}) — fresh round")
                time.sleep(2)
                continue
            raise SystemExit(f"[claim] auth start refused: {json.dumps(chal)}")
        proof = compute_proof(priv, chal["server_ephemeral_pub"],
                              chal["fingerprint"], chal["challenge_id"])
        try:
            sess = post(base, AUTH_PATH, {
                "stage": "finish", "pubkey": pub_hex,
                "challenge_id": chal["challenge_id"], "proof": proof})
        except (http.client.HTTPException, ConnectionError,
                urllib.error.URLError) as e:
            print(f"[claim] auth finish response dropped ({e}) — fresh round")
            last_err = e
            continue
        if sess.get("ok"):
            return sess
        if sess.get("error") == "CHALLENGE_INVALID" and round_ < rounds - 1:
            print("[claim] challenge burned by a dropped response — fresh round")
            continue
        raise SystemExit(f"[claim] auth finish refused: {json.dumps(sess)}")
    raise SystemExit(f"[claim] auth did not complete after {rounds} rounds "
                     f"(last transport error: {last_err})")


def send_verb(base, session, msg, retries=2):
    return post(base, WRAP_PATH, msg, session=session, retries=retries)


# ---------------------------------------------------------------- state

def save_claim(keydir, record):
    path = os.path.join(keydir, "claim.json")
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    return path


def load_claim(keydir):
    path = os.path.join(keydir, "claim.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------- flows

def do_claim(args):
    keydir = keydir_path(args.keydir)
    priv, pub_hex, created = ensure_keypair(keydir)
    fp = fingerprint(pub_hex)
    if created:
        print(f"[claim] generated a new X25519 keypair in {keydir}")
        print("[claim] private key: static_key (mode 0600) — it never "
              "leaves this machine. Back it up; losing it loses the node.")
    else:
        print(f"[claim] using existing keypair in {keydir}")
    print(f"[claim] public key : {pub_hex}")
    print(f"[claim] fingerprint: {fp}")

    sess = authenticate(args.base, priv, pub_hex)
    route = sess.get("route")
    print(f"[claim] proof verified — route {route} assigned, "
          f"session until {sess.get('expires_at')}")

    reg = send_verb(args.base, sess["session"], {"type": "REGISTER"})
    caps = reg.get("capabilities") or reg.get("caps") or []
    hello = send_verb(args.base, sess["session"], {"type": "HELLO"})
    if not reg.get("ok", True) and reg.get("error"):
        print(f"[claim] REGISTER answered: {json.dumps(reg)[:300]}")
    print(f"[claim] REGISTER ok — route {reg.get('route', route)}"
          + (f", capabilities: {', '.join(caps)}" if caps else ""))
    print(f"[claim] HELLO ok — {hello.get('service', 'web4-wrapper/underground')}")

    record = {
        "node_name": args.name,
        "public_key": pub_hex,
        "fingerprint": fp,
        "route": route,
        "session": sess["session"],
        "session_expires_at": sess.get("expires_at"),
        "base": args.base,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "node0_fingerprint": NODE0_FINGERPRINT,
        "mesh_door_onion": MESH_DOOR_ONION,
    }
    path = save_claim(keydir, record)
    print(f"[claim] claim saved to {path} (mode 0600)")
    print()
    print("=" * 68)
    print(f"  NODE CLAIMED — route {route} · fingerprint {fp}")
    print("=" * 68)
    print("""
Next steps:
  1. Stay live:   ./claim-node.sh --hello   (re-auths; sessions last ~2h,
     your key + route are permanent)
  2. Get listed:  public Node #s are issued in claim order and published
     in nodes.json in this repo — the first 500 claimed nodes are named
     on the Dead Brands site. File a GitHub issue titled
     "Node claim: <your fingerprint>" with your node name, fingerprint
     and route to take your listing slot.
  3. Go deeper:   NODE-CLAIM.md covers pinning + activation to full
     door/relay node status, and the Tor mesh door is at
     """ + MESH_DOOR_ONION)
    return 0


def do_hello(args):
    keydir = keydir_path(args.keydir)
    if not os.path.exists(os.path.join(keydir, "static_key")):
        print("[claim] no keypair yet — run ./claim-node.sh first to claim.")
        return 2
    priv, pub_hex, _ = ensure_keypair(keydir)
    sess = authenticate(args.base, priv, pub_hex)
    hello = send_verb(args.base, sess["session"], {"type": "HELLO"})
    reg = send_verb(args.base, sess["session"], {"type": "REGISTER"})
    claim = load_claim(keydir) or {}
    if claim:
        claim["session"] = sess["session"]
        claim["session_expires_at"] = sess.get("expires_at")
        save_claim(keydir, claim)
    print(f"[claim] HELLO ok — route {reg.get('route', sess.get('route'))}, "
          f"fp {sess.get('fingerprint', fingerprint(pub_hex))}, "
          f"session until {sess.get('expires_at')}")
    print(f"[claim] HELLO payload: {json.dumps(hello)[:300]}")
    return 0


def do_dry_run(args):
    """Local self-test. No network, no claim, nothing registered.
    Generates a throwaway keypair in a temp dir, fabricates the server
    side of the challenge, and verifies the proof transcript end to end
    exactly as the registry will — from both sides of the exchange."""
    print("[dry-run] local self-test — no network calls, nothing is claimed")
    with tempfile.TemporaryDirectory() as td:
        keydir = os.path.join(td, "keys")
        priv, pub_hex, created = ensure_keypair(keydir)
        assert created
        fp = fingerprint(pub_hex)
        st = os.stat(os.path.join(keydir, "static_key"))
        mode = stat.S_IMODE(st.st_mode)
        print(f"[dry-run] keypair generated: pub={pub_hex}")
        print(f"[dry-run] fingerprint: {fp}")
        print(f"[dry-run] private key file mode: {oct(mode)} "
              f"({'ok' if mode == 0o600 else 'FAIL — expected 0o600'})")
        assert mode == 0o600

        # Fabricate the server side: ephemeral keypair + challenge id.
        server_eph = X25519PrivateKey.generate()
        server_eph_pub = server_eph.public_key().public_bytes_raw().hex()
        challenge_id = secrets.token_hex(16)

        start_payload = {"pubkey": pub_hex}
        print(f"[dry-run] would POST {args.base}{AUTH_PATH}")
        print(f"[dry-run]   body: {json.dumps(start_payload)}")
        print(f"[dry-run] mock challenge: challenge_id={challenge_id} "
              f"server_ephemeral_pub={server_eph_pub} fingerprint={fp}")

        proof = compute_proof(priv, server_eph_pub, fp, challenge_id)
        # Server-side check: X25519 is symmetric — the registry derives
        # the same shared secret from ITS ephemeral private + OUR public.
        shared_server = server_eph.exchange(
            X25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)))
        expect = hmac.new(shared_server,
                          (PROOF_PREFIX + fp + "." + challenge_id).encode(),
                          hashlib.sha256).hexdigest()
        print(f"[dry-run] proof computed locally : {proof}")
        print(f"[dry-run] proof expected by server: {expect}")
        assert hmac.compare_digest(proof, expect), "proof mismatch"
        print("[dry-run] PASS — proof transcript verifies from both sides")

        finish_payload = {"stage": "finish", "pubkey": pub_hex,
                          "challenge_id": challenge_id, "proof": proof}
        print(f"[dry-run] would POST {args.base}{AUTH_PATH}")
        print(f"[dry-run]   body: {json.dumps(finish_payload)}")
        print("[dry-run] on success the registry returns "
              "{ok, session, route, fingerprint, expires_at}; the claim "
              "is then saved to claim.json (mode 0600) in the key dir.")
    print("[dry-run] SELF-TEST PASSED — the wrapper is ready. "
          "Run ./claim-node.sh to make the real claim.")
    return 0


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(
        description="Claim your Web4 node (Dead Brands Underground wrapper). "
                    "Generates your keypair locally, proves possession to "
                    "the registry, and records your route. Your private "
                    "key never leaves this machine.")
    ap.add_argument("--name", default=None,
                    help="display name for your node (used in your claim "
                         "record and your site listing)")
    ap.add_argument("--keydir", default=None,
                    help="key directory (default: $WEB4_NODE_HOME or "
                         "~/.web4-node)")
    ap.add_argument("--base", default=DEFAULT_BASE,
                    help=f"registry base URL (default: {DEFAULT_BASE})")
    ap.add_argument("--hello", action="store_true",
                    help="re-authenticate with an existing key and prove "
                         "you're live (HELLO + REGISTER)")
    ap.add_argument("--dry-run", "--self-test", action="store_true",
                    dest="dry_run",
                    help="local self-test only: keygen + proof transcript "
                         "verified end to end, no network, no claim")
    args = ap.parse_args()

    if args.dry_run:
        return do_dry_run(args)
    if args.hello:
        return do_hello(args)
    return do_claim(args)


if __name__ == "__main__":
    sys.exit(main())
