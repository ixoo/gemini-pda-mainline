#!/usr/bin/env bash

# Source-pin and derive the retention-window Android-v0 candidate builder from
# the stable held-online constructor while adding every intervening identity.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod grep jq mktemp perl rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-02-a72-cpu8-held-online/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=65c39fa45b1f76fb85780473feb3b675bd5e6647934e68be2761bc823c07e0fe
[[ -f "$source_builder" && ! -L "$source_builder" &&
	"$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_BUILDER_SHA256" ]] ||
	die 'source held-online candidate builder changed'

bundle=
arguments=("$@")
for ((index = 0; index < ${#arguments[@]}; index++)); do
	if [[ "${arguments[index]}" == --bundle && $((index + 1)) -lt ${#arguments[@]} ]]; then
		bundle=${arguments[index + 1]}
	fi
done
if [[ -n "$bundle" ]]; then
	[[ -f "$bundle/provenance/build.json" && ! -L "$bundle/provenance/build.json" ]] ||
		die 'retention-window compile provenance is missing or unsafe'
	[[ "$(jq -er '.late_patchset_sha256' "$bundle/provenance/build.json")" == \
		f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91 ]] ||
		die 'late-CPU8 parent patchset changed'
	[[ "$(jq -er '.cpu9_patchset_sha256' "$bundle/provenance/build.json")" == \
		17733d2ae50c16f9d0db2d4bd4075fa5a72ce081606db7d3bf1bfe83f4159a2b ]] ||
		die 'CPU9 parent patchset changed'
	[[ "$(jq -er '.window_patchset_sha256' "$bundle/provenance/build.json")" == \
		9ce572fbc87a1444bb71894dd4528f39dc065065a45b36db52a14791f167eeec ]] ||
		die 'retention-window patchset changed'
	[[ "$(jq -er '.purpose' "$bundle/provenance/build.json")" == \
		cpu9-retention-window-compile-review-only ]] ||
		die 'retention-window compile purpose changed'
fi

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-cpu9-window-builder.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_CPU9_WINDOW_SCRIPT_DIR:?missing}"#g;
	s#118ff3cb3e9a2fbee10a44ada748e46bbe9b5312#be443b37972751708e628d8dc691d7f5c10be3ba#g;
	s#9158af17b17e483ec68257378e5c4bd923b254e7242b5ba338f1324eec5f960b#97def9a894f84e316349fd01ca7a5044b9b786ea385bb34a4badf242a212c7d4#g;
	s#53046cf314f76f213abafa53a1e79758ff835941d78a47ecc878d0a2e1ad3789#140bed8c432d1ec3ee1d223e06bf51750fc6bbed37cb1d0f596c89f557bffe9c#g;
	s#936b9256709514938ddf2f3ab13e63bd9c8d37e991fe40a568aa36a8f8818018#6f1e5f45c8f75cdfde5a996f902f499d685566c3bec227efa6cdb56aaeffa115#g;
	s#readonly HELD_PATCHSET_SHA256=e6da1e8cc976ad63dd9cf8a254bb7234d73589cfad6afeb07135403a27d03ba3#readonly HELD_PATCHSET_SHA256=e6da1e8cc976ad63dd9cf8a254bb7234d73589cfad6afeb07135403a27d03ba3\nreadonly LATE_PATCHSET_SHA256=f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91\nreadonly CPU9_PATCHSET_SHA256=17733d2ae50c16f9d0db2d4bd4075fa5a72ce081606db7d3bf1bfe83f4159a2b\nreadonly WINDOW_PATCHSET_SHA256=9ce572fbc87a1444bb71894dd4528f39dc065065a45b36db52a14791f167eeec#g;
	s#held-online-compile-review-only#cpu9-retention-window-compile-review-only#g;
	s#\.gemian-a72-held#\.gemian-a72-cpu9-window#g;
	s#gemian-a72-cpu8-held-online\.boot\.img#gemian-a72-cpu9-retention-window.boot.img#g;
	s#experiment=2026-08-02-a72-cpu8-held-online#experiment=2026-08-03-a72-cpu9-retention-window#g;
	s#printf '\''held_patchset_sha256=%s\\n'\'' "\$HELD_PATCHSET_SHA256"#printf '\''held_patchset_sha256=%s\\n'\'' "\$HELD_PATCHSET_SHA256"\n  printf '\''late_patchset_sha256=%s\\n'\'' "\$LATE_PATCHSET_SHA256"\n  printf '\''cpu9_patchset_sha256=%s\\n'\'' "\$CPU9_PATCHSET_SHA256"\n  printf '\''window_patchset_sha256=%s\\n'\'' "\$WINDOW_PATCHSET_SHA256"#g;
	s#gemian-a72-cpu8-held-online-\$\{raw_sha256:0:12\}#gemian-a72-cpu9-retention-window-\${raw_sha256:0:12}#g;
	s#gemian-a72-cpu8-held-online-candidate#gemian-a72-cpu9-retention-window-candidate#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"

for token in \
	'REPOSITORY_COMMIT=be443b37972751708e628d8dc691d7f5c10be3ba' \
	'LATE_PATCHSET_SHA256=f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91' \
	'CPU9_PATCHSET_SHA256=17733d2ae50c16f9d0db2d4bd4075fa5a72ce081606db7d3bf1bfe83f4159a2b' \
	'WINDOW_PATCHSET_SHA256=9ce572fbc87a1444bb71894dd4528f39dc065065a45b36db52a14791f167eeec' \
	'KERNEL_SHA256=97def9a894f84e316349fd01ca7a5044b9b786ea385bb34a4badf242a212c7d4' \
	'EXPECTED_RAW_SHA256=140bed8c432d1ec3ee1d223e06bf51750fc6bbed37cb1d0f596c89f557bffe9c' \
	'EXPECTED_PADDED_SHA256=6f1e5f45c8f75cdfde5a996f902f499d685566c3bec227efa6cdb56aaeffa115' \
	'cpu9-retention-window-compile-review-only' \
	'window_patchset_sha256=%s' \
	'gemian-a72-cpu9-retention-window-candidate'; do
	grep -Fq "$token" "$derived" || die "derived builder lacks: $token"
done
! grep -Fq 'held-online-compile-review-only' "$derived" ||
	die 'derived builder retains old compile purpose'
export GEMINI_CPU9_WINDOW_SCRIPT_DIR="$script_dir"
"$derived" "$@"
