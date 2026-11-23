#!/usr/bin/env bash
# Build the release zip users install into Live's "Remote Scripts" folder.
#
#   scripts/build_release.sh <version> <outdir>
#
# Writes <outdir>/Launchpad95.zip with one top folder, Launchpad95/, holding only what Live
# needs: the script's *.py files (repository root), M4LDevice/, LICENSE, README.md and
# CHANGELOG.md. Only files tracked by git are taken (no caches, no local junk). The zip is
# deterministic: sorted entries, fixed timestamps and permissions; <version> goes into the
# zip comment.
set -euo pipefail

if [ $# -ne 2 ]; then
	echo "usage: $0 <version> <outdir>" >&2
	exit 2
fi

VERSION=$1
OUTDIR=$2
if ! [[ $VERSION =~ ^[0-9A-Za-z][0-9A-Za-z.+-]*$ ]]; then
	echo "error: bad version '$VERSION' (expected e.g. 1.2.3, without a leading v)" >&2
	exit 2
fi

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PKG=Launchpad95
mkdir -p "$OUTDIR"
ZIP="$(cd "$OUTDIR" && pwd)/$PKG.zip"

# The release contents, as paths relative to the repository root (tracked files only).
FILES=$(cd "$ROOT" && git ls-files -- ':(glob)*.py' 'M4LDevice/**' LICENSE README.md CHANGELOG.md | LC_ALL=C sort)
for required in __init__.py Launchpad.py LICENSE README.md CHANGELOG.md; do
	if ! grep -qx "$required" <<<"$FILES"; then
		echo "error: $required is missing from the release contents" >&2
		exit 1
	fi
done

rm -f "$ZIP"
printf '%s\n' "$FILES" | python3 -c '
import sys
import zipfile

root, pkg, zip_path, version = sys.argv[1:5]
files = [line for line in sys.stdin.read().splitlines() if line]
dirs = sorted({pkg + "/"} | {pkg + "/" + f.rsplit("/", 1)[0] + "/" for f in files if "/" in f})
stamp = (2020, 1, 1, 0, 0, 0)
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.comment = ("Launchpad95 " + version).encode()
    entries = [(d, None) for d in dirs] + [(pkg + "/" + f, f) for f in files]
    for name, src in sorted(entries):
        info = zipfile.ZipInfo(name, stamp)
        info.create_system = 3
        if src is None:
            info.external_attr = (0o40755 << 16) | 0x10
            z.writestr(info, b"")
        else:
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(root + "/" + src, "rb") as fh:
                z.writestr(info, fh.read())
' "$ROOT" "$PKG" "$ZIP" "$VERSION"

echo "built $ZIP ($(printf '%s\n' "$FILES" | wc -l | tr -d ' ') files, version $VERSION)"
