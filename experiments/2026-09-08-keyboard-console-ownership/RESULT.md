# Console-ownership observation result

The single attended test on 2026-09-09 passed the console-ownership observation.
The owner reported boot2 started and confirmed a readable status screen. The
exact [installed candidate](DEPLOYMENT.md) authenticated on mainline boot
`edfffb14-344f-483e-8e4c-cf38303c31c2`.

The baseline matched the kernel configuration and initramfs identities, kept
CPU0–7 online and CPUs8–9 offline, and passed console/map checks. The separate
metadata query identified PID 1 descriptors 0, 1 and 2 as character device
`1:3` (`/dev/null`). Its complete final marker, unchanged boot, zero exit and
empty stderr passed within 0.382 seconds. This demonstrates the intended
stdio change while the explicit status screen remains readable; it does not
establish an empty global reader scan or keyboard coverage.

The two negative authentication probes and fresh positive probe passed.
The complete logger export contains 121,081 bytes and 1,746 records, from
sequence zero through the explicit seal. Logger termination preceded export;
all available files were preserved without truncation. The exact evidence
identities and phase manifests are in [session-result.json](session-result.json).
Raw streams, commands and credentials remain private.

## Recovery and its limit

The one native recovery request produced its complete request frame and restart
announcement with empty stderr, but its SSH process reached the outer timeout
at 14.085 seconds. That request remains **inconclusive** and was not retried.
The owner reported Gemian back; the single authenticated confirmation then
established changed-ID Gemian boot
`e0389001-dc2c-428d-a965-c6cb1f3415a8`.

The unchanged aggregate retains `recovered-with-baseline-incomplete` because
orderly SSH disconnect was not proven. The existing supplemental verifier
independently reparsed the complete baseline, authentication, log, exact timeout
witness and confirmation archive and returned
`supplemental-authenticated-baseline-recovery-verified`. The disconnect runner's
existing `reviewed-supplemental` dependency path also accepted those exact pins.
Neither check upgrades the original request or enables a device action.

## Local refusal and next boundary

Before the baseline connection, the collector refused a mode-0755 local parent
directory. No attempt directory or device connection had been created. The
parent was restricted to mode 0700 and the still-unconsumed admission was used.
That host preparation refusal is retained separately from the successful single
hardware observation.

The session is complete, its budgets are consumed, and Gemian is available.
The [prepared disconnect proof](NEXT_SESSION.md) is the next distinct test.
It still requires a fresh owner-selected boot and exact admission; its binding
remains disabled. No disconnect probe, keyboard capture, storage-content read,
thermal sample, CPU admission or radio action occurred in this session.
