#!/usr/bin/env bash
# Fetch Ableton's _Framework (decompiled, from the gluon/AbletonLive1x_MIDIRemoteScripts
# repositories) into <dest>, for running the Launchpad95 tests outside Live.
#
#   scripts/fetch_framework.sh <dest>
#   ABLETON_FRAMEWORK_DIR=<dest> python -m pytest tests
#
# Pinned commits; the Live 11.2.11 tree is the base, three files (two do not parse there) come
# from the Live 12 tree, and tests/framework.patch fixes decompiler bugs. Nothing from
# Ableton is committed to this repository. Idempotent: does nothing when <dest> is up to
# date with the pinned commits and the patch.
set -euo pipefail

if [ $# -ne 1 ]; then
	echo "usage: $0 <dest>" >&2
	exit 2
fi

DEST=$1
L11_REPO=https://github.com/gluon/AbletonLive11_MIDIRemoteScripts
L11_SHA=6ec80666c81654518dc79f6bc5d2b4af50ca4ec3   # "Uncompyled 11.2.11"
L12_REPO=https://github.com/gluon/AbletonLive12_MIDIRemoteScripts
L12_SHA=e83d5192f321b24eb9daab843ac49a2d95d862b1
# Files taken from the Live 12 tree (they do not parse in the Live 11 tree, or are
# decompiled more faithfully there).
L12_FILES="_Framework/ChannelStripComponent.py _Framework/ClipSlotComponent.py _Framework/SubjectSlot.py"

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
PATCH=$REPO_ROOT/tests/framework.patch

hash_file() {
	if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

STAMP="$L11_SHA $L12_SHA $L12_FILES $(hash_file "$PATCH")"
if [ -f "$DEST/.framework-stamp" ] && [ "$(cat "$DEST/.framework-stamp")" = "$STAMP" ]; then
	echo "framework in $DEST is up to date"
	exit 0
fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/lp95-framework.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

fetch() {
	local dir=$1 repo=$2 sha=$3
	git init -q "$dir"
	git -C "$dir" fetch -q --depth 1 "$repo" "$sha"
	git -C "$dir" -c advice.detachedHead=false checkout -q FETCH_HEAD
}

fetch "$WORK/l11" "$L11_REPO" "$L11_SHA"
fetch "$WORK/l12" "$L12_REPO" "$L12_SHA"

OUT=$WORK/out
mkdir -p "$OUT/ableton/v2"
cp -R "$WORK/l11/_Framework" "$WORK/l11/_Generic" "$OUT/"
cp "$WORK/l11/ableton/__init__.py" "$OUT/ableton/"
cp "$WORK/l11/ableton/v2/__init__.py" "$OUT/ableton/v2/"
cp -R "$WORK/l11/ableton/v2/base" "$OUT/ableton/v2/"
for file in $L12_FILES; do
	cp "$WORK/l12/$file" "$OUT/$file"
done

if [ -s "$PATCH" ]; then (cd "$OUT" && patch -p1 --forward --silent < "$PATCH"); fi

echo "$STAMP" > "$OUT/.framework-stamp"
rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
mv "$OUT" "$DEST"
echo "framework fetched into $DEST"
