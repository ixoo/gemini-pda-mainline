#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage()
{
	printf 'usage: %s --output NEW_FILE [--samples N] [--interval SECONDS]\n' \
		"$0" >&2
}

readonly TARGET=gemini@192.168.1.50
readonly IDENTITY_RELATIVE=artifacts/credentials/gemini_ed25519
readonly WALL_CLOCK_GRACE_SECONDS=60
output=
samples=180
interval=1

while (($#)); do
	case "$1" in
	--output|--samples|--interval)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--output) output=$2 ;;
		--samples) samples=$2 ;;
		--interval) interval=$2 ;;
		esac
		shift 2
		;;
	-h|--help)
		usage
		exit 0
		;;
	*)
		usage
		die "unknown option: $1"
		;;
	esac
done

[[ "$samples" =~ ^[0-9]+$ ]] || die 'samples must be an integer'
((samples >= 1 && samples <= 900)) || die 'samples must be between 1 and 900'
[[ "$interval" =~ ^[0-9]+$ ]] || die 'interval must be an integer'
((interval >= 1 && interval <= 60)) || die 'interval must be between 1 and 60'
((samples * interval <= 900)) || die 'requested sample duration exceeds 900 seconds'
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
identity="$repo_root/$IDENTITY_RELATIVE"
private_root="$repo_root/artifacts/runtime-captures"
known_hosts_path="${HOME:?HOME is not set}/.ssh/known_hosts"
bounded_exec="$script_dir/bounded-exec.pl"
# The remote loop sleeps only between samples.  The fixed grace covers the
# identity/power gates, vendor reads, filtered dmesg, SSH connection setup and
# three 5-second server-alive misses without weakening the hard process bound.
sampling_sleep_seconds=$(((samples - 1) * interval))
wall_timeout_seconds=$((sampling_sleep_seconds + WALL_CLOCK_GRACE_SECONDS))
readonly script_dir repo_root identity known_hosts_path bounded_exec
readonly sampling_sleep_seconds wall_timeout_seconds

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1" 2>/dev/null; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }

[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 ]] || \
	die 'exact Gemini SSH identity is absent or unsafe'
[[ -f "$bounded_exec" && ! -L "$bounded_exec" ]] || \
	die 'bounded-exec helper is absent or unsafe'
[[ "$(cd -- "$(dirname -- "$identity")" && pwd -P)/$(basename -- "$identity")" == "$identity" ]] || \
	die 'exact Gemini SSH identity path contains an intermediate symlink'
git -C "$repo_root" check-ignore -q -- "$identity" || \
	die 'exact Gemini SSH identity is not private'
identity_start_sha256=$(file_sha256 "$identity")
[[ "$identity_start_sha256" =~ ^[0-9a-f]{64}$ ]] || die 'cannot identify Gemini SSH key'

[[ -f "$known_hosts_path" && ! -L "$known_hosts_path" && \
	"$(file_mode "$known_hosts_path")" == 600 ]] || \
	die 'SSH known-hosts database is absent or unsafe'
[[ "$(cd -- "$(dirname -- "$known_hosts_path")" && pwd -P)/$(basename -- "$known_hosts_path")" == "$known_hosts_path" ]] || \
	die 'SSH known-hosts path contains an intermediate symlink'
known_hosts_start_sha256=$(file_sha256 "$known_hosts_path")
[[ "$known_hosts_start_sha256" =~ ^[0-9a-f]{64}$ ]] || die 'cannot identify known-hosts database'

[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] || \
	die 'private runtime-capture root is absent or not mode 0700'
private_root="$(cd -- "$private_root" && pwd -P)"
readonly private_root
case "$output" in
/*) ;;
*) output="$repo_root/${output#./}" ;;
esac
[[ "$(dirname -- "$output")" == "$private_root" ]] || \
	die '--output must be directly inside artifacts/runtime-captures/'
[[ "$(basename -- "$output")" =~ ^gemian-a72-readonly-[A-Za-z0-9._-]+\.txt$ ]] || \
	die 'output basename must match gemian-a72-readonly-*.txt'
git -C "$repo_root" check-ignore -q -- "$output" || die 'output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'output must be a new path'

partial="$output.partial"
[[ ! -e "$partial" && ! -L "$partial" ]] || die 'partial output already exists'
set +e
perl "$bounded_exec" "$wall_timeout_seconds" -- ssh \
	-F /dev/null \
	-i "$identity" \
	-o IdentitiesOnly=yes \
	-o IdentityAgent=none \
	-o BatchMode=yes \
	-o ConnectTimeout=5 \
	-o ServerAliveInterval=5 \
	-o ServerAliveCountMax=3 \
	-o StrictHostKeyChecking=yes \
	-o UserKnownHostsFile="$known_hosts_path" \
	-o GlobalKnownHostsFile=/dev/null \
	-o WarnWeakCrypto=no \
	-o LogLevel=ERROR \
	"$TARGET" \
	"sudo -n env GEMINI_OBSERVER_SAMPLES=$samples GEMINI_OBSERVER_INTERVAL=$interval sh -s" \
	<"$script_dir/remote-probe.sh" >"$partial"
ssh_status=$?
set -e
chmod 0600 "$partial"

[[ "$(file_sha256 "$identity")" == "$identity_start_sha256" ]] || \
	die 'Gemini SSH identity changed during collection'
[[ "$(file_sha256 "$known_hosts_path")" == "$known_hosts_start_sha256" ]] || \
	die 'known-hosts database changed during collection'
if ((ssh_status != 0)); then
	printf 'error: remote collector failed with status %s; preserving partial evidence: %s\n' \
		"$ssh_status" "$partial" >&2
	exit "$ssh_status"
fi

mv "$partial" "$output"

printf 'capture=%s\n' "$output"
printf 'bytes=%s\n' "$(wc -c <"$output" | tr -d ' ')"
printf 'sha256=%s\n' "$(shasum -a 256 "$output" | awk '{print $1}')"
printf 'remote_files_created=none\n'
printf 'state_changing_device_writes=none\n'
printf 'target=%s\n' "$TARGET"
printf 'sampling_sleep_seconds=%s\n' "$sampling_sleep_seconds"
printf 'wall_timeout_seconds=%s\n' "$wall_timeout_seconds"
