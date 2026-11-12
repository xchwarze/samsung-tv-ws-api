#!/usr/bin/env bash
# No strict mode: this script may be sourced and must not alter the caller's shell options.

# Function scope keeps variables out of the caller's shell when sourced.
_cleanup_venv() {
    local workspace venv script target
    local venvs=(.venv venv env ENV env.bak venv.bak)

    # Follow symlinks without readlink -f, which macOS lacks before 12.3.
    script=$1
    while [ -L "$script" ]; do
        target=$(readlink -- "$script")
        case $target in
            /*) script=$target ;;
            *) script=$(dirname -- "$script")/$target ;;
        esac
    done
    workspace="$(dirname -- "$script")/.."

    echo "🗑️  Removing virtual environments..."

    for venv in "${venvs[@]}"; do
        # -ef compares directory identity, so symlinked project paths still match.
        if [ "${VIRTUAL_ENV:-}" -ef "$workspace/$venv" ]; then
            echo "⚠️  Active virtual environment detected at $VIRTUAL_ENV."
            if type deactivate > /dev/null 2>&1; then
                echo "Attempting to deactivate..."
                deactivate 2>/dev/null || true
            fi
            if [ -n "${VIRTUAL_ENV:-}" ]; then
                echo "❌ $VIRTUAL_ENV is still active. Run 'deactivate' first, or source this script: source scripts/cleanup-venv.sh"
                return 1
            fi
            break
        fi
    done

    for venv in "${venvs[@]}"; do
        [ -d "$workspace/$venv" ] || continue
        if [ ! -f "$workspace/$venv/pyvenv.cfg" ]; then
            echo "⚠️  Skipping $venv: not a virtual environment (no pyvenv.cfg)"
            continue
        fi
        if ! rm -rf "${workspace:?}/$venv"; then
            echo "❌ Failed to remove $venv"
            return 1
        fi
        echo "Removed $venv"
    done

    echo "✅ Virtual environment cleanup complete!"
}

# zsh sets $0 to the function name inside functions, so resolve the path here.
if ! _cleanup_venv "${BASH_SOURCE[0]:-$0}"; then
    unset -f _cleanup_venv
    # return when sourced, exit when executed
    return 1 2>/dev/null || exit 1
fi
unset -f _cleanup_venv
