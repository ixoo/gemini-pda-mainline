# USB role decision after the second export session

The two [read-status physical results](USB_CHRDET_ERRORS.md) used the same
51-patch kernel. The first recorded a successful nonzero CHRDET read, a device
branch and controller start. The second recorded a successful zero read, a host
branch, no cable sample and no controller start. Both returned to authenticated
Gemian and preserved one console. Neither result joins the charger sample to a
particular role check or identifies the physical state of the left port.

## Selected source and linked path

The selected kernel package is the [validated build](results/usb-chrdet-errors-build.json)
at commit `0c02543ad35cb22fd8281ee5400aac0c01504c3d`, using prepared inputs
`f1933271c1010008f17e61e6ca4524e627792247f69e9fbeaf5db6585b47315a`.
The prepared `drivers/misc/mediatek/mu3d/drv/mt_usb.c` is SHA-256
`397bcde2601dd4b72a1921e809352bac089caade8e0df1a8f5dbb216de868268`;
`drivers/misc/mediatek/xhci/xhci-mtk-driver.c` is
`f58a440ee6569f70f3986025670d81fbe861c7da2c6b4f5c306bc6f32c83c090`.
These are private prepared-source identities, not newly published vendor source.

`connection_work()` records ready, then calls `mt_usb_is_device()` before
`usb_cable_connected()`. With the selected `CONFIG_USB_XHCI_MTK=y`, the former
inverts `mtk_is_host_mode()`. On a host result, it records the host bit, powers
the device side down and returns without making the ordinary cable sample.
Thus `cable=ffffffff` in the second boot is the expected consequence of that
early return. It is not a sampled cable-false result. The charger and PMIC
masks cover other callers as well and cannot establish that the successful-zero
read preceded or caused the role decision.

The selected configuration has `CONFIG_USB_MU3D_DRV=y`,
`CONFIG_USB_MTK_DUALMODE=y`, `CONFIG_USB_C_SWITCH=y` and
`CONFIG_USB_XHCI_MTK=y`; `CONFIG_USB_MTK_OTG_SWITCH` and
`CONFIG_MTK_OTG_PMIC_BOOST_5V` are off. In the exact linked `vmlinux`, the
`mtk_is_host_mode()` body at `ffffffc0004edb90` loads one state word, compares
it with `IDPIN_IN_HOST` (value 1), returns that equality and makes no call.
The source also mentions `vbus_on`, but the selected binary has folded that
unused boost path away. This establishes that the host branch observed the
internal ID-pin state, not the CHRDET getter's return value.

The selected source has two possible writers of `IDPIN_IN_HOST`: the delayed
ID-pin mode switch selects host when its charger-voltage classification does
not exceed 4000 mV, and the Type-C host-enable callback writes host directly.
The linked image contains both `mtk_xhci_mode_switch` and `typec_otg_enable`.
An exported `mtk_set_host_mode_in_host()` also writes that state; no direct
caller was found in the selected prepared Mediatek source. Source and symbol
presence do not prove which writer ran in the second boot. The retained console
does not provide an attributable writer event; its checked post-return segment
contains no role-transition witness.

## Next discriminator

The next candidate must distinguish the ID-pin work path from the Type-C
callback at the point each writes the software host state, while retaining the
existing early-return and export behavior. A small cumulative software marker
reported through the existing one-shot shutdown line can answer which paths
ran without a new PMIC read, role action or capture clear. Pin the selected
source and linked writer paths, validate the exact added operations and a
bounded return before admitting another physical selection. Mixed markers or
missing output remain inconclusive; neither authorizes forcing device mode.

## Prepared software discriminator

The [experiment patch](patches/usb-role-writers/0001-usb-retain-host-state-writer-paths.patch)
adds a seven-bit cumulative `role` field to the existing one-shot report:

| Bit | Existing software-state write observed |
| --- | --- |
| 0 | ID-pin work selected host |
| 1 | ID-pin work selected device |
| 2 | ID-pin work returned to out |
| 3 | Type-C host-enable callback selected host |
| 4 | Type-C host-disable callback selected out |
| 5 | Exported host setter selected host |
| 6 | Exported out setter selected out |

The report becomes `wifi-usb-v4 paths=hhhh cable=hhhhhhhh chrdet=hhhh pmic=hh role=hh`.
Markers use the existing diagnostic configuration gate, add no hardware read,
role request, scheduling action, retry or new reporting site, and leave every
original assignment and return in place. The mask records whether each path
ran at least once, not its order, count or value at the earlier role check.
Only an unambiguous host-writer subset can identify a unique path; mixed bits
remain inconclusive. A missing summary is also inconclusive because the
original report guard can be consumed before the diagnostic.

The [source receipt](results/usb-role-writers.json) pins both selected parent
files, exact reversal and replay, and strict Checkpatch with zero findings.
This assistant-generated, non-certifying native experiment is not an upstream
submission. The first 51 patches and selected configuration are unchanged.
The [Buildbox receipt](results/usb-role-writers-build.json) records a complete
link with zero undefined symbols. Its package passed the full checksum
inventory; the selected configuration and appended device tree are byte-identical
to the preceding kernel. Linked inspection found a load-only role getter, all
seven writer marks after their software-state assignments, and the original
one-shot report guard before its getters. The inherited native build still
uses `-w` and reports 69 section mismatches. The
[offline candidate receipt](results/usb-role-writers-candidate.json) pins the
52-patch kernel, unchanged startup runtime, distinct cycle and exact 16 MiB
image. Filesystem and container checks passed, including byte-identical
reassembly and device-tree reservation checks. Installation and a new physical
measurement remain separate gates.
