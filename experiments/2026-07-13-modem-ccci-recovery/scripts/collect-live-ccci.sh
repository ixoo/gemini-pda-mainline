#!/usr/bin/env bash

# Read-only CCCI/CLDMA topology inventory. It deliberately avoids opening
# modem character devices, issuing ioctls, reading identifiers, or transmitting
# traffic. The optional dmesg section is omitted because it can contain
# subscriber or network data.

set -u
export LC_ALL=C

section() { printf '\n[%s]\n' "$1"; }

section identity
uname -a 2>/dev/null || true

section ccci-class
for node in /sys/class/ccci_node/*; do
  [ -e "$node" ] || continue
  name=${node##*/}
  printf 'node=%s' "$name"
  [ -r "$node/dev" ] && printf ' dev=%s' "$(cat "$node/dev")"
  [ -L "$node/device/driver" ] && printf ' driver=%s' "$(basename "$(readlink "$node/device/driver")")"
  printf '\n'
done

section ccci-platform
for device in /sys/bus/platform/devices/*; do
  name=${device##*/}
  case "$name" in
    *ccci*|*cldma*|*ccif*|*modem*|*md_*|*md[0-9]*) ;;
    *) continue ;;
  esac
  printf 'device=%s' "$name"
  [ -L "$device/driver" ] && printf ' driver=%s' "$(basename "$(readlink "$device/driver")")"
  printf '\n'
  for prop in compatible reg interrupts clocks clock-names mediatek,md_id mediatek,cldma_capability mediatek,md_smem_size; do
    file="$device/of_node/$prop"
    [ -r "$file" ] || continue
    printf '  %s=' "$prop"
    od -An -tx1 -v "$file" | tr -d ' \n'
    printf '\n'
  done
done

section ccci-fdt
for node in \
  /sys/firmware/devicetree/base/soc/mdcldma@10014000 \
  /sys/firmware/devicetree/base/soc/ap_cldma@10219000 \
  /sys/firmware/devicetree/base/soc/md_cldma@1021a000 \
  /sys/firmware/devicetree/base/soc/ap_ccif0@10209000 \
  /sys/firmware/devicetree/base/soc/md_ccif0@1020a000 \
  /sys/firmware/devicetree/base/soc/ap_ccif1@1020b000 \
  /sys/firmware/devicetree/base/soc/md_ccif1@1020c000 \
  /sys/firmware/devicetree/base/soc/ap2c2k_ccif@1020b000 \
  /sys/firmware/devicetree/base/soc/md2md_md1_ccif0@10211000 \
  /sys/firmware/devicetree/base/soc/md2md_md2_ccif0@10213000 \
  /sys/firmware/devicetree/base/soc/mdhw_smi@1021c000 \
  /sys/firmware/devicetree/base/soc/ccci_util_cfg; do
  [ -d "$node" ] || continue
  printf 'node=%s\n' "${node##*/}"
  for prop in compatible reg interrupts clocks clock-names mediatek,md_id mediatek,cldma_capability mediatek,md_smem_size mediatek,md1-smem-size mediatek,md3-smem-size mediatek,md1md3-smem-size; do
    file="$node/$prop"
    [ -r "$file" ] || continue
    printf '  %s=' "$prop"
    od -An -tx1 -v "$file" | tr -d ' \n'
    printf '\n'
  done
done

section ccci-devices
for path in /dev/ccci* /dev/ttyC* /dev/ccmni* /dev/emd* /dev/eemcs*; do
  [ -e "$path" ] || continue
  printf '%s' "${path##*/}"
  [ -c "$path" ] && printf ' type=char'
  [ -b "$path" ] && printf ' type=block'
  printf '\n'
done

section ccci-interrupts
grep -Ei 'ccci|cldma|ccif|ccmni|eemcs|modem|md[0-9]*[_ -]?wdt|md[0-9]*[_ -]?cldma' \
  /proc/interrupts 2>/dev/null || true

section ccci-proc
for path in /proc/ccci* /proc/cldma* /proc/eemcs* /proc/md*; do
  [ -e "$path" ] || continue
  printf '%s\n' "$path"
done

section network-interfaces
awk -F: 'NR > 2 { gsub(/^ +| +$/, "", $1); print $1 }' /proc/net/dev 2>/dev/null \
  | sort

section network-state
for iface in /sys/class/net/ccmni* /sys/class/net/cc3mni*; do
  [ -d "$iface" ] || continue
  name=${iface##*/}
  printf 'iface=%s' "$name"
  for attr in operstate carrier mtu; do
    [ -r "$iface/$attr" ] || continue
    value=$(cat "$iface/$attr" 2>/dev/null || true)
    [ -n "$value" ] && printf ' %s=%s' "$attr" "$value"
  done
  printf '\n'
done

section modem-processes
ps -eo comm= 2>/dev/null \
  | awk 'tolower($0) ~ /ccci|cldma|eemcs|ccmni|modem|ril|emd/ { print }' \
  | sort -u || true
