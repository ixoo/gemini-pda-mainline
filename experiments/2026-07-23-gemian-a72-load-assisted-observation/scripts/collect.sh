#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --tag SAFE-TAG\n' "$0" >&2; }

tag=
while (($#)); do
	case "$1" in
	--tag)
		(($# >= 2)) || die '--tag requires a value'
		tag=$2
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

[[ "$tag" =~ ^[a-z0-9][a-z0-9-]{0,63}$ ]] || die 'tag is absent or unsafe'

readonly TARGET=gemini@192.168.1.50
readonly IDENTITY_RELATIVE=artifacts/credentials/gemini_ed25519
readonly OBSERVER_SAMPLES=70
readonly OBSERVER_REMOTE_TIMEOUT=95
readonly OBSERVER_HOST_TIMEOUT=105
readonly LOAD_REMOTE_TIMEOUT=55
readonly LOAD_HOST_TIMEOUT=65
readonly OBSERVER_SYNC_TIMEOUT=20
readonly EXPECTED_OBSERVER_REMOTE_SHA256=b08e2b442a95c06f4a4b131a4ca27a19289f21fee01f0d9ade6b8b59f656ccbc
readonly EXPECTED_LOAD_REMOTE_SHA256=c04bdfda47676645ef55dc5d99c5d067076b59e6246ae29baa20d848bcd0992d
readonly EXPECTED_BOUNDED_EXEC_SHA256=e250c4f0375aed986bc73eeea699cf5f4ba51625aa51a1ede2d40ac601f62ce5
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
identity="$repo_root/$IDENTITY_RELATIVE"
known_hosts="${HOME:?HOME is not set}/.ssh/known_hosts"
private_root="$repo_root/artifacts/runtime-captures"
readonly_remote="$repo_root/experiments/2026-07-22-gemian-a72-readonly-discovery/scripts/remote-probe.sh"
load_remote="$script_dir/remote-load-probe.sh"
bounded_exec="$script_dir/bounded-exec.pl"
load_capture="$private_root/gemian-a72-load-assisted-$tag-load.txt"
load_partial="$load_capture.partial"
observer_capture="$private_root/gemian-a72-readonly-load-assisted-$tag-observer.txt"
observer_partial="$observer_capture.partial"

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1" 2>/dev/null; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }

[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 ]] ||
	die 'exact Gemini identity is absent or unsafe'
[[ -f "$known_hosts" && ! -L "$known_hosts" && "$(file_mode "$known_hosts")" == 600 ]] ||
	die 'known-hosts database is absent or unsafe'
[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] ||
	die 'private capture root is absent or unsafe'
[[ -f "$readonly_remote" && ! -L "$readonly_remote" &&
	-f "$load_remote" && ! -L "$load_remote" &&
	-f "$bounded_exec" && ! -L "$bounded_exec" ]] ||
	die 'collector dependency is absent'
[[ "$(file_sha256 "$readonly_remote")" == "$EXPECTED_OBSERVER_REMOTE_SHA256" ]] ||
	die 'read-only observer input differs from the reviewed revision'
[[ "$(file_sha256 "$load_remote")" == "$EXPECTED_LOAD_REMOTE_SHA256" ]] ||
	die 'load probe input differs from the reviewed revision'
[[ "$(file_sha256 "$bounded_exec")" == "$EXPECTED_BOUNDED_EXEC_SHA256" ]] ||
	die 'bounded-exec input differs from the reviewed revision'
identity_start_sha256=$(file_sha256 "$identity")
known_hosts_start_sha256=$(file_sha256 "$known_hosts")

for path in "$load_capture" "$load_partial" "$observer_capture" \
	"$observer_partial"
do
	[[ ! -e "$path" && ! -L "$path" ]] || die "output already exists: $path"
	git -C "$repo_root" check-ignore -q -- "$path" || die "output is not ignored: $path"
done

observer_pid=
load_pid=
deferred_host_signal=0
host_cleanup()
{
	trap - EXIT
	trap '' HUP INT PIPE TERM
	for pid in ${load_pid:-} ${observer_pid:-}; do
		[[ -n "$pid" ]] || continue
		kill -TERM "$pid" 2>/dev/null || true
	done
	for pid in ${load_pid:-} ${observer_pid:-}; do
		[[ -n "$pid" ]] || continue
		wait "$pid" 2>/dev/null || true
	done
	[[ ! -e "$load_partial" ]] || chmod 0600 "$load_partial"
	[[ ! -e "$observer_partial" ]] || chmod 0600 "$observer_partial"
}
host_signal()
{
	host_cleanup
	printf 'error: collection interrupted; partial evidence preserved\n' >&2
	exit 4
}
defer_host_signal()
{
	deferred_host_signal=1
}
trap host_cleanup EXIT
trap host_signal HUP INT PIPE TERM

start_observer()
{
	deferred_host_signal=0
	trap defer_host_signal HUP INT PIPE TERM
	perl "$bounded_exec" "$OBSERVER_HOST_TIMEOUT" -- ssh \
		-F /dev/null \
		-i "$identity" \
		-o IdentitiesOnly=yes \
		-o IdentityAgent=none \
		-o BatchMode=yes \
		-o ConnectTimeout=5 \
		-o ServerAliveInterval=5 \
		-o ServerAliveCountMax=3 \
		-o StrictHostKeyChecking=yes \
		-o UserKnownHostsFile="$known_hosts" \
		-o GlobalKnownHostsFile=/dev/null \
		-o WarnWeakCrypto=no \
		-o LogLevel=ERROR \
		"$TARGET" \
		"sudo -n env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C GEMINI_OBSERVER_SAMPLES=$OBSERVER_SAMPLES GEMINI_OBSERVER_INTERVAL=1 timeout --signal=TERM --kill-after=1s ${OBSERVER_REMOTE_TIMEOUT}s sh -s" \
		<"$readonly_remote" >"$observer_partial" &
	observer_pid=$!
	trap host_signal HUP INT PIPE TERM
	((deferred_host_signal == 0)) || host_signal
}

start_load()
{
	deferred_host_signal=0
	trap defer_host_signal HUP INT PIPE TERM
	perl "$bounded_exec" "$LOAD_HOST_TIMEOUT" -- ssh \
		-F /dev/null \
		-i "$identity" \
		-o IdentitiesOnly=yes \
		-o IdentityAgent=none \
		-o BatchMode=yes \
		-o ConnectTimeout=5 \
		-o ServerAliveInterval=5 \
		-o ServerAliveCountMax=3 \
		-o StrictHostKeyChecking=yes \
		-o UserKnownHostsFile="$known_hosts" \
		-o GlobalKnownHostsFile=/dev/null \
		-o WarnWeakCrypto=no \
		-o LogLevel=ERROR \
		"$TARGET" \
		"sudo -n env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C timeout --signal=TERM --kill-after=1s ${LOAD_REMOTE_TIMEOUT}s sh -s" \
		<"$load_remote" >"$load_partial" &
	load_pid=$!
	trap host_signal HUP INT PIPE TERM
	((deferred_host_signal == 0)) || host_signal
}

start_observer
sync_deadline=$((SECONDS + OBSERVER_SYNC_TIMEOUT))
while ! grep -Fqx 'sample_end=1' "$observer_partial" 2>/dev/null; do
	if ! kill -0 "$observer_pid" 2>/dev/null; then
		set +e
		wait "$observer_pid"
		observer_early_status=$?
		set -e
		observer_pid=
		die "read-only observer exited before synchronization (status $observer_early_status)"
	fi
	((SECONDS < sync_deadline)) ||
		die 'read-only observer did not complete its first natural sample in time'
	sleep 0.1
done
start_load

set +e
wait "$load_pid"
load_status=$?
set -e
load_pid=
if ((load_status != 0)); then
	kill -TERM "$observer_pid" 2>/dev/null || true
	set +e
	wait "$observer_pid"
	observer_status=$?
	set -e
	observer_pid=
	chmod 0600 "$load_partial" "$observer_partial"
	printf 'error: load probe failed with status %s; partial evidence preserved\n' \
		"$load_status" >&2
	exit 3
fi

set +e
wait "$observer_pid"
observer_status=$?
set -e
observer_pid=

chmod 0600 "$load_partial" "$observer_partial"
if ((observer_status != 0)); then
	printf 'error: read-only observer failed with status %s; partial preserved: %s\n' \
		"$observer_status" "$observer_partial" >&2
	exit 3
fi

grep -Fqx 'status=completed' "$load_partial" ||
	die 'load probe did not emit its completion marker'
grep -Fqx '__GEMIAN_A72_COMPLETE__' "$observer_partial" ||
	die 'read-only observer did not emit its completion section'
grep -Fqx 'boot_id_stable_through_capture=yes' "$observer_partial" ||
	die 'read-only observer did not prove boot-ID stability'

load_uptime_begin=$(awk -F= '/^run_uptime_begin=/ { print $2; exit }' "$load_partial")
load_uptime_end=$(awk -F= '/^run_uptime_end=/ { print $2; exit }' "$load_partial")
observer_uptime_begin=$(awk -F= '
	$0 == "__GEMIAN_A72_NATURAL_SAMPLES__" { sampling = 1; next }
	sampling && /^uptime_before=/ { print $2; exit }
' "$observer_partial")
observer_uptime_end=$(awk -F= '
	$0 == "__GEMIAN_A72_NATURAL_SAMPLES__" { sampling = 1; next }
	$0 == "__GEMIAN_A72_SAMPLING_BOUNDARY__" { sampling = 0 }
	sampling && /^uptime_after=/ { last = $2 }
	END { print last }
' "$observer_partial")
[[ -n "$load_uptime_begin" && -n "$load_uptime_end" &&
	-n "$observer_uptime_begin" && -n "$observer_uptime_end" ]] ||
	die 'capture uptime coverage fields are absent'
awk -v observer_begin="$observer_uptime_begin" \
	-v load_begin="$load_uptime_begin" \
	-v load_end="$load_uptime_end" \
	-v observer_end="$observer_uptime_end" '
	BEGIN {
		exit !((observer_begin + 0) <= (load_begin + 0) &&
			(observer_end + 0) >= (load_end + 0))
	}
' || die 'read-only observer did not span the full load probe'

load_observed_a72=$(awk -F= '/^observed_a72=/ { print $2; exit }' "$load_partial")
case "$load_observed_a72" in
yes)
	first_a72_uptime=$(awk -F= '/^first_a72_uptime=/ { print $2; exit }' \
		"$load_partial")
	[[ "$first_a72_uptime" =~ ^[0-9]+([.][0-9]+)?$ ]] ||
		die 'load probe A72 observation lacks a valid uptime'
	awk -F= -v target="$first_a72_uptime" '
		$0 == "__GEMIAN_A72_NATURAL_SAMPLES__" { sampling = 1; next }
		$0 == "__GEMIAN_A72_SAMPLING_BOUNDARY__" { sampling = 0 }
		sampling && /^uptime_before=/ {
			delta = ($2 + 0) - (target + 0)
			if (delta < 0)
				delta = -delta
			if (delta <= 1.5)
				found = 1
		}
		END { exit !found }
	' "$observer_partial" ||
		die 'no companion observer sample was near the A72 observation'
	observer_near_a72_sample=yes
	;;
no)
	observer_near_a72_sample=not-applicable
	;;
*)
	die 'load probe emitted an invalid observed_a72 value'
	;;
esac

observer_boot_id=$(awk -F= '/^boot_id=/ { print $2; exit }' "$observer_partial")
observer_boot_id_sha256=$(printf '%s\n' "$observer_boot_id" | shasum -a 256 |
	awk '{ print $1 }')
load_boot_id_sha256=$(awk -F= '/^boot_id_sha256=/ { print $2; exit }' "$load_partial")
[[ "$observer_boot_id_sha256" == "$load_boot_id_sha256" ]] ||
	die 'the two captures do not identify the same boot'
[[ "$(file_sha256 "$identity")" == "$identity_start_sha256" ]] ||
	die 'Gemini SSH identity changed during collection'
[[ "$(file_sha256 "$known_hosts")" == "$known_hosts_start_sha256" ]] ||
	die 'known-hosts database changed during collection'
[[ "$(file_sha256 "$readonly_remote")" == "$EXPECTED_OBSERVER_REMOTE_SHA256" &&
	"$(file_sha256 "$load_remote")" == "$EXPECTED_LOAD_REMOTE_SHA256" &&
	"$(file_sha256 "$bounded_exec")" == "$EXPECTED_BOUNDED_EXEC_SHA256" ]] ||
	die 'a reviewed collector input changed during collection'

mv "$load_partial" "$load_capture"
mv "$observer_partial" "$observer_capture"

printf 'load_capture=%s\n' "$load_capture"
printf 'load_sha256=%s\n' "$(shasum -a 256 "$load_capture" | awk '{ print $1 }')"
printf 'observer_capture=%s\n' "$observer_capture"
printf 'observer_sha256=%s\n' "$(shasum -a 256 "$observer_capture" | awk '{ print $1 }')"
printf 'remote_files_created=none\n'
printf 'cpu_online_writes=none\n'
printf 'policy_writes=none\n'
printf 'partition_access=none\n'
printf 'observer_synchronized_before_load=yes\n'
printf 'observer_spanned_load_and_cooldown=yes\n'
printf 'observer_near_a72_sample=%s\n' "$observer_near_a72_sample"
