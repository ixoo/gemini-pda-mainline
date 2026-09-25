# Observe the native ID-pin role input

The [CMDQ-gated boot-only result](results/cmdq-gate-boot-window-2.json)
reached userspace and returned normally, but its retained USB summary reported
`role=01` (`id_host`) and a host connection path. The selected ID-pin work
chooses that state when its existing `battery_meter_get_charger_voltage()`
result is at most 4000 mV. The prior image did not retain the result, and its
debug print did not appear in the retained console. Charger detection and
PMIC masks in the one-shot summary are independent of this role decision.

The [experiment patch](patches/usb-id-voltage/0001-usb-retain-ID-pin-role-voltage.patch)
stores the value returned by the existing getter at the existing ID-pin
decision and appends it as signed `id_mv` to the existing one-shot USB shutdown
summary (`wifi-usb-v5`). `INT_MIN` means that no sample was stored. The value
is the latest such sample, so multiple ID-pin decisions cannot be counted or
ordered from this field. The patch is selected only after the 57-patch CMDQ
gate; it adds no ADC read, role request, controller start, retry or new report
site. Ordinary builds do not retain the value. This is a native diagnostic,
not an upstream submission or a radio action.

The [58-patch Buildbox result](results/usb-id-voltage-build.json) linked with
zero undefined symbols and the inherited 69 section mismatches. Its exact
10-file package passed checksums remotely and after fetch. The selected
configuration is unchanged from the 57-patch kernel. Linked inspection found
one `wifi-usb-v5` format and no `v4` format; the mode-switch body stores the
existing charger getter result before comparing it with 4001 mV, and the
one-shot report calls the retained-value getter. Compilation does not establish
runtime USB behavior. Strict Checkpatch passed with the native source's
existing cross-file declaration pattern excluded.

The next physical boot is justified only by this new measurement. Its
hypothesis is that the observed `id_host` path follows the existing voltage
threshold. An attributable `role=01` with `id_mv` at most 4000 supports that
software branch, while `INT_MIN`, mixed role bits or a conflicting value leaves
the decision unresolved. A device branch and a complete authenticated USB
export would also test transport serviceability, but no snapshot or gadget
appearance is assumed. The returned value alone does not establish actual
port power, ADC health, cable state or why the getter produced it. Do not force
device mode or change charger detection based on this diagnostic.

Before that boot, require an exact 58-patch Buildbox link, checked image and
boot-only package, guarded inactive `boot2` installation with full readback,
clean Gemian shutdown, and collectors armed before owner selection. The
one-shot retained console and changed-boot Gemian return remain the fallback
when USB export does not appear. GCE hardware-idle and the separate Wi-Fi
resource admissions remain open.
