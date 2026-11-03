#!/usr/bin/env bash
# Builds the zip the brief asks for: the TDD and deployment.md, nothing else.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/submission"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

mkdir -p "$out"
cp -- "$root/docs/TDD.pdf" "$root/deployment.md" "$work/"
rm -f -- "$out/ngo-platform-submission.zip"
(cd "$work" && zip -q "$out/ngo-platform-submission.zip" TDD.pdf deployment.md)
echo "$out/ngo-platform-submission.zip"
