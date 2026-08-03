#!/usr/bin/env bash

# Source-pin and derive the bounded-coherency Android-v0 candidate builder from
# the stable held-online constructor while pinning every intervening gate.
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
		die 'bounded-coherency compile provenance is missing or unsafe'
	[[ "$(jq -er '.repository_commit' "$bundle/provenance/build.json")" == \
		938cdefde98522a2cd3504605aee04e4c83d5671 ]] ||
		die 'compile repository commit changed'
	[[ "$(jq -er '.terminal_patchset_sha256' "$bundle/provenance/build.json")" == \
		2d94a2cd489e33a7df854ffec7533fbf969dc9c810e9eece57d118b905060310 ]] ||
		die 'terminal parent patchset changed'
	[[ "$(jq -er '.coherence_patchset_sha256' "$bundle/provenance/build.json")" == \
		d4c40577b9e91fedfde048b29cb203311de264c526c71e3abd907fc6fafcf67f ]] ||
		die 'bounded-coherency patchset changed'
	[[ "$(jq -er '.purpose' "$bundle/provenance/build.json")" == \
		cpu9-bounded-coherency-compile-review-only ]] ||
		die 'bounded-coherency compile purpose changed'
fi

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-cpu9-coherence-builder.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_CPU9_COHERENCE_SCRIPT_DIR:?missing}"#g;
	s#118ff3cb3e9a2fbee10a44ada748e46bbe9b5312#938cdefde98522a2cd3504605aee04e4c83d5671#g;
	s#9158af17b17e483ec68257378e5c4bd923b254e7242b5ba338f1324eec5f960b#04602bc2cf61c8ca1232457eba608e347c29eebda7ce6c2d811004051748e604#g;
	s#53046cf314f76f213abafa53a1e79758ff835941d78a47ecc878d0a2e1ad3789#647ebe58da86171b3a36ddd5225bc564b11be4e9799f94fe4b35b9bd005ef139#g;
	s#936b9256709514938ddf2f3ab13e63bd9c8d37e991fe40a568aa36a8f8818018#eda1d5bb312aa937e41499ea8fd13a5f8ae95865399605fe7cf93ee61daaa23d#g;
	s#readonly HELD_PATCHSET_SHA256=e6da1e8cc976ad63dd9cf8a254bb7234d73589cfad6afeb07135403a27d03ba3#readonly HELD_PATCHSET_SHA256=e6da1e8cc976ad63dd9cf8a254bb7234d73589cfad6afeb07135403a27d03ba3\nreadonly LATE_PATCHSET_SHA256=f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91\nreadonly CPU9_PATCHSET_SHA256=17733d2ae50c16f9d0db2d4bd4075fa5a72ce081606db7d3bf1bfe83f4159a2b\nreadonly WINDOW_PATCHSET_SHA256=9ce572fbc87a1444bb71894dd4528f39dc065a45b36db52a14791f167eeec\nreadonly TERMINAL_PATCHSET_SHA256=2d94a2cd489e33a7df854ffec7533fbf969dc9c810e9eece57d118b905060310\nreadonly COHERENCE_PATCHSET_SHA256=d4c40577b9e91fedfde048b29cb203311de264c526c71e3abd907fc6fafcf67f#g;
	s#held-online-compile-review-only#cpu9-bounded-coherency-compile-review-only#g;
	s#\.gemian-a72-held#\.gemian-a72-cpu9-coherence#g;
	s#gemian-a72-cpu8-held-online\.boot\.img#gemian-a72-cpu9-bounded-coherency.boot.img#g;
	s#experiment=2026-08-02-a72-cpu8-held-online#experiment=2026-08-03-a72-cpu9-bounded-coherency#g;
	s#printf '\''held_patchset_sha256=%s\\n'\'' "\$HELD_PATCHSET_SHA256"#printf '\''held_patchset_sha256=%s\\n'\'' "\$HELD_PATCHSET_SHA256"\n  printf '\''late_patchset_sha256=%s\\n'\'' "\$LATE_PATCHSET_SHA256"\n  printf '\''cpu9_patchset_sha256=%s\\n'\'' "\$CPU9_PATCHSET_SHA256"\n  printf '\''window_patchset_sha256=%s\\n'\'' "\$WINDOW_PATCHSET_SHA256"\n  printf '\''terminal_patchset_sha256=%s\\n'\'' "\$TERMINAL_PATCHSET_SHA256"\n  printf '\''coherence_patchset_sha256=%s\\n'\'' "\$COHERENCE_PATCHSET_SHA256"#g;
	s#gemian-a72-cpu8-held-online-\$\{raw_sha256:0:12\}#gemian-a72-cpu9-bounded-coherency-\${raw_sha256:0:12}#g;
	s#gemian-a72-cpu8-held-online-candidate#gemian-a72-cpu9-bounded-coherency-candidate#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"

for token in \
	'REPOSITORY_COMMIT=938cdefde98522a2cd3504605aee04e4c83d5671' \
	'COHERENCE_PATCHSET_SHA256=d4c40577b9e91fedfde048b29cb203311de264c526c71e3abd907fc6fafcf67f' \
	'KERNEL_SHA256=04602bc2cf61c8ca1232457eba608e347c29eebda7ce6c2d811004051748e604' \
	'EXPECTED_RAW_SHA256=647ebe58da86171b3a36ddd5225bc564b11be4e9799f94fe4b35b9bd005ef139' \
	'EXPECTED_PADDED_SHA256=eda1d5bb312aa937e41499ea8fd13a5f8ae95865399605fe7cf93ee61daaa23d' \
	'cpu9-bounded-coherency-compile-review-only' \
	'coherence_patchset_sha256=%s' \
	'gemian-a72-cpu9-bounded-coherency-candidate'; do
	grep -Fq "$token" "$derived" || die "derived builder lacks: $token"
done
! grep -Fq 'cpu9-terminal-attribution-compile-review-only' "$derived" ||
	die 'derived builder retains old compile purpose'
export GEMINI_CPU9_COHERENCE_SCRIPT_DIR="$script_dir"
"$derived" "$@"
