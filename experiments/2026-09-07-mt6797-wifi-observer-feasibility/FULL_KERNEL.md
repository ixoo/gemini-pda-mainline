# Complete native controller kernel link

The [Buildbox-only builder](build-full-kernel.py) compiles the complete native
kernel from [forty-seven pinned patches](full-kernel-inputs.json): the previously
compiled controller composition, the emergency reset correction, and historical
patch 0001's A72 refusal/configuration declaration, plus the detector's watchdog
header dependency, the [calibration open-error correction](CALIBRATION_OPEN.md)
and [native recovery-reset isolation](RESET_ISOLATION.md), followed by the
[restart-wrapper correction](patches/restart-wrapper/0001-watchdog-bypass-RTC-mode-writes-in-captured-experiment.patch)
and [earlier restart exclusion](RESTART_GATE.md), then the
[raw PMSG reader correction](CAPTURE_DEVICE.md#raw-reader-correction), and the
[native HPS startup policy](HPS_BOOT_POLICY.md).
It does not select the old
recovery trigger, profile or consumed artifact.

Run from the clean, pushed project checkout:

```sh
GEMINI_BUILD_EXPERIMENT=wifi-controller KERNEL_JOBS=8 ./scripts/build-kernel --backend buildbox
```

The explicit experiment selector uses the existing Buildbox clean-push check,
mirror fetch, exact checkout and shared build lock before calling this builder.
It accepts no manifest profile, module build or VM backend. It defaults to eight
jobs; the native builder permits one through sixteen. This is a separate native
experiment, not a new upstream kernel profile. The
builder uses the existing pinned Gemian source and GCC 6.3 toolchain. It reuses
a prepared source tree keyed by the complete input manifest, verifies that tree
with the repository's existing integrity tool, and builds in a separate
managed temporary output. The generated DCT input must match the existing
normalized checksum. Configuration permits only the experimental symbol and
the established disabled-ANBOX serialization change. Build identity fields are
fixed; two-build reproducibility has not been established.

The link must contain the capture, recovery and request entry points, contain
no historical delayed recovery callback, and have no unresolved symbols.
Outputs include the linked kernel, symbol map, configuration, logs and checksum
manifest. No Android boot container or minimal filesystem is constructed.
The retained configuration still contains unrelated vendor drivers; a successful
link does not establish their exclusion or authorize running this kernel.

This is an integration check toward a recoverable observation candidate.
Filesystem construction, complete reset/resource isolation, capture preparation,
independent reproduction, container validation and an approved device session
remain separate requirements. Firmware files remain private and are not inputs
to this compile-only package.

The first attempt stopped before compilation because the linker identity check
lacked the pinned library environment. After that correction, full compilation
exposed a missing `ext_wd_drv.h` include path in the detector's native Makefile.
The retained [failure identity and correction](results/controller-build-sources.json)
record that error; isolated object checks had supplied this path explicitly.
The correction adds a configuration-dependent include path to the native rule.
Failed compilation now retains complete logs with a checksum manifest.

The [complete link receipt](results/full-kernel-link.json) records success at
`d19a9c4947614d51363085f6c47a4c7b51ec3964`. All eleven fetched package files
match the remotely validated inventory and checksum manifest. The full source
tree retained its integrity digest through compilation, all required entry
points are linked, and the linked kernel has no unresolved symbols.
That receipt covers the original 41-patch input manifest. The
[44-patch link receipt](results/full-kernel-link-44.json) records the complete
updated build from `e025cf58bf3fc6745222b1d72039f785ad1ff5de`, including the
calibration, reset-isolation and restart-wrapper corrections. All eleven package
files passed remote inventory/checksum validation and local verification after
fetch. Source integrity remained unchanged, the required entry points are linked,
and no undefined symbols remain.

The [45-patch link receipt](results/full-kernel-link-45.json) records the complete
restart-gate composition at `aa2c51767d0fab9ebbc187b6b355f30931e8c4d4`.
All eleven package files passed remote and fetched checksum verification;
source integrity, required symbols and absence of undefined symbols passed.
The [linked restart inspection](RESTART_GATE.md) confirms the shared atomic
claim precedes the inspected restart effects and remains inside IRQ exclusion
during timer arming. The private startup assembly still binds the earlier
44-patch package; no updated session or boot container is selected here.

The RTC wrapper patch routes experimental `arch_reset()` directly to the existing
`wdt_arch_reset(1)` before RTC recovery/fastboot/charging-mode writes. The
low-level owner parks after takeover and retains its normal reset path before
takeover. This avoids introducing a new lock across potentially sleeping RTC
operations. Ordinary builds retain their original wrapper. In the final linked
ARM64 kernel, `arch_reset` is 24 bytes in `.text`: its only call is
`wdt_arch_reset` with argument one, followed by return. It contains no RTC call
or indirect watchdog-API dispatch. This establishes the wrapper's compiled
control flow, not complete isolation of restart notifiers or other kernel actors.

Modpost reports 69 section mismatches. The retained observer package reports
the same count, but mismatch identities have not been compared. Native compiler
commands retain `-w`; this is not warning-clean evidence. The controller and
recovery entries and the inspected wrapper symbols reside in `.text`, which
does not establish the lifetime of every downstream callback or data object.
This result closes the complete-link check for these inputs, not device admission.

The [46-patch link](results/full-kernel-link-46.json) passes from
`c9a8d30423da33a7fae8c95f2c0d9b5f96b90ee7`, adding the raw-reader correction.
All eleven package files passed remote and fetched checksum verification;
configuration, required symbols, absence of undefined symbols and source
integrity passed. The final reader's capture-PMSG branch bypasses both text
parser calls and stores zero timestamp and compression metadata. Its frame is
112 bytes and its code is 648 bytes. The same 69 section-mismatch count and
compiler warning limitation remain. This package is bound by the
[third private filesystem assembly](STARTUP_ASSEMBLY.md#export-filesystem); no
boot container or physical session is selected.

The [47-patch HPS startup correction](HPS_BOOT_POLICY.md#validated-build-and-selected-session)
passes the complete Buildbox link, fetched checksum inventory and linked-code
comparison. Its receipt and separately selected export-return candidate are
owned by that experiment record; device execution remains outstanding there.
