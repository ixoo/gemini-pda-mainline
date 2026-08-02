#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --initial CAPTURE --tag SAFE-TAG\n' "$0" >&2; }

initial=
tag=
while (($#)); do
	case "$1" in
	--initial) (($# >= 2)) || die '--initial requires a value'; initial=$2; shift 2 ;;
	--tag) (($# >= 2)) || die '--tag requires a value'; tag=$2; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$tag" =~ ^[a-z0-9][a-z0-9-]{0,63}$ ]] || die 'tag is absent or unsafe'
[[ -n "$initial" ]] || die 'initial capture is required'

readonly TARGET=gemini@192.168.1.50
readonly SOURCE_SHA256=c04bdfda47676645ef55dc5d99c5d067076b59e6246ae29baa20d848bcd0992d
readonly DERIVER_SHA256=5bd1e648a90dc808e82cdad2718069b3198b16b96bd2a50c0ee8c5e52c3bd6d4
readonly DERIVED_SHA256=8bf8bf37e32d0b787dfaa651121a64dc39bf1f37aab4a1ba5b558fea4ec032da
readonly INITIAL_VALIDATOR_SHA256=ec6809e25c45e2fb16eb01aee0e5798473061ce38fcbe5f730a111e1dc599f61
readonly PULSE_VALIDATOR_SHA256=75f4e924927aed083605b7116984386f79a4825d90e79dedfe19caad9e27fb88
readonly BOUNDED_EXEC_SHA256=e250c4f0375aed986bc73eeea699cf5f4ba51625aa51a1ede2d40ac601f62ce5
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
private_root="$repo_root/artifacts/runtime-captures"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
known_hosts="${HOME:?HOME is not set}/.ssh/known_hosts"
source_probe="$repo_root/experiments/2026-07-23-gemian-a72-load-assisted-observation/scripts/remote-load-probe.sh"
bounded_exec="$repo_root/experiments/2026-07-23-gemian-a72-load-assisted-observation/scripts/bounded-exec.pl"
deriver="$script_dir/derive-two-worker-pulse.py"
initial_validator="$script_dir/validate-initial.py"
pulse_validator="$script_dir/validate-pulse.py"
capture="$private_root/gemian-a72-bounded-observer-$tag-pulse.txt"
partial="$capture.partial"
validation="$capture.validation.txt"

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{print $1}'; }
for command in awk basename cat chmod dirname git grep mktemp mv perl python3 \
	rm shasum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "missing host command: $command"
done
[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 ]] ||
	die 'Gemini identity is absent or unsafe'
[[ -f "$known_hosts" && ! -L "$known_hosts" && "$(file_mode "$known_hosts")" == 600 ]] ||
	die 'known-hosts database is absent or unsafe'
[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] ||
	die 'private capture root is absent or unsafe'

initial_parent="$(cd -- "$(dirname -- "$initial")" 2>/dev/null && pwd -P)" ||
	die 'initial capture parent is unavailable'
initial_path="$initial_parent/$(basename -- "$initial")"
case "$initial_path" in
"$private_root"/*-initial.txt) ;;
*) die 'initial capture is outside the private capture root or has the wrong suffix' ;;
esac
[[ -f "$initial_path" && ! -L "$initial_path" && "$(file_mode "$initial_path")" == 600 ]] ||
	die 'initial capture is absent or unsafe'
git -C "$repo_root" check-ignore -q -- "$initial_path" || die 'initial capture is not ignored'

for pin in "$SOURCE_SHA256 $source_probe" "$DERIVER_SHA256 $deriver" \
	"$INITIAL_VALIDATOR_SHA256 $initial_validator" \
	"$PULSE_VALIDATOR_SHA256 $pulse_validator" \
	"$BOUNDED_EXEC_SHA256 $bounded_exec"; do
	read -r expected path <<<"$pin"
	[[ -f "$path" && ! -L "$path" && "$(file_sha256 "$path")" == "$expected" ]] ||
		die "collector dependency changed: $path"
done
for output in "$capture" "$partial" "$validation"; do
	[[ ! -e "$output" && ! -L "$output" ]] || die "output exists: $output"
	git -C "$repo_root" check-ignore -q -- "$output" || die "output is not ignored: $output"
done

stage_dir=
cleanup()
{
	case "${stage_dir:-}" in "$private_root"/.pulse-stage.*)
		[[ ! -L "$stage_dir" ]] && rm -rf -- "$stage_dir"
		;;
	esac
}
trap cleanup EXIT HUP INT TERM
stage_dir=$(mktemp -d "$private_root/.pulse-stage.XXXXXXXX")
case "$stage_dir" in "$private_root"/.pulse-stage.*) ;; *) die 'unsafe staging path' ;; esac
[[ -d "$stage_dir" && ! -L "$stage_dir" ]] || die 'unsafe staging directory'
initial_check="$stage_dir/initial.validation.txt"
derived_probe="$stage_dir/remote-two-worker-pulse.sh"
python3 "$initial_validator" "$initial_path" >"$initial_check" ||
	die 'initial capture does not pass its exact validator'
grep -Fqx 'initial_disposition=empty-offline' "$initial_check" ||
	die 'initial capture is not empty/offline; pulse remains prohibited'
grep -Fqx 'next_action=eligible-for-separate-second-prepulse-gate' "$initial_check" ||
	die 'initial capture does not authorize evaluation of the second gate'
boot_id_sha256=$(awk -F= '/^boot_id_before_sha256=/ {print $2; exit}' "$initial_path")
[[ "$boot_id_sha256" =~ ^[0-9a-f]{64}$ ]] || die 'initial boot ID hash is malformed'
initial_sha256=$(file_sha256 "$initial_path")

python3 "$deriver" "$source_probe" "$derived_probe" >"$stage_dir/derivation.txt" ||
	die 'two-worker probe derivation failed'
[[ -f "$derived_probe" && ! -L "$derived_probe" && \
	"$(file_mode "$derived_probe")" == 600 && \
	"$(file_sha256 "$derived_probe")" == "$DERIVED_SHA256" ]] ||
	die 'derived two-worker probe identity changed'

identity_start_sha256=$(file_sha256 "$identity")
known_hosts_start_sha256=$(file_sha256 "$known_hosts")
status=0
perl "$bounded_exec" 75 -- ssh -F /dev/null -i "$identity" \
	-o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
	-o ConnectTimeout=8 -o ServerAliveInterval=5 -o ServerAliveCountMax=4 \
	-o StrictHostKeyChecking=yes -o UserKnownHostsFile="$known_hosts" \
	-o GlobalKnownHostsFile=/dev/null -o WarnWeakCrypto=no -o LogLevel=ERROR \
	"$TARGET" \
	"sudo -n env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C GEMINI_EXPECTED_BOOT_ID_SHA256=$boot_id_sha256 timeout --signal=TERM --kill-after=1s 65s sh -s" \
	<"$derived_probe" >"$partial" || status=$?
chmod 0600 "$partial"
if ((status != 0)); then
	printf 'error: pulse probe failed with status %s; partial preserved: %s\n' \
		"$status" "$partial" >&2
	exit 3
fi
[[ "$(file_sha256 "$initial_path")" == "$initial_sha256" ]] ||
	die 'initial capture changed during collection'
[[ "$(file_sha256 "$identity")" == "$identity_start_sha256" ]] ||
	die 'Gemini identity changed during collection'
[[ "$(file_sha256 "$known_hosts")" == "$known_hosts_start_sha256" ]] ||
	die 'known-hosts database changed during collection'
[[ "$(file_sha256 "$source_probe")" == "$SOURCE_SHA256" && \
	"$(file_sha256 "$deriver")" == "$DERIVER_SHA256" && \
	"$(file_sha256 "$pulse_validator")" == "$PULSE_VALIDATOR_SHA256" && \
	"$(file_sha256 "$bounded_exec")" == "$BOUNDED_EXEC_SHA256" ]] ||
	die 'a collector dependency changed during collection'
python3 "$pulse_validator" "$partial" >"$validation" || {
	chmod 0600 "$validation"
	die "pulse capture validation failed; partial preserved: $partial"
}
chmod 0600 "$validation"
mv -n "$partial" "$capture"
printf 'initial_capture=%s\ninitial_sha256=%s\n' "$initial_path" "$initial_sha256"
printf 'capture=%s\nvalidation=%s\n' "$capture" "$validation"
printf 'derived_remote_sha256=%s\n' "$DERIVED_SHA256"
cat "$validation"
