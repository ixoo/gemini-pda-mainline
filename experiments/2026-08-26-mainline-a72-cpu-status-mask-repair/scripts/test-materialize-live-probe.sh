#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
workdir=$(mktemp -d "${TMPDIR:-/tmp}/.gemini-test-materialize-probe.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM

first="$workdir/first.sh"
second="$workdir/second.sh"
"$script_dir/materialize-live-probe.sh" --output "$first" >"$workdir/first.txt"
"$script_dir/materialize-live-probe.sh" --output "$second" >"$workdir/second.txt"
cmp -s "$first" "$second"
grep -Fx 'materialized_probe_sha256=de72e6cf61aec14c2deb56ee67a133ad323612d87812914e96a2644bca91d1c9' "$workdir/first.txt" >/dev/null
grep -Fx 'derivation_levels=2' "$workdir/first.txt" >/dev/null
[[ "$(wc -c <"$first" | tr -d ' ')" -gt 4096 ]]

printf 'materialized_generations=2-byte-identical\n'
printf 'materialized_probe_sha256=de72e6cf61aec14c2deb56ee67a133ad323612d87812914e96a2644bca91d1c9\n'
printf 'derivation_levels=2\n'
printf 'device_action=none\nresult=pass\n'
