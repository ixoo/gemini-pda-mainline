# Experiment: retain every otherwise-unused clock during early boot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-17-clk-ignore-unused-diagnostic` |
| Candidate | J |
| Status | Kernel payload and boot image independently reproduced; installed to `boot2` with full readback; first attended attempt reported `4/60`, strongly attributed to shared `/init` tick 04 before black; repeat pending |
| Subsystem | Common Clock Framework, LK display handoff, simplefb/fbcon |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date | 2026-07-17 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question and current evidence boundary

Candidate I was installed with a matching full-partition readback, but the
reported intended `boot2` selection went directly to black and never displayed
its marker or counter. That does not establish that Candidate I reached
external `/init`; its active-refresh-versus-static-hold hypothesis remains
untested.

Candidate J asks a deliberately broad earlier discriminator: does preventing
normal unused-clock cleanup make the retained LK framebuffer and fbcon output
visible on an otherwise exact Candidate I boot? A positive result would support
an undeclared clock dependency somewhere in early handoff, but would not
identify the correct clock, provider, consumer or Device Tree contract.
`clk_ignore_unused` is a diagnostic, not a proposed default.

The first owner-attended intended `boot2` attempt displayed console output, and
the last visible suffix reported before the screen went black was `4/60`. The
shared I/J `/init` is the only tracked source of that counter and emits
`GEMINI_FBCON_REFRESH_20260716_I T+04 ACTIVE REFRESH 04/60`. Combined with the
verified J write/readback and intended slot selection, this strongly attributes
the visible output to J reaching the shared `/init` through tick 04. The owner
did not report an exact full-line transcription or exact marker recognition.
This is one positive attempt, not a repeatability or causal result.

## Why an Android-header-only candidate is invalid

The retained LK source appends the Android boot-image header command line to
its final command line and then overwrites `/chosen/bootargs`. That mutation
order is recorded in the [current LK console mutation result](../2026-07-13-uart-console-recovery/results/lk-console-mutation-current-77-20260714.txt)
and its [source audit](../2026-07-13-uart-console-recovery/scripts/audit-lk-console-mutation.sh).
The post-LK presence of any particular header token still requires runtime
evidence.

More importantly for the current kernel, exact Candidate I has
`CONFIG_CMDLINE_FORCE=y`. Linux replaces the loader-provided chosen bootargs
with compiled `CONFIG_CMDLINE` in `drivers/of/fdt.c`; it does not merge in the
header-only addition. An early draft changed only Android-header offsets and
produced SHA-256
`3b87a4f604ab0519290987feec9fdca139d4959b4caa1dbfee9889c4c90d2b6d`.
Its `Image.gz` was still exact I, so it was a runtime no-op. The corrected
builder and validator explicitly reject that hash; it must never be exported
or installed.

## Corrected controlled delta

The dedicated `usbdiag-clkignore` kernel profile applies the normal handoff and
usbdiag fragments, followed by `configs/gemini-clk-ignore-unused.fragment`.
That final fragment has one configuration request only. The resolved config
diff against the exact Candidate I usbdiag package is exactly one line:

```text
CONFIG_CMDLINE="... g_ether.iSerialNumber=GEMINI_USB_DIAG_20260716_B"
CONFIG_CMDLINE="... g_ether.iSerialNumber=GEMINI_USB_DIAG_20260716_B clk_ignore_unused"
```

The package validator requires:

- identical pinned kernel source, architecture, compiler, linker, patch series
  and every packaged patch;
- exactly one resolved-config line change, with `CONFIG_CMDLINE_FORCE=y`
  retained;
- exact profile fragment provenance and configuration-input hashes;
- a changed `Image` and `Image.gz` with pinned hashes; and
- a byte-identical complete DTB tree, including the Gemini base DTB.

Candidate J then mechanically reconstructs exact Candidate I through its own
builder. It reuses I's final overlay-derived DTB and complete initramfs
byte-for-byte. This preserves the simplefb clocks and geometry semantics of I,
not merely a fresh unmodified package DTB. Candidate J's Android-v0 header name,
header command line, addresses, ramdisk and padding rules remain exact I. The
kernel payload necessarily changes to the `usbdiag-clkignore` `Image.gz`; only
`kernel_size` when required and the canonical payload-derived ID may change in
the header.

