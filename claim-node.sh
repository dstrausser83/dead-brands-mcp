#!/usr/bin/env bash
# Claim your Web4 node — one command.
#
#   ./claim-node.sh                  claim (or re-auth if already claimed)
#   ./claim-node.sh --name "my-pi"   claim with a display name
#   ./claim-node.sh --hello          re-authenticate and prove you're live
#   ./claim-node.sh --dry-run        local self-test, no network, no claim
#   ./claim-node.sh --help           everything the wrapper can do
#
# The only dependency is Python 3.11+ and the `cryptography` package.
# If `cryptography` is missing, this launcher builds a one-time local
# virtualenv (.venv/) and installs it there — nothing system-wide.
set -euo pipefail
cd "$(dirname "$0")"

if python3 -c "import cryptography" >/dev/null 2>&1; then
  exec python3 claim-node.py "$@"
fi

echo "[claim] python3 found, but the 'cryptography' package is missing."
echo "[claim] creating a one-time local virtualenv in .venv/ ..."
python3 -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet "cryptography>=42"
echo "[claim] virtualenv ready — continuing."
exec ./.venv/bin/python claim-node.py "$@"
