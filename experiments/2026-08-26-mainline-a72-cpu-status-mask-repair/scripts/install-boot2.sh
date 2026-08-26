#!/usr/bin/env bash

# Source-pin the movement-attribution installer and retarget it to the exact
# CPU-status-mask candidate and exact movement-attribution predecessor.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0051eaff77442d71be36c24e1b995ce2d62c9b0ab41438ce71b5980e98d29bf1
readonly DEVICE_ADDRESS=192.168.1.50
readonly SHUTDOWN_HELPER_SHA256=35317e3533cb0c9b757e198b519fac8be0f88fa1f9e423c4e717fcabb276b833
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-26-mainline-a72-platform-movement-attribution/scripts/install-boot2.sh"
shutdown_helper="$script_dir/confirm-shutdown-port.py"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ -f "$shutdown_helper" && ! -L "$shutdown_helper" && -x "$shutdown_helper" ]] ||
	die 'shutdown TCP helper is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'
[[ "$(sha256sum "$shutdown_helper" | awk '{print $1}')" == "$SHUTDOWN_HELPER_SHA256" ]] ||
	die 'shutdown TCP helper changed'

require_tcp_shutdown=yes
evidence_dir=
arguments=("$@")
while (($#)); do
	case "$1" in
	--evidence-dir)
		(($# >= 2)) || die '--evidence-dir requires a value'
		evidence_dir=$2
		shift 2
		;;
	--record-preflight-only|-h|--help)
		require_tcp_shutdown=no
		shift
		;;
	*) shift ;;
	esac
done

derived=$(mktemp "$script_dir/.derived-install-boot2-cpu-status-mask.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        "movement-attribution candidate and retired failure-stage predecessor.",
        "CPU-status-mask candidate and exact movement-attribution predecessor.",
        1,
    ),
    (
        '("8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78", 1)',
        '("8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", "6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7", 1)',
        1,
    ),
    (
        '("1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2", "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", 1)',
        '("1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2", "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78", 1)',
        1,
    ),
    ("ace809cb0da37d977f36f9db5c0618b153103767a89cd796e1ed02d783831b48", "fa59a909220097851bed92d6514b2bf3a5c3e1c336a5f7d920fe87737bbc1d08", 1),
    ("candidate-a72-platform-movement-fd070a56", "candidate-a72-cpu-status-mask-ebaddc69", 1),
    ("a72-platform-movement-deployment-", "a72-cpu-status-mask-deployment-", 1),
    (r"\.gemini-a72-platform-movement\.", r"\.gemini-a72-cpu-status-mask\.", 1),
    ("/home/gemini/.gemini-a72-platform-movement.XXXXXXXX", "/home/gemini/.gemini-a72-cpu-status-mask.XXXXXXXX", 1),
    ("2026-08-26-mainline-a72-platform-movement-attribution", "2026-08-26-mainline-a72-cpu-status-mask-repair", 1),
    (
        '("retired third-reader predecessor", "retired failure-stage predecessor", 1)',
        '("retired third-reader predecessor", "exact movement-attribution predecessor", 1)',
        1,
    ),
    (".derived-install-boot2-platform-movement-inner.XXXXXXXX", ".derived-install-boot2-cpu-status-mask-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU-status-mask installer derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "${arguments[@]}"
status=$?
set -e
if [[ "$status" == 0 && "$require_tcp_shutdown" == yes ]]; then
	set +e
	shutdown_output=$(python3 "$shutdown_helper" --address "$DEVICE_ADDRESS" \
		--port 22 --attempts 20 --required-consecutive 3 --interval 2 --timeout 1)
	shutdown_status=$?
	set -e
	printf '%s\n' "$shutdown_output"
	if [[ "$shutdown_status" != 0 ]]; then
		printf 'error: write/readback passed but TCP/22 remains open; shutdown is not confirmed\n' >&2
		status=2
	else
		case "$evidence_dir" in /*) ;; *) evidence_dir="$repo_root/${evidence_dir#./}" ;; esac
		summary="$evidence_dir/deployment-summary.txt"
		[[ -f "$summary" && ! -L "$summary" ]] || die 'deployment summary missing after TCP shutdown proof'
		printf '%s\nshutdown_confirmation=ssh-failure-plus-three-tcp-closures\n' \
			"$shutdown_output" >>"$summary"
		(
			cd "$evidence_dir"
			sha256sum deployment-summary.txt >SHA256SUMS
		)
		chmod 0600 "$evidence_dir/SHA256SUMS"
	fi
fi
cleanup
trap - EXIT HUP INT TERM
exit "$status"
