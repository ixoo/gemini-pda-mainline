#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Capture bounded touchscreen identity/log lines from the running vendor
# kernel. This is read-only: it does not open /proc/NVTflash, access I2C,
# unbind the driver, request firmware, or change device state.

set -euo pipefail
export LC_ALL=C

printf '%s\n' 'validation=nvt-live-trim-log-capture'
printf 'kernel='; uname -r
printf 'capture_scope=filtered_dmesg_only\n'
printf 'hardware_write=none\n'
printf '\n[identity_and_probe]\n'
dmesg | grep -Ei \
  'nvt_ts_check_chip_ver_trim|nvt_read_pid|nvt_ts_probe.*(IC FW|request irq|end)|nvt_irq_registration|nvt_local_init|tpd_driver_name' \
  || true
printf '\n[power_and_firmware]\n'
dmesg | grep -Ei \
  'update_firmware_request|Direct firmware load for novatek_ts_fw\.bin|Falling back to user helper|Check_CheckSum|nvt_ts_(suspend|resume)|LCD (ON|OFF) Notify' \
  | tail -n 80 || true
printf '\n[safety]\n'
printf 'proc_nvtflash_read=none\n'
printf 'i2c_transactions=none\n'
printf 'driver_unbind=none\n'
printf 'firmware_request=none\n'
