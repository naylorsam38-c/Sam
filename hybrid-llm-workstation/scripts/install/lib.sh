#!/usr/bin/env bash
# Shared helpers for the install phase scripts. Never fabricates success:
# every check either genuinely passes, genuinely fails, or is explicitly
# skipped with a stated reason (spec operational rules #1, #2, #10, #12).
set -uo pipefail

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

step() { echo; echo "== $* =="; }

pass() { echo "  PASS: $*"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $*" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
skip() { echo "  SKIP: $*"; SKIP_COUNT=$((SKIP_COUNT + 1)); }

summary() {
    echo
    echo "---------------------------------------------"
    echo "Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed, ${SKIP_COUNT} skipped"
    echo "---------------------------------------------"
    [ "${FAIL_COUNT}" -eq 0 ]
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }
