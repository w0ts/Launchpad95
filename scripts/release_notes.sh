#!/usr/bin/env bash
# Print the CHANGELOG.md section of one version: the body under its "## [<version>]" heading
# ("## [1.2.3] - 2026-12-01"; the dated history uses "## 2023-11-26"), up to the next "## ".
#
#   scripts/release_notes.sh <version> [changelog]
#
# Fails when the section is missing or empty.
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
	echo "usage: $0 <version> [changelog]" >&2
	exit 2
fi

VERSION=$1
CHANGELOG=${2:-"$(cd "$(dirname "$0")/.." && pwd)/CHANGELOG.md"}
if [ ! -f "$CHANGELOG" ]; then
	echo "error: $CHANGELOG not found" >&2
	exit 1
fi

NOTES=$(awk -v ver="$VERSION" '
	/^## / {
		if (found) exit
		head = substr($0, 4)
		sub(/[ \t]+-[ \t].*$/, "", head)
		sub(/[ \t]+$/, "", head)
		if (head == ver || head == "[" ver "]") found = 1
		next
	}
	found {
		if ($0 ~ /^[ \t]*$/) { blank++; next }
		if (printed) for (i = 0; i < blank; i++) print ""
		blank = 0
		printed = 1
		print
	}
' "$CHANGELOG")

if [ -z "$NOTES" ]; then
	echo "error: $CHANGELOG has no section '## [$VERSION]' (or it is empty)" >&2
	exit 1
fi
printf '%s\n' "$NOTES"
