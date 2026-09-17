#!/bin/sh
# The release publishes no checksums; these were recorded on first download (2026-09-17).
# To support another platform, download its asset once, check it runs, and add its hash below.
set -eu

VERSION=0.5.6
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)   TARGET=aarch64-apple-darwin;      SHA=4601e7f4e4c03e59a4c5b5000216ef3add3e808799cfccd95e14e83ea4611081 ;;
  Darwin-x86_64)  TARGET=x86_64-apple-darwin;       SHA=d3be84003acb7c23e738ad7f70a158ec779a8d233a82e7fa3e717d112eb5b50f ;;
  Linux-x86_64)   TARGET=x86_64-unknown-linux-musl; SHA=70775e251eee44c0f2451a1e833326cf8bcbbe304d3e7cd12851e6fce72ef7da ;;
  Linux-aarch64)  TARGET=aarch64-unknown-linux-gnu; SHA=14e02a1c0028f3ca0bdf83b62b3336e56ba0556894ef295a95e8573f06557166 ;;
  *) echo "unsupported platform: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

BIN_DIR="$(cd "$(dirname "$0")" && pwd)/bin"
BIN="$BIN_DIR/deep-filter"
mkdir -p "$BIN_DIR"
TMP="$BIN.download"
curl -fsSL -o "$TMP" "https://github.com/Rikorose/DeepFilterNet/releases/download/v$VERSION/deep-filter-$VERSION-$TARGET"

ACTUAL=$(shasum -a 256 "$TMP" | cut -d' ' -f1)
if [ "$ACTUAL" != "$SHA" ]; then
  rm -f "$TMP"
  echo "sha256 mismatch for deep-filter-$VERSION-$TARGET: expected $SHA, got $ACTUAL" >&2
  exit 1
fi
chmod +x "$TMP"
mv "$TMP" "$BIN"
"$BIN" --version
