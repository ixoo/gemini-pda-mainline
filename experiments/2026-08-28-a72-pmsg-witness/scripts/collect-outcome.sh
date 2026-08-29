#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	cat <<'EOF'
usage: collect-outcome.sh --target USER@HOST --output-name NAME [OPTIONS]

Wait for one confirmed disconnect/reconnect/changed-boot-ID cycle, collect the
known-good Gemian pstore, and classify the exact pmsg-ramoops-0 witness.

Options:
  --identity FILE       SSH identity passed to the collector
  --wait-seconds N      Complete-cycle deadline (default: 300)
  --ask-sudo-password   Ask once before the cycle when sudo is not passwordless
  -h, --help            Show this help
EOF
}

target=
output_name=
identity=
wait_seconds=300
ask_sudo_password=0
while (($#)); do
	case "$1" in
	--target) target=${2:-}; shift 2 ;;
	--output-name) output_name=${2:-}; shift 2 ;;
	--identity) identity=${2:-}; shift 2 ;;
	--wait-seconds) wait_seconds=${2:-}; shift 2 ;;
	--ask-sudo-password) ask_sudo_password=1; shift ;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown argument: $1" ;;
	esac
done
[[ "$target" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9._-]*$ ]] ||
	die '--target must be a simple USER@HOST value'
[[ "$output_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] ||
	die '--output-name must be a simple directory name'
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || die '--wait-seconds must be positive'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_dir="$(cd -- "$script_dir/../../../" && pwd -P)"
collector="$repo_dir/scripts/collect-device-pstore"
validator="$script_dir/validate_pmsg.py"
output="$repo_dir/artifacts/device-pstore/$output_name"
readonly COLLECTOR_SHA256=9047084f3012aff47e23e56498d4bc0ae6f8fb7e4f15caec10abb6c15e9a9b3b
readonly VALIDATOR_SHA256=4aceef4150953fea326e7479076023d9ad0fd518642584af8dbf108ee1ebd52f
readonly CANDIDATE_RAW_SHA256=f2be7936996ea5a2d94f236c584e2b41b1b61a6eb8877e615a2b5d344547fdad
readonly CANDIDATE_PADDED_SHA256=0814c06b9bb41aa7ec666ad1abbb4bbf86e113e11878ac3de159d6cec3112f78

for command in awk python3 sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "missing command: $command"
done
for input in "$collector" "$validator"; do
	[[ -f "$input" && ! -L "$input" && -x "$input" ]] ||
		die "unsafe runtime tool: $input"
done
[[ "$(sha256sum "$collector" | awk '{print $1}')" == "$COLLECTOR_SHA256" ]] ||
	die 'pstore collector changed'
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] ||
	die 'pmsg validator changed'
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"

collector_args=(
	--target "$target"
	--output "artifacts/device-pstore/$output_name"
	--wait-seconds "$wait_seconds"
	--wait-for-cycle
	--expected-kernel 3.18.41+
)
if [[ -n "$identity" ]]; then
	collector_args+=(--identity "$identity")
fi
if ((ask_sudo_password)); then
	collector_args+=(--ask-sudo-password)
fi

printf 'expected_candidate_raw_sha256=%s\n' "$CANDIDATE_RAW_SHA256"
printf 'expected_candidate_padded_sha256=%s\n' "$CANDIDATE_PADDED_SHA256"
"$collector" "${collector_args[@]}"
python3 "$validator" --capture "$output"
