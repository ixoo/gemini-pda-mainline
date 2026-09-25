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

The [physical result](results/usb-id-voltage-runtime.json) resolves that
specific software branch. The exact 58-patch kernel was packaged as a
boot-only image, installed to guarded inactive `boot2` with matching full
readback, and selected physically after a clean Gemian shutdown. Both host
collectors were armed first. One retained console identifies mainline boot
`cb2620d0-4c56-4465-8401-9a877323fc0f`: userspace passed preflight,
entered the snapshot stage, waited for a host request, stopped, and restarted
normally. Authenticated Gemian boot
`a3eb4157-ef96-45d2-a8e0-405b1ef46572` confirms the changed-boot return.
The single `wifi-usb-v5` summary reports `id_mv=28`, `role=01` (`id_host`),
the host connection path, no cable sample, and no device-controller start.
The prearmed host collector saw no export gadget, so no request or snapshot
transfer occurred. No checked fault token followed the return marker.

The existing getter's 28 mV return is below the 4000 mV threshold and thus
supports the observed host choice. In the exact selected source, the fuel-gauge
getter discards the battery-meter control status. The meter's charger read
uses PMIC AUXADC channel 2, scales the returned value by the configured
divider, and reports success; the AUXADC routine can return register data
after a readiness timeout. Thus the 28 mV value does not establish actual
port power or ADC validity. A private scan of the retained console found no
AUXADC timeout line, but the selected source compiles that debug print out;
its absence does not establish a ready conversion. A later read-only
observation in the authenticated returned Gemian boot showed `usb/online=0`,
`ac/online=0`, and battery status
`Not charging`. The owner had reported the left-port cable connected before
this boot. The Gemian reading is from a different boot and is not an
independent physical VBUS measurement. The masks
are cumulative and the value is the latest stored sample, not an ordered
trace. Resolve power at the port and ADC readiness before any role-policy
change; this result does not justify forcing device mode.
There was no radio action or observed CMDQ task submission, and GCE
hardware-idle and the separate Wi-Fi resource admissions remain open.

A later [five-minute read-only Gemian watch](results/usb-power-watch.json)
remained at `usb/online=0`, `ac/online=0` and `Not charging`. The requested
physical charger change was not confirmed within that window, so the watch
does not establish how the device responds to a known-good charger.

A [later bounded Gemian read](results/gemian-charger-voltage-20260925.json)
on the same boot also returned cached `ChargerVoltage=0`, with USB and AC
offline and charging status unchanged. An audit of the pinned Gemian kernel
source found that reading this property returns a previously updated value;
it does not itself start an ADC conversion. The cable's destination was not
confirmed for this read, and the software value is not an independent VBUS
measurement. Port power and ADC readiness remain unresolved.

A [read-only Gemian interface inventory](results/gemian-typec-interface-20260925.json)
found no Type-C, extcon, USB-role or dual-role class, and no status attribute
on the two FUSB301 platform devices. The exposed OTG switch has not been
established as a physical attachment signal. This inspection supplies no
independent port-power evidence; it did not read controller registers or
change device state.

The owner then identified the cable's other end as the Mac. A
[fresh five-minute Gemian watch](results/usb-power-mac-to-charger-watch-20260925.json)
began from that reported connection and collected 83 successful samples on one
boot, all with cached charger voltage zero, USB/AC offline and `Not charging`.
The requested move to a known-good charger was not confirmed within the watch,
so this is still not a charger-response result. Starting from the reported
Mac connection, Gemian reported no power transition in that interval.