The initramfs remains exact Candidate I, so its visible marker remains:

```text
GEMINI_FBCON_REFRESH_20260716_I
```

That line proves execution of the shared I/J initramfs, not Candidate J by
itself. Attribution to J additionally requires a verified J artifact and a
verified target-partition write/readback record.

## Associated code

- `configs/gemini-clk-ignore-unused.fragment` contains the sole profile
  override.
- `scripts/validate-package-delta.py` proves the exact source, patch, config,
  toolchain and DTB package boundary.
- `scripts/validate-boot-delta.py` requires exact-I header cmdline, DTB and
  initramfs while allowing only the newly compiled kernel payload and its
  derived Android-v0 fields.
- `scripts/test-validator-mutations.sh` runs positive gates, mutates a temporary
  package config and Android header, reconstructs the rejected header-only
  no-op, and requires the two validators to reject every negative case.
- `scripts/build-clk-ignore-unused-candidate.sh` reconstructs exact I, invokes
  every package/container/LK gate, rejects the invalid header-only artifact and
  emits a checksum manifest.

The usbdiag baseline builder uses
`validate-usbdiag-manifest.py` to compare the manifest schema, kernel,
architecture, patch-series path and exact usbdiag profile. This permits an
unrelated new profile without weakening its existing exact series, patch,
fragment, resolved-config and package-provenance gates. Its focused regression
test is `test-validate-usbdiag-manifest.sh`.

All tools are file-only. They have no device, partition, flashing or
hardware-write interface.

## Build procedure

The profile has no convenience shortcut. Build it explicitly in the ARM64 VM:

```sh
KERNEL_PROFILE=usbdiag-clkignore ./scripts/dev-vm build-kernel
```

Equivalently:

```sh
./scripts/dev-vm run env KERNEL_PROFILE=usbdiag-clkignore ./scripts/kernel build
```

Like its usbdiag parent, this is a built-in-only profile. `BUILD_MODULES=1` is
rejected by `scripts/kernel`.

Build the non-flashing boot candidate from both explicit packages:

```sh
experiments/2026-07-17-clk-ignore-unused-diagnostic/scripts/\
build-clk-ignore-unused-candidate.sh \
  --baseline-package ~/artifacts/gemini-pda/\
linux-7.1.3-gemini-usbdiag-3d92a7e9-fdf1d345 \
  --package ~/artifacts/gemini-pda/\
linux-7.1.3-gemini-usbdiag-clkignore-3d92a7e9-d1224166 \
  --output ~/artifacts/boot-candidates/gemini-clk-ignore-unused-J-compiled-final1
```

After one exploratory serialization pins the corrected boot-image hash, build
into two fresh directories, verify both checksum manifests, and require
recursive byte equality. A successful build does not authorize or perform a
device write.

The checked-in mutation regression was run in the VM against the exact package
and boot-container inputs:

```sh
./scripts/dev-vm run \
  experiments/2026-07-17-clk-ignore-unused-diagnostic/scripts/\
test-validator-mutations.sh \
  --baseline-package /home/julien.guest/artifacts/gemini-pda/\
linux-7.1.3-gemini-usbdiag-3d92a7e9-fdf1d345 \
  --package /home/julien.guest/artifacts/gemini-pda/\
linux-7.1.3-gemini-usbdiag-clkignore-3d92a7e9-d1224166 \
  --baseline-candidate /home/julien.guest/artifacts/boot-candidates/\
gemini-fbcon-refresh-I-final1 \
  --candidate /home/julien.guest/artifacts/boot-candidates/\
gemini-clk-ignore-unused-J-compiled-final1
```

It passed both positive gates and rejected a temporary resolved-config
mutation, an Android-header command-line mutation and a reconstructed copy of
the known header-only no-op. The script confines mutations to a temporary
directory and has no hardware-write interface.

## Safety

Building Candidate J does not touch hardware. The separate standing-authorized
`boot2` write is recorded in
[`results/boot2-write-candidate-j-20260717.txt`](results/boot2-write-candidate-j-20260717.txt).
It was synced, flushed and verified by a complete matching readback; it did not
reboot or shut down the device. Runtime selection remains a separate operation.

