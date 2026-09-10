# Recorded controller initialization

The unselected [patch](patches/controller-init/0001-wmt-initialize-after-recorded-recovery-takeover.patch)
connects the [capture/recovery backend](RECOVERY_GATE.md) to the existing native
connectivity initialization chain. This implements the initialization part of
the controller; it does not yet run the responder or WLAN ON/OFF sequence.
No kernel profile selects it and no device request was issued.

## Experimental entry

With the compile-only recovery symbol enabled, `/dev/wmtdetect` accepts only
`COMBO_IOCTL_CAPTURE_INIT`, `_IOW('w', 9, struct wmt_capture_identity)`.
The reviewed ARM64 encoding is `0x40607709`. The argument is a pointer to exactly
96 bytes: cycle identity (16), then the existing candidate/boot/input identity
(80). This new request uses pointer-copy semantics; the historical scalar
initialization ioctl is refused along with every other detector ioctl in this
experimental build. The compatibility handler refuses all 32-bit requests.
Without the experiment symbol the existing detector behavior is preserved.
This is a disposable experiment interface, not a proposed upstream ABI.

The handler requires `CAP_SYS_ADMIN`, copies the complete input before any
effect, requires the built-in/Wi-Fi configuration, then invokes the one-shot
capture/recovery backend. Any refusal returns before setting chip state or
calling an initializer. Success records initialization entry, sets the software
chip cache to the fixed MT6797 identity `0x6797`, and enters the native chain.
There is no arbitrary chip argument. Candidate/configuration/firmware validation
and minimal userspace isolation remain the controller packager's prerequisites;
capability and supplied identity bytes do not authenticate those inputs.

The backend's twelve-second deadline remains armed throughout. Initializer or
recording failure ends initialization, attempts one failed capture terminal,
and returns an error. A positive native failure becomes `-EIO` at the ioctl
boundary while its original value is preserved in the record. There is no
retry, teardown, watchdog restoration or reboot call. Duplicate requests are
refused by the backend before initialization. Closing the descriptor is not
resource cleanup.

## Native return values and records

The three existing wrappers retain their native calls and order. Under capture,
they now stop at the first nonzero initializer result or record-write failure.
This prevents arithmetic cancellation of errors and avoids running later
components after a failure. The disabled-capture inline helpers return zero,
preserving the original aggregation outside this experiment. A weak missing-WLAN
implementation returns unsupported in the experiment instead of success; the
WLAN wrapper also refuses a missing Wi-Fi/gen3 selection.

Kind 12, transaction zero, contains three little-endian 32-bit fields: site,
stage (1 entry, 2 return), and signed native result. Entry results are zero.

| Site | Native boundary |
| --- | --- |
| 0 | Controller initialization, including software chip-cache assignment |
| 1–6 | Common, Bluetooth, GPS, FM, WLAN and ANT wrappers, in that order |
| 11–14 | HIF-SDIO, common core, STP-UART and STP-SDIO initialization |
| 21–22 | WLAN character interface and gen3 initialization |

The successful sequence contains 26 records (3328 bytes), nested within the
controller and common/WLAN wrapper boundaries. These follow the identity and
two recovery records. `check_startup_prefix()` in the [decoder](capture-records.py)
requires that exact prefix with every native result zero and no intervening
activity, missing/repeated record or later initializer record. It calls the
recovery-prefix check first. This checks the named returns, not deeper internal
error handling, callback quiescence, firmware loading or whole-cycle completion.
The original Bluetooth/GPS/FM registrations remain; excluding their userspace
consumers is still necessary and does not prove absence of initializer effects.

## Verification and remaining work

The [source receipt](results/controller-init-sources.json) pins the full edited
parents and outputs at Gemian revision `59e00a9144d782e148332009a835b99c43382467`.
The patch follows the capture/recovery patch and its prerequisites. Its archive
author is synthetic and supplies no DCO certification.

The [fixture](test-controller-init.py) executes the complete native controller,
ioctl handler and three wrappers with injected leaf initializers, capture and
recovery. It checks the successful order, 20 positive/negative initializer
failures, all 26 lost records, four preflight refusals and duplicate refusal.
Actual emitted record bytes pass the decoder; 52 missing/repeated-record
mutations are rejected. This fixture specifies the Linux ioctl packing on the
host; it does not use the host OS's potentially different ioctl encoding.
Strict Checkpatch and the existing capture tests pass. The
[native compilation receipt](results/controller-init-object-compile.json) records
ten successful complete-object compilations and the same fixture on Buildbox
at `6cc40eb8bd31f32b24d2acae9cb0b5a97d50a10b`, using
`check-recovery-setters.py COMMIT --controller`. It verifies the selected
built-in/Wi-Fi/gen3 macros and changed header dependencies. The detector object
references the capture/recovery backend only in the child. All 45 returned files
match the remote inventory and 44-entry checksum manifest, SHA-256
`f4f4d975f7b478dfff4575f5a50a706a6015f2fbcba1b74a4f138f1dde7201a2`.
The native compiler commands retain `-w`; these are not warning-clean or
complete-kernel-link results.

Complete kernel linking, minimal filesystem packaging, reset/resource isolation
and the exact owner-approved device session remain open. This source checkpoint
neither installs a candidate nor claims runtime support.

The [transport setup prerequisites](TRANSPORT_SETUP.md) repair false success,
wait for configuration completion and exclude display-triggered power work.

The [single-cycle controller](CONTROLLER_CYCLE.md) now connects that sequence,
joins the responder process and records producer completion. Candidate packaging,
full linking and the device session remain outstanding.
