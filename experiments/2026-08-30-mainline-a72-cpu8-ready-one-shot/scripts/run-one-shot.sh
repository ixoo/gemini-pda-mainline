#!/usr/bin/env bash

# Materialize and run exactly one published, boot-ID-bound CPU8 action.
set -euo pipefail
export LC_ALL=C
umask 077

readonly CONTRACT_SHA256=45c81c4ead6611d8550c602908700e1f3403cd31c7bcddf6c7bcfe31e47325e4
readonly COLLECTOR_SHA256=b3dbdc0ee516567dcc059574252aad04742932451e239bda853a668e09510927
readonly DERIVED_SHA256=fa1dc4cbd2b79fb643cf9a16074b1689b5fe3d7a9328abf4f6966014d4e18156
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in mktemp rm sha256sum; do
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

# The source-pinned derived collector must remain beside its support files.
derived=$(mktemp "$script_dir/.cpu8-ready-one-shot-run.XXXXXXXX")
rm -f -- "$derived"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
"$collector" --materialize "$derived"
[[ "$(sha256sum "$derived" | awk '{print $1}')" == "$DERIVED_SHA256" ]] || die 'derived collector changed'

set +e
/bin/bash "$derived" \
	--output artifacts/runtime-captures/a72-cpu8-ready-one-shot-attempt-1 \
	--deployment-boot-id 7586aa0f-56be-4a83-8f05-4ca535af2db2 \
	--wait-seconds 180 \
	--recovery-seconds 300
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