At runtime, `clk_ignore_unused` retains every clock that the Common Clock
Framework would otherwise classify as unused. This can increase power use and
heat, preserve unintended device activity and make any positive result
non-specific. A test must be owner-attended, brief, performed with stable power
and an independently recoverable boot path, and stopped immediately for heat,
charging anomalies, instability or changed recovery behavior. Do not leave J
running unattended or adopt the option as a normal default.

## Bounded runtime procedure

The first owner-attended Candidate J selection is now complete. It produced the
reported `4/60` suffix from the distinctive `NN/60` counter and then black,
strongly supporting shared `/init` execution through tick 04 for that
attempt. Tick 04 proves that at least four one-second sleeps completed after
the refresh loop began; it does not measure time from slot selection or provide
an upper bound on loop progress before visibility was lost. The
[exact-tree source audit](results/post-attempt-1-source-audit-20260717.md)
rejects several tempting no-op follow-ups. The next action is one more J
selection after returning to the known-good OS and allowing the unit to reach
normal temperature and power conditions. Stop after that attempt and reassess;
do not build or install a new candidate, perform an exact-I rollback, or add a
third J attempt automatically. No boot or partition write is implicit in the
build.

1. Confirm the device can still enter its known-good OS and recovery path. Use
   stable external power and begin only with the unit at normal temperature and
   with no charging, battery, filesystem or recovery anomaly. Expected result:
   the known-good path works before any development-slot change.
2. Under the repository's logical-`boot2` safety policy, resolve the live GPT
   label, preserve the full old partition, write only the exact padded J image,
   sync and flush it, and require a matching full-partition readback. Record the
   padded SHA-256. Do not reboot automatically. Expected result: the installed
   checksum identifies J; any mismatch ends the experiment before boot.
3. Have the owner select `boot2` once and observe for 90 seconds from selection.
   Record whether the shared `GEMINI_FBCON_REFRESH_20260716_I` marker appears,
   first and last readable `T+NN`, transition time, screen orientation,
   backlight state, apparent final power state, heat, and recovery action.
   Because the initramfs is shared, attribute a visible marker to J only in
   combination with the verified J write/readback and intended `boot2`
   selection. No marker is an unconfirmed selection or early-handoff result,
   not a post-`/init` J failure. Attempt 1 completed with the last visible suffix
   reported as `4/60`, followed by black. This is strongly attributable to the
   shared `/init` tick 04 even though the full line and marker were not exactly
   transcribed.
4. Return to the known-good OS after the attempt. Stop immediately and perform
   no repetition after unexpected heat, a charging anomaly, instability,
   watchdog looping, filesystem symptoms, or changed recovery behavior.
   Otherwise wait until power and temperature are normal before another
   owner-attended selection.
5. After returning to the known-good OS and confirming normal temperature and
   power conditions, repeat step 3 exactly once for Candidate J. Stop after
   this second attempt and record it, whether its outcome agrees or disagrees.
   Do not build or install a new candidate yet. If an anomaly occurred during
   attempt 1 or recovery, do not repeat.
6. Only after the second J result has been recorded and reviewed, and only if
   both J attempts are attributable and show a consistent display outcome that
   justifies a matched control, request fresh explicit owner authorization before
   reinstalling the older Candidate I image. The standing `boot2` opt-in covers
   only the latest validated candidate and therefore does not authorize this
   rollback control. After authorization, install exact I to the same logical
   `boot2` with the same live target, power, mount, holder, backup, size, sync,
   flush and full-readback checks. Perform exactly two owner-attended I
   selections under the same 90-second observation and safety conditions. This
   optional matched control is needed before describing J as different from I;
   do not reuse the earlier single unconfirmed direct-black I observation as
   that control.
7. Finish in the known-good OS and record every attempt, including negative and
   unconfirmed results. Expected outcomes are: marker-confirmed visible output,
   marker-confirmed transition to black, or no-marker/unconfirmed handoff. None
   alone identifies a particular clock.

## Interpretation

- If both attributable J attempts show visible output while both matched
  exact-I attempts remain directly black, broad unused-clock retention changes
  the early display outcome. Follow with narrow provider/clock tests; do not
  retain the broad option as a fix.
- If attributed J also goes directly black, this control did not recover
  visible output. It does not prove kernel non-entry or rule out boot selection,
  LK handoff, framebuffer state, power-domain, reset or other clock problems.
