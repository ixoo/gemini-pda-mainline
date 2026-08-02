#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --tag SAFE-TAG\n' "$0" >&2; }

tag=
while (($#)); do
	case "$1" in
	--tag) (($# >= 2)) || die '--tag requires a value'; tag=$2; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$tag" =~ ^[a-z0-9][a-z0-9-]{0,63}$ ]] || die 'tag is absent or unsafe'

readonly TARGET=gemini@192.168.1.50
readonly REMOTE_SHA256=cd44e286d333375b53a90b2f26aa968e235574c3912f41e236ba7820700defc8
readonly VALIDATOR_SHA256=ec6809e25c45e2fb16eb01aee0e5798473061ce38fcbe5f730a111e1dc599f61
readonly BOUNDED_EXEC_SHA256=e250c4f0375aed986bc73eeea699cf5f4ba51625aa51a1ede2d40ac601f62ce5
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
known_hosts="${HOME:?HOME is not set}/.ssh/known_hosts"
private_root="$repo_root/artifacts/runtime-captures"
remote_probe="$script_dir/remote-initial-probe.sh"
validator="$script_dir/validate-initial.py"
bounded_exec="$repo_root/experiments/2026-07-23-gemian-a72-load-assisted-observation/scripts/bounded-exec.pl"
capture="$private_root/gemian-a72-bounded-observer-$tag-initial.txt"
partial="$capture.partial"
validation="$capture.validation.txt"

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{print $1}'; }
for command in awk cat chmod git mv perl python3 rm shasum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "missing host command: $command"
done
[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 ]] ||
	die 'Gemini identity is absent or unsafe'
[[ -f "$known_hosts" && ! -L "$known_hosts" && "$(file_mode "$known_hosts")" == 600 ]] ||
	die 'known-hosts database is absent or unsafe'
[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] ||
	die 'private capture root is absent or unsafe'
for pin in "$REMOTE_SHA256 $remote_probe" "$VALIDATOR_SHA256 $validator" \
	"$BOUNDED_EXEC_SHA256 $bounded_exec"; do
	read -r expected path <<<"$pin"
	[[ -f "$path" && ! -L "$path" && "$(file_sha256 "$path")" == "$expected" ]] ||
		die "collector dependency changed: $path"
done
for output in "$capture" "$partial" "$validation"; do
	[[ ! -e "$output" && ! -L "$output" ]] || die "output exists: $output"
	git -C "$repo_root" check-ignore -q -- "$output" || die "output is not ignored: $output"
done

status=0
perl "$bounded_exec" 75 -- ssh -F /dev/null -i "$identity" \
	-o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
	-o ConnectTimeout=8 -o ServerAliveInterval=5 -o ServerAliveCountMax=4 \
	-o StrictHostKeyChecking=yes -o UserKnownHostsFile="$known_hosts" \
	-o GlobalKnownHostsFile=/dev/null -o WarnWeakCrypto=no -o LogLevel=ERROR \
	"$TARGET" \
	"sudo -n env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C timeout --signal=TERM --kill-after=1s 65s sh -s" \
	<"$remote_probe" >"$partial" || status=$?
chmod 0600 "$partial"
if ((status != 0)); then
	printf 'error: initial probe failed with status %s; partial preserved: %s\n' \
		"$status" "$partial" >&2
	exit 3
fi
python3 "$validator" "$partial" >"$validation" || {
	chmod 0600 "$validation"
	die "initial capture validation failed; partial preserved: $partial"
}
chmod 0600 "$validation"
mv -n "$partial" "$capture"
printf 'capture=%s\nvalidation=%s\n' "$capture" "$validation"
cat "$validation"
