#!/usr/bin/env bash
# Is the committed JavaScript what the TypeScript compiles to?
#
#     ./tools/js-is-current.sh
#
# static/js/*.js is committed so that previewing the site needs no Node
# at all — see "Why the compiled JS is in the repo" in README. The whole
# bargain depends on it never drifting from src/, so this is the thing
# that notices. It runs in CI, which is where drift would otherwise
# arrive unseen.
set -euo pipefail
cd "$(dirname "$0")/.."

npx tsc

if git diff --quiet -- static/js; then
  printf '\n  the committed JavaScript matches src/\n\n'
  exit 0
fi

printf '\n  The committed JavaScript is out of date.\n\n'
git diff --stat -- static/js | sed 's/^/    /'
printf '\n  Fix it with:\n\n    npx tsc && git add static/js && git commit\n\n'
exit 1
