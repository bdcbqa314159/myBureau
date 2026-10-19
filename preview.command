#!/usr/bin/env bash
# Double-click this file in Finder to see the site.
#
# macOS opens a .command file in Terminal and runs it, which means the
# whole preview never requires typing a command. It is a two-line
# wrapper around preview.sh, which is the real thing.
cd "$(dirname "$0")"
./preview.sh
