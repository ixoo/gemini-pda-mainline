#!/bin/sh
# Read-only, bounded runtime identity-surface census for the named Gemini.
# Only paths, token labels, and counts leave the device; file contents are
# never printed or retained.
set -eu

target=${1:-gemini@192.168.1.50}
key=${GEMINI_SSH_KEY:-artifacts/credentials/gemini_ed25519}

exec ssh -i "$key" \
    -o IdentitiesOnly=yes \
    -o IdentityAgent=none \
    -o ConnectTimeout="${GEMINI_CONNECT_TIMEOUT:-5}" \
    "$target" 'sh -s' <<'REMOTE'
set -eu
export LC_ALL=C

printf '%s\n' '# Gemian runtime identity-surface census'
printf 'kernel=%s\n' "$(uname -r)"
printf 'architecture=%s\n' "$(uname -m)"
printf 'boot_id=%s\n' "$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unavailable)"
printf 'cpu_possible=%s\n' "$(cat /sys/devices/system/cpu/possible 2>/dev/null || echo unavailable)"
printf 'cpu_present=%s\n' "$(cat /sys/devices/system/cpu/present 2>/dev/null || echo unavailable)"
printf 'cpu_online=%s\n' "$(cat /sys/devices/system/cpu/online 2>/dev/null || echo unavailable)"

tmp=${TMPDIR:-/tmp}/gemini-runtime-identity.$$
trap 'rm -f "$tmp" "$tmp.paths"' EXIT HUP INT TERM
: >"$tmp.paths"

for root in /sys/kernel/debug /sys/devices/platform /sys/devices/system/cpu /proc/device-tree; do
    if [ -d "$root" ]; then
        find "$root" -maxdepth 6 -type f 2>/dev/null || true
    fi
done | grep -Ei '/(dvfs|eem|ppm|cpufreq|calib|volt|vsram|vproc|epoch|generation|owner|lock|transition|handle|ptp)(/|$)|/(dvfs|eem|ppm|cpufreq|calib|volt|vsram|vproc|epoch|generation|owner|lock|transition|handle|ptp)[^/]*$' \
    | sort -u | head -n 256 >"$tmp.paths" || true

printf 'candidate_path_count=%s\n' "$(wc -l <"$tmp.paths" | tr -d ' ')"
while IFS= read -r path; do
    [ -r "$path" ] || continue
    printf 'candidate_path=%s\n' "$path"
done <"$tmp.paths"

scan_file() {
    path=$1
    [ -r "$path" ] || return 0
    bytes=$(wc -c <"$path" 2>/dev/null | tr -d ' ' || echo 0)
    hits=
    for token in epoch generation calibration handle owner transition lock mutex atomic; do
        if head -c 4096 "$path" 2>/dev/null \
            | tr '\000' ' ' \
            | grep -Eiq "$token"; then
            hits=${hits:+"$hits,"}$token
        fi
    done
    if [ -n "$hits" ]; then
        printf 'content_token_hit=%s tokens=%s bytes=%s\n' "$path" "$hits" "$bytes"
    fi
    return 0
}

while IFS= read -r path; do
    scan_file "$path"
done <"$tmp.paths"

for path in /proc/ppm /proc/eem /proc/cpufreq; do
    [ -e "$path" ] || continue
    printf 'known_surface=%s\n' "$path"
    if [ -f "$path" ]; then
        scan_file "$path"
    else
        find "$path" -maxdepth 2 -type f 2>/dev/null | sort -u | head -n 64 | while IFS= read -r child; do
            printf 'known_surface_child=%s\n' "$child"
            scan_file "$child"
        done
    fi
done

printf '%s\n' 'raw_payload_retained=none'
printf '%s\n' 'device_action=none'
printf '%s\n' 'hardware_write=none'
REMOTE
