#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -d "$1/.git" ]]; then
    printf 'usage: %s REFERENCE_GIT_TREE\n' "$0" >&2
    exit 2
fi

ref=$1
git_ref=(git -C "$ref")

printf 'reference=%s\n' "$ref"
printf 'commit=%s\n' "$("${git_ref[@]}" rev-parse HEAD)"
"${git_ref[@]}" show -s --format='date=%cI%nsubject=%s' HEAD

for file in README.md hardware.md kernel.md driver_ports.md blockers.md boot.md claude.md patches/README.md patches/STANDARDS.md configs/gemini-cmdline.config; do
    if [[ -f "$ref/$file" ]]; then
        sha256sum "$ref/$file"
    fi
done

printf 'patch_count=%s\n' "$(find "$ref/patches/v6.6" -type f -name '*.patch' -print | wc -l | tr -d ' ')"
find "$ref/patches/v6.6" -type f -name '*.patch' -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    | sha256sum \
    | awk '{print "patches_sha256_manifest=" $1}'

printf '\nselected_claim_markers:\n'
for file in README.md hardware.md kernel.md driver_ports.md blockers.md boot.md claude.md; do
    [[ -f "$ref/$file" ]] || continue
    printf '[%s]\n' "$file"
    grep -Ein 'MT6797X|Helio X27|Linux 6\.6|Linux 3\.18|UART0|0x11002000|GPIO97|GPIO98|AW9523B|0x5b|SSD2092|R63419|FUSB301A|MT6351|RT9466|CONSYS|AHB|BTIF|STP|mtk w boot2|mtk w linux|first image|FIRST CORRECT IMAGE|USB gadget SSH|B-18' "$ref/$file" | sed 's/[[:blank:]]*$//' | head -80 || true
done
