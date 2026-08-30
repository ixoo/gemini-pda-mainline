#!/usr/bin/env bash

# Materialize and run exactly one published, boot-ID-bound CPU8 action.
set -euo pipefail
export LC_ALL=C
umask 077

readonly CONTRACT_SHA256=6f12640027ac5538f5e4fed47e5e2609912d94e1eff8035bae9e66843a85e0ea
readonly COLLECTOR_SHA256=4920f2c44d6b8d12d30c2b706eb1e48549a74446710387642dcb4873a0cd1b0d
readonly DERIVED_SHA256=1e372c425b664fdd9af75659dd029bc6baac5276800f1fbf168cba7e2a219bb8
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in mktemp rm rmdir sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ $# == 0 ]] || die 'run-one-shot.sh accepts no arguments'

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
contract="$script_dir/../contract.json"
collector="$script_dir/collect-live-trigger.sh"
[[ -f "$contract" && ! -L "$contract" ]] || die 'contract is missing or unsafe'
[[ -f "$collector" && ! -L "$collector" ]] || die 'collector is missing or unsafe'
[[ "$(sha256sum "$contract" | awk '{print $1}')" == "$CONTRACT_SHA256" ]] || die 'contract changed'
[[ "$(sha256sum "$collector" | awk '{print $1}')" == "$COLLECTOR_SHA256" ]] || die 'collector changed'

temporary_root=$(mktemp -d "$script_dir/.ready-one-shot-run.XXXXXXXX")
derived="$temporary_root/collector"
cleanup() {
	[[ ! -e "${derived:-}" ]] || rm -f -- "$derived"
	[[ ! -d "${temporary_root:-}" ]] || rmdir -- "$temporary_root"
}
trap cleanup EXIT HUP INT TERM
"$collector" --materialize "$derived"
[[ "$(sha256sum "$derived" | awk '{print $1}')" == "$DERIVED_SHA256" ]] || die 'derived collector changed'

set +e
/bin/bash "$derived" \
	--output artifacts/runtime-captures/a72-ready-admission-one-shot-attempt-1 \
	--deployment-boot-id 0a0d0adb-9a28-4783-8b1e-c91613e9554f \
	--wait-seconds 180 \
	--recovery-seconds 300
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
