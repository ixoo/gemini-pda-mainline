#!/usr/bin/env bash

# Add the exact Stage-27 CPU clock metadata required by the pinned LK iterator.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'Usage: %s --base-dtb FILE --output FILE\n' "$0"; }

base_dtb=
output=
while (($#)); do
	case "$1" in
	--base-dtb) base_dtb=${2:-}; shift 2 ;;
	--output) output=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$base_dtb" && -n "$output" ]] || { usage >&2; exit 2; }
for command in awk chmod cp dirname dtc fdtget fdtput mkdir mktemp mv rm sha256sum sort; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$base_dtb" && ! -L "$base_dtb" && -s "$base_dtb" ]] ||
	die 'base DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
mkdir -p -- "$(dirname -- "$output")"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-17-mainline-i2c5-serviceability-restoration/scripts/build-serviceability-dtb.sh"
readonly SOURCE_BUILDER_SHA256=b63913108ab329915e505c6fbee54b6c85338dcb80252dbee9b9731142ee9503
readonly PREDECESSOR_DTB_SHA256=a6b76ffc352e818d90709712a372c583ee275baf5f06ebf2cd11f593022b429c
readonly OUTPUT_DTB_SHA256=a87558efd982007798b1c706b4df9e8048b71954423d45bbaf5fbe32515e2f14
readonly CPU_PROPERTIES=clock-frequency,compatible,device_type,enable-method,reg
readonly SCP=/scp@10020000
readonly WDT=/watchdog@10007000
readonly SSUSB=/usb@11271000
readonly XHCI=/usb@11271000/usb@11270000
readonly I2C5=/i2c@1101c000
readonly AW9523=/i2c@1101c000/gpio-expander@5b
readonly KEYBOARD=/keyboard-matrix

readonly -a CPU_NODES=(
	/cpus/cpu@0 /cpus/cpu@1 /cpus/cpu@2 /cpus/cpu@3
	/cpus/cpu@100 /cpus/cpu@101 /cpus/cpu@102 /cpus/cpu@103
	/cpus/cpu@200 /cpus/cpu@201
)
readonly -a CPU_CLOCKS=(
	1391000000 1391000000 1391000000 1391000000
	1950000000 1950000000 1950000000 1950000000
	2288000000 2288000000
)

[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_BUILDER_SHA256" ]] ||
	die 'source I2C5 predecessor builder changed'

temporary="$(mktemp "$(dirname -- "$output")/.lk-cpu-clock-dtb.XXXXXXXX")"
rm -f -- "$temporary"
cleanup() { [[ ! -e "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT HUP INT TERM
"$source_builder" --base-dtb "$base_dtb" --output "$temporary" >/dev/null
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$PREDECESSOR_DTB_SHA256" ]] ||
	die 'stopped I2C5 predecessor DT changed'

actual_cpu_names="$(fdtget -l "$temporary" /cpus | awk \
	'BEGIN { first=1 } { if (!first) printf " "; printf "%s", $0; first=0 } END { print "" }')"
readonly EXPECTED_CPU_NAMES='cpu@0 cpu@1 cpu@2 cpu@3 cpu@100 cpu@101 cpu@102 cpu@103 cpu@200 cpu@201'
[[ "$actual_cpu_names" == "$EXPECTED_CPU_NAMES" ]] || die 'CPU node order changed'

for index in "${!CPU_NODES[@]}"; do
	node=${CPU_NODES[$index]}
	if fdtget "$temporary" "$node" clock-frequency >/dev/null 2>&1; then
		die "predecessor unexpectedly has clock-frequency: $node"
	fi
	fdtput -tu "$temporary" "$node" clock-frequency "${CPU_CLOCKS[$index]}"
done

dtc -q -I dtb -O dtb -o /dev/null "$temporary"
for index in "${!CPU_NODES[@]}"; do
	node=${CPU_NODES[$index]}
	[[ "$(fdtget -tu "$temporary" "$node" clock-frequency)" == "${CPU_CLOCKS[$index]}" ]] ||
		die "CPU clock value changed: $node"
	properties="$(fdtget -p "$temporary" "$node" | sort | awk 'BEGIN { first=1 } { if (!first) printf ","; printf "%s", $0; first=0 } END { print "" }')"
	[[ "$properties" == "$CPU_PROPERTIES" ]] || die "CPU property inventory changed: $node"
done

[[ "$(fdtget -ts "$temporary" "$SCP" status)" == disabled ]] || die 'SCP closure changed'
if fdtget "$temporary" "$WDT" interrupts >/dev/null 2>&1; then
	die 'stopped watchdog IRQ was restored'
fi
[[ "$(fdtget -ts "$temporary" "$SSUSB" status)" == okay ]] || die 'USB status changed'
[[ "$(fdtget -ts "$temporary" "$SSUSB" dr_mode)" == peripheral ]] || die 'USB role changed'
[[ "$(fdtget -ts "$temporary" "$XHCI" status)" == disabled ]] || die 'xHCI closure changed'
[[ "$(fdtget -ts "$temporary" "$I2C5" status)" == okay ]] || die 'I2C5 closure changed'
[[ "$(fdtget -ts "$temporary" "$AW9523" status)" == okay ]] || die 'AW9523 closure changed'
[[ "$(fdtget -ts "$temporary" "$KEYBOARD" status)" == okay ]] || die 'keyboard closure changed'
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
	die 'derived LK CPU-clock DT identity changed'

mv "$temporary" "$output"
chmod 0600 "$output"
temporary=
trap - EXIT HUP INT TERM
printf 'validation=mainline-lk-cpu-clock-iterator-repair-derivation\n'
printf 'predecessor_dtb_sha256=%s\noutput_dtb_sha256=%s\n' \
	"$PREDECESSOR_DTB_SHA256" "$OUTPUT_DTB_SHA256"
printf 'semantic_delta=exact-Stage27-CPU-clock-frequency-group\n'
printf 'CPU_clock_properties_added=10\nCPU_node_order=Stage27-control-match\n'
printf 'LK_iterator_progress_prerequisite=present\nCPU8_CPU9_admission=closed\n'
printf 'SCP_status=disabled\nwatchdog_IRQ=absent\nUSB_role=peripheral\n'
printf 'I2C5_status=okay\nAW9523_status=okay\nkeyboard_status=okay\n'
printf 'xhci_status=disabled\nrole=peripheral\nmaximum_speed=high-speed\n'
printf 'device_access=none\nhardware_write=none\nresult=pass\n'
