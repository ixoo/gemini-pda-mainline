#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C

die() {
	echo "error: $*" >&2
	exit 2
}

for command in jq mktemp python3; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd -P)"
validator="${script_dir}/validate-usbdiag-manifest.py"
current="${repo_root}/kernel/manifest.json"
[[ -s "$validator" && -s "$current" ]] || die "validator inputs are missing"

workdir="$(mktemp -d)"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

# A package created before an unrelated profile was added must remain a valid
# exact usbdiag source, because its source, patch and usbdiag profile inputs did
# not change.
jq 'del(.config.profiles["usbdiag-clkignore"])' "$current" \
	>"${workdir}/prior-manifest.json"
python3 "$validator" --current "$current" \
	--packaged "${workdir}/prior-manifest.json" >/dev/null

# Unrelated profiles are outside this validator's boundary.
jq '.config.profiles.unrelated = {"base":"defconfig","fragments":[]}' \
	"${workdir}/prior-manifest.json" >"${workdir}/unrelated.json"
python3 "$validator" --current "$current" \
	--packaged "${workdir}/unrelated.json" >/dev/null

# Every field that binds the usbdiag package itself remains mandatory.
jq '.schema = 2' "${workdir}/prior-manifest.json" \
	>"${workdir}/bad-schema.json"
if python3 "$validator" --current "$current" \
	--packaged "${workdir}/bad-schema.json" >/dev/null 2>&1; then
	die "validator accepted a changed schema"
fi

jq '.kernel.sha256 = ("0" * 64)' "${workdir}/prior-manifest.json" \
	>"${workdir}/bad-kernel.json"
if python3 "$validator" --current "$current" \
	--packaged "${workdir}/bad-kernel.json" >/dev/null 2>&1; then
	die "validator accepted a changed kernel input"
fi

jq '.architecture = "x86_64"' "${workdir}/prior-manifest.json" \
	>"${workdir}/bad-architecture.json"
if python3 "$validator" --current "$current" \
	--packaged "${workdir}/bad-architecture.json" >/dev/null 2>&1; then
	die "validator accepted a changed architecture"
fi

jq '.patch_series = "patches/other"' "${workdir}/prior-manifest.json" \
	>"${workdir}/bad-series.json"
if python3 "$validator" --current "$current" \
	--packaged "${workdir}/bad-series.json" >/dev/null 2>&1; then
	die "validator accepted a changed patch series"
fi

jq '.config.profiles.usbdiag.fragments = ["configs/other.fragment"]' \
	"${workdir}/prior-manifest.json" >"${workdir}/bad-usbdiag.json"
if python3 "$validator" --current "$current" \
	--packaged "${workdir}/bad-usbdiag.json" >/dev/null 2>&1; then
	die "validator accepted a changed usbdiag profile"
fi

printf 'validation=usbdiag-manifest-validator-regression\n'
printf 'prior_manifest_without_new_profile=accepted\n'
printf 'unrelated_profile_change=accepted\n'
printf 'schema_kernel_architecture_series_usbdiag_mutations=rejected\n'
