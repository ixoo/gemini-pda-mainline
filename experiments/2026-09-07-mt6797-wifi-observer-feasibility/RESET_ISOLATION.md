# Excluding native recovery resets from the captured cycle

The [reset-isolation patch](patches/reset-isolation/0001-wmt-isolate-recovery-reset-paths-in-captured-experiment.patch)
prevents the experimental WMT recovery entry points from resetting shared
resources while the original Wi-Fi worker may still own them. Native
`wmt_lib_cmb_rst()` otherwise disables STP, sends reset notifications, signals
the current operation and tries hardware/software reset up to ten times.
The earlier operation-ownership correction prevents premature operation reuse;
it does not exclude those hardware and protocol effects.

With `CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR`, these paths now use the existing
capture invalidation routine and return failure before the native reset work:

| Entry | Experimental result |
| --- | --- |
| `wmt_lib_cmb_rst` | `WMTRSTRET_FAIL`; no reset notification, signal, retry or subsystem reset |
| `wmt_lib_hw_rst`, `wmt_lib_sw_rst` | False; no state reset, queue manipulation or reset operation submission |
| `wmt_core_trigger_stp_assert` | False; no firmware assertion callback |
| `wmt_lib_btm_cb` with `BTM_RST_OP` | False; no successful acknowledgement of an unperformed reset |

The invalidation helper retains its existing lock and failure-record behavior;
only its name and linkage change so the core unit can call it. A refused reset
does not release the original worker or its resources. The controller must
stop normal requests on failed capture, and the already armed watchdog remains
the terminal recovery mechanism. No watchdog change or new timeout is added.
Before capture is active, invalidation is a no-op, but these experimental
reset entries still return failure without effects.

Normal chip-startup reset operations are unchanged. The source caller search
found hardware/software recovery-reset submissions only in these two library
helpers; their other direct callers are the diagnostic controls. Whole-chip
reset is called from the BTM callback and the diagnostic interface. The core
assert helper is called from BTM and its core error path. This scoped finding
does not exclude all direct CONSYS accesses or unrelated kernel actors.

## Validation and remaining scope

The [native receipt](results/reset-isolation.json) pins the four parent/output
files, patch, compiler inputs and objects. From clean pushed commit
`7958552d8865484eb67c04aa02c4e03d2a2d93f9`, Buildbox compiled both complete
`wmt_lib.c` and `wmt_core.c` units before and after the change. It reused the
verified 41-patch prepared source and prior full-link configuration in separate
temporary output. The intervening calibration patch changes only the separate
WLAN `platform.c`, so these four parent files are unchanged by it.

Removing exactly the new configuration guards and reversing the helper rename
recovers all four parent source files. Native dependency records confirm the
changed public header in both units and changed request header in WMT-library
compilation. The resulting ARM64 reset functions call only the existing capture
activity/invalidation path and return their documented failure values. The
assert helper has no indirect callback, unlike its parent. The compiled BTM
reset branch was reviewed through its false return; its non-reset branches
remain present. This is compiled control-flow evidence, not device execution.

Strict checkpatch passed with the missing-signoff category excluded for the
explicitly synthetic, non-certifying experiment archive. The native commands
inherit `-w`, so this is not warning-clean evidence. Source integrity matched
before and after compilation. All 19 package files passed remote inventory and
checksum validation and checksum verification after fetch.

The patch occupies entry 43 in the [full-kernel inputs](full-kernel-inputs.json)
without changing the preceding entries or canonical upstream profiles. The
[updated complete link](FULL_KERNEL.md) covers all 44 entries, including the
subsequent RTC restart-wrapper correction. The [minimal PID1](BOOT_STARTUP.md)
is implemented and tested separately but is not yet packaged. Remaining restart
notifier effects, shared-resource consumers, capture zero-state preparation,
complete packaging and the owner-approved radio/recovery session remain
prerequisites. No device access occurred here.