- If the shared I marker appears, I's counter/static-hold behavior can be
  observed, but the result is confounded by broad retention and is not an exact
  Candidate I timing result.

## Results

The first owner-attended intended `boot2` selection displayed console text and
then became black. The owner reported `4/60` as the last visible suffix, not an
exact transcription of the complete line or marker. Only the tracked shared I/J
initramfs `/init` emits that counter; at tick 04 its exact source line is
`GEMINI_FBCON_REFRESH_20260716_I T+04 ACTIVE REFRESH 04/60`. Together with the
verified Candidate J write/readback and intended `boot2` selection, this is
strong evidence that J entered Linux, produced fbcon/tty0 output, and executed
the shared `/init` through tick 04. It proves that at least four one-second
sleeps completed after `/init`'s refresh loop began; selection-to-black time
and any upper bound on loop progress before visibility was lost remain unknown.
Backlight state, orientation, first visible tick, selection-to-black time,
final power/runtime state, heat, recovery action, reboot behavior, and
repeatability were not reported.

This single positive attempt is materially associated with broad unused-clock
retention, but causality is not established: the earlier exact-I attempt did
not establish selection or `/init` and is not a matched control. No particular
clock, regulator, power domain, or native display path is identified. The
sanitized observation is in
[`results/runtime-candidate-j-attempt-1-20260717.txt`](results/runtime-candidate-j-attempt-1-20260717.txt).
The exact Candidate J source/configuration audit and the resulting second-test
gate are in
[`results/post-attempt-1-source-audit-20260717.md`](results/post-attempt-1-source-audit-20260717.md).

Two isolated `usbdiag-clkignore` kernel builds passed the normal kernel
artifact validator and independently reproduced `Image`, `Image.gz`,
`System.map`, `kernel.config`, all 119 DTBs and the copied provenance inputs
byte-for-byte. The complete package directories are not byte-identical:
`provenance/build.json` differs only in `generated_utc`
(`2026-07-17T10:45:09Z` versus `2026-07-17T11:07:51Z`), which also changes the
derived `SHA256SUMS`. A Candidate J boot container built from the independent
package is byte-identical to the pinned final image. Separately, one exploratory
boot-container build established the corrected hash and two fresh final builds
from the first pinned package are recursively byte-identical with passing
checksum manifests.

```text
candidate package:       linux-7.1.3-gemini-usbdiag-clkignore-3d92a7e9-d1224166
resolved config:         283570babf78d9299948a35c8133dfa906b04a0c35a2d0d2997309326d607f0d
Candidate J Image.gz:    5,484,175 bytes; fb86a201a4427e71368ea14532213ae4cad104452f28448206fca928d255e318
Candidate J System.map:  0c605affbbde57112af5fac9823a046ded34e00d86886da37b1f99fbf7ce61af
Candidate J boot image:  6,520,832 bytes; 6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4
Candidate I DTB:         25,828 bytes; 2054f0affec1ed5edff6b6a7de2a5d97102145c35fd335b4c0fd834571918a34
Candidate I initramfs:   1,006,187 bytes; 85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85
kernel payload rebuild:  PASS — isolated build and artifact roots
whole package equality:  NO — generated timestamp and derived manifest only
rebuild-derived boot:    PASS — byte-identical; same SHA-256
boot-container equality: PASS — two builds from the same pinned packages
LK/container gates:     PASS
boot2 write/readback:    PASS — 16,777,216-byte full image
runtime attempt 1:       OBSERVED — reported 4/60 suffix strongly attributed to shared /init tick 04, then black
```

The sanitized record is
`results/candidate-j-build-20260717.txt`. The exact exported final directory is
under the Git-ignored
`artifacts/vm-export/boot-candidates/gemini-clk-ignore-unused-J-compiled-final1/`
path; every exported file is mode `0600` and its manifest rechecks on the host.
The three misleading VM directories produced by the rejected header-only draft
were moved out of the normal candidate namespace and into a clearly named
`rejected-header-only-noop-20260717/` quarantine. Candidate J was installed
only to logical `boot2`; the write, sync, flush and complete readback are
captured in the linked write record above. The write itself left the device in
its known-good Gemian kernel with root on `mmcblk0p29` and did not reboot or
shut it down. The later first owner-attended Candidate J selection is recorded
separately in the linked runtime result.
