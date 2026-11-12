#!/usr/bin/env bash
# Setups the repository.

# Stop on errors
set -e

# Use copy mode for UV to avoid hardlink warnings on different filesystems
export UV_LINK_MODE=copy

# Find the absolute path of the directory where this script resides
SETUP_SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" &>/dev/null && pwd)

# Always use this repo's .venv, even if the shell exports another project's
# environment (e.g. a shared devcontainer)
REPO_ROOT=$(dirname "$SETUP_SCRIPT_DIR")
export VIRTUAL_ENV="$REPO_ROOT/.venv"

cd "$REPO_ROOT"

# Keep an existing .venv: uv venv would replace its interpreter
if [ ! -x "$VIRTUAL_ENV/bin/python" ]; then
    uv venv "$VIRTUAL_ENV"
fi
uv pip install -r requirements.txt
"$VIRTUAL_ENV/bin/pre-commit" install
