#!/usr/bin/env bash
# child-publish-watcher.sh — federated architecture cross-repo trigger (monorepo case).
#
# Watches a CHILD architecture repo's lifecycle CURRENT pointer for changes
# and, when the child publishes a new generation, invokes the PARENT repo's
# federated invalidation CLI so parent artifacts referencing that child
# (via `child_ref: repo://<CHILD_ARCH_ID>@...`) are marked stale and can
# be rebuilt.
#
# ----------------------------------------------------------------------------
# Configuration — REPLACE these placeholders before use.
# ----------------------------------------------------------------------------
CHILD_REPO="${CHILD_REPO:-/path/to/child/repo}"           # child architecture repo root
PARENT_REPO="${PARENT_REPO:-/path/to/parent/repo}"        # parent architecture repo root
CHILD_ARCH_ID="${CHILD_ARCH_ID:-child-package-id}"        # child's architecture_id (matches repo:// prefix)
# ----------------------------------------------------------------------------

set -euo pipefail

WATCH_TARGET="${CHILD_REPO}/.architecture/lifecycle/CURRENT"

if [ ! -f "${WATCH_TARGET}" ]; then
    echo "watcher: CURRENT pointer not found at ${WATCH_TARGET}" >&2
    exit 1
fi

on_change() {
    echo "watcher: child ${CHILD_ARCH_ID} published a new generation; invalidating parent"
    (
        cd "${PARENT_REPO}"
        opencode-arch invalidate --federated-child "${CHILD_ARCH_ID}"
    )
}

# Choose a watcher. fswatch on macOS, inotifywait on Linux.
if command -v fswatch >/dev/null 2>&1; then
    echo "watcher: using fswatch on ${WATCH_TARGET}"
    fswatch -o "${WATCH_TARGET}" | while read -r _; do
        on_change
    done
elif command -v inotifywait >/dev/null 2>&1; then
    echo "watcher: using inotifywait on ${WATCH_TARGET}"
    while inotifywait -e modify,move_self,create "${WATCH_TARGET}" >/dev/null 2>&1; do
        on_change
    done
else
    echo "watcher: neither fswatch nor inotifywait is installed" >&2
    echo "  macOS:  brew install fswatch" >&2
    echo "  Linux:  apt install inotify-tools  (or equivalent)" >&2
    exit 2
fi
