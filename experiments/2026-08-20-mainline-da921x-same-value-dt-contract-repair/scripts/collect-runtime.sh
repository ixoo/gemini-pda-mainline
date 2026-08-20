#!/usr/bin/env bash

# Derive the one-token collector with durable pretrigger lifecycle evidence.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e803aff77af72346fe87856ab628434ab2f70b922b5696f83533e11d32f4cbac

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-19-mainline-da921x-same-value-write-implementation/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived="$(mktemp "$script_dir/.derived-collect-runtime.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("b81813d13acc970c7b9203b89ec034921ef6f7e1017539a0c228754619af7b22",
     "85dbd8d020cc6d3527743f05d4a1071a8f573407a5519ae1584127e55e33bae9", 1),
    ("d28ae6cdf63ca0923f2101ad7252a9908824697280754a69d9e709b553172d54",
     "ae9acfcad3c80e979dee6ce612198bf9cc1a8ffe9cd77379987309338a8d9278", 1),
    ("088f6746d8435f43d721b5d666f2111117239aa83c151b2535cb8d488f600f8e",
     "9a960968371d7c08cd184921e52cf6b1c161df5d07f0b061657d01a91f61bbdb", 1),
    ("artifacts/da921x-same-value-write/candidate-mainline-da921x-same-value-write-b84f3ba8/boot2-padded.img",
     "artifacts/da921x-same-value-dt-contract-repair/candidate-mainline-da921x-same-value-dt-repair-87b38fc4/boot2-padded.img", 1),
    ("usage: %s --deployment-boot-id UUID --output artifacts/runtime-captures/mainline-da921x-same-value-write-attempt-1",
     "usage: %s --deployment-boot-id UUID --output artifacts/runtime-captures/mainline-da921x-same-value-dt-repair-attempt-1", 1),
    ("experiment=2026-08-19-mainline-da921x-same-value-write-implementation",
     "experiment=2026-08-20-mainline-da921x-same-value-dt-contract-repair", 1),
    ('classifier="$script_dir/classify-runtime.py"',
     'classifier="$repo_root/experiments/2026-08-19-mainline-da921x-same-value-write-implementation/scripts/classify-runtime.py"', 1),
    ("current=\"$(ioreg -p IOUSB -l -w 0 2>/dev/null | grep -E 'Gemini|MediaTek|RNDIS|CDC' || true)\"",
     "current=\"$(ioreg -p IOUSB -l -w 0 2>/dev/null | grep -Eo 'Gemini|MediaTek|RNDIS|CDC' | sort -u | tr '\\n' ',' || true)\"", 1),
    ('python3 "$classifier" --pretrigger "$pretrigger" >"$pretrigger_classification"\n'
     "grep -Fqx 'runtime_classification=pretrigger-exact-20' \"$pretrigger_classification\" ||\n"
     "\tdie 'pretrigger capture was rejected'\n",
     'set +e\n'
     'python3 "$classifier" --pretrigger "$pretrigger" >"$pretrigger_classification" '
     '2>"$output/pretrigger-classifier-stderr.txt"\n'
     'pretrigger_classifier_status=$?\n'
     'set -e\n'
     'if ((pretrigger_classifier_status != 0)); then\n'
     '\tpretrigger_failure=pretrigger-rejected-no-token\n'
     '\tif grep -Fqx da921x_i2c_client_count=0 "$pretrigger"; then\n'
     '\t\tpretrigger_failure=pretrigger-no-da921x-client-no-token\n'
     '\telif grep -Fqx same_value_write_attribute_count=0 "$pretrigger"; then\n'
     '\t\tpretrigger_failure=pretrigger-no-same-value-attribute-no-token\n'
     '\tfi\n'
     '\tprintf "runtime_classification=%s\\ntrigger_attempts=0\\ntrigger_retries=0\\nresult=stopped\\n" '
     '"$pretrigger_failure" >"$classification"\n'
     '\tprintf "classification=%s\\npretrigger_durable_before_stop=yes\\ntrigger_token_attempts=0\\n" '
     '"$pretrigger_failure" >>"$events"\n'
     '\tsync\n'
     '\texit 5\n'
     'fi\n'
     "grep -Fqx 'runtime_classification=pretrigger-exact-20' \"$pretrigger_classification\" ||\n"
     "\tdie 'pretrigger classifier did not retain its pass result'\n", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe collector derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
