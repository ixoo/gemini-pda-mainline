# A53 service-kernel RAM regression candidate

Status: the first A53 board boot reached CPU0–7 and authenticated USB, and its
complete kernel log was preserved. A separate read-only probe verified return
to changed-boot Gemian. The consumed session runner remains inconclusive at its
return phase; no unchanged-image retry is selected. Current device custody
and the closed session are recorded in the
[queue](../../project/experiment-queue.json).

## Purpose and bounded change

The [service-facilities kernel](A53_SERVICE_FACILITIES.md) passes the
[Debian QEMU runtime](A53_DEBIAN_QEMU.md). Its first board session reused the
accepted authenticated RAM environment and reached CPU0–7, USB and complete
logging, independently of future persistent-root storage selection. This is a step
toward the A53 integration baseline, not a distribution installation or the
ten-cold-boot release gate.

The [composition recipe](build-a53-ram-candidate.py) requires the exact
Buildbox package from `ac6cf1774966ff282449881c5337d9888eab1d5a` and the
[accepted console candidate](../2026-09-08-keyboard-console-ownership/validation.json).
It checks the complete kernel package inventory and all six accepted parent
file hashes. The parent image is identified by its full digest, never its
timestamp or a mutable profile name.

Only `/init` changes within the 47-member RAM archive: its one exact kernel
release check becomes `7.1.3-gemini-a53-service-facilities`. All other member
bytes and metadata remain identical, including private authentication keys,
console ownership, CPU0–7 gates, bounded logging and recovery helpers. The
accepted device tree remains byte-identical; it has no embedded build-identity
property requiring replacement. No storage mount, peripheral activation,
hotplug request or automatic recovery is added to startup.

The recipe uses the existing archive parser/serializer and Android-v0
serializer/analyzer. It checks archive round-trip equality, actual kernel
decompression, logger-sealing syscall linkage, exact LK addresses/format and
16 MiB partition fit. Output is private, contains a secret host key and is
never published. Composition itself has no device access.

From a clean source checkout in the RE VM, provide the accepted parent and
validated kernel package as explicit paths:

```sh
python3 experiments/2026-09-09-standard-kernel-package/build-a53-ram-candidate.py \
  --kernel-package "$A53_KERNEL_PACKAGE" \
  --parent "$A53_ACCEPTED_RAM_CANDIDATE" \
  --output "$A53_NEW_RAM_CANDIDATE"
```

The output parent must exist. An occupied output is refused. The locked managed
stage contains regenerable composition data only; a later invocation removes
an abandoned stage without deleting an existing final candidate.

## Focused validation

The [init test receipt](results/a53-service-ram-init.json) records five cases
using the exact accepted ARM64 BusyBox under QEMU. The existing shell fixture's
effect proxy supplies the chosen kernel release; mount, network, console,
logger and PID1 effects remain injected. The new release launches exactly the
two expected services and init, all with null standard descriptors and
`CONSOLE=/dev/null`. The old release, an unrelated release, a wrong CPU mask and
a failed devtmpfs mount each hold before any service launch. Shell syntax and
the complete archive member/metadata round-trip pass.

The prior authentication and logging results remain evidence for the unchanged
userspace bytes. These five tests do not rerun Dropbear authentication, exercise
real device nodes, test the new kernel's PID1 path or establish board support.

## Complete composition result

The [composition receipt](results/a53-service-ram-candidate.json) records the
image built from clean recipe commit
`4ce5197b3c79139baaae6dc2026c6566336dde5d` in the RE VM. The existing
Buildbox kernel was reused; no kernel compilation or device action occurred.
The complete boot image is 9,129,984 bytes, leaving 7,647,232 bytes in boot2.
Its SHA-256 is
`97c23e3f34686d8831e56f9903e109f6b9ba89cb121c88996f25411e86d5bec0`;
the exact 16 MiB padded image has SHA-256
`f185a0f2f993f8c68227f2a6e225e951ee22487d418610b9156ee1e517f56cb0`.

The LK analyzer accepted the image, paired payloads, header and load addresses.
A separate readback checked all output hashes, the complete file inventory,
private permissions and exact zero padding. Inverting the one release-string
change reproduces the original init member including metadata. All 46 other
members and the device tree compare equal to the accepted parent. The packaged
init hash matches the five-case fixture. Managed staging was removed; the final
private candidate remained in the RE VM at this composition checkpoint.

Local repository checks and the exact source commit's
[hosted Linux checks](https://github.com/ixoo/gemini-pda-mainline/actions/runs/34725518175)
passed. No new kernel/DT source or binding changed, so no additional kernel
build or DT schema run was needed. This is packaging and injected userspace
evidence only; it establishes no new physical support claim.

## Bound observation and recovery scripts

The [offline generator](a53-ram-session.py) checks the exact private candidate
inventory, image hashes and permissions, then reuses the existing observation,
log-sealing and recovery script generators. Its module instances accept the
new release and exact candidate/init/config identities. Historical files and
their closed receipts remain unchanged. The observation classifier additionally
rejects a zero or noncanonical boot UUID after an otherwise passing frame.

The [binding tests](results/a53-service-ram-session-tests.json) establish that
reversing those identity substitutions makes all four generated scripts
byte-identical to their historical counterparts. One valid observation frame
passes; nine altered identity, CPU, framing or transport cases refuse. All
42 exact-ARM64 shell cases pass, covering both sets of 17 identity/RAM/claim
guards and eight additional failed-log cases. Failed logs retain their available
bytes and are never promoted to a complete log. No target signal, restart or
hardware operation is executed by these fixtures.

Six accepted recovery-request framing/transport combinations remain requests
only, requiring later changed-boot Gemian confirmation. Three malformed,
interrupted or returned-helper cases refuse. Shell syntax passes. Full
ShellCheck has zero errors/warnings and 23 informational findings identical
to the original scripts: eight intentional awk expressions and fifteen reports
about the same BusyBox assignment in a subshell. None is suppressed or repaired
by changing the historical control flow.

The generator's CLI writes a private bundle and never contacts SSH or executes
its scripts. Supplied UUIDs are bindings, not observations. The checked bundle
uses explicitly synthetic fixture UUIDs and must never be sent to the PDA.
For actual collection, `prepare()` supplies the exact-candidate context and
bound classifier; `collector.remote_script(context)` obtains the observation
before a mainline UUID is known. Generate the later scripts only after that
UUID is observed and verified. The returned historical collector/finisher CLI
entry points still have their original admission contracts and are not new
live entry points.

## Offline installation binding

The [installer adapter](a53-ram-installer.py) validates the exact candidate
through the session binding and pins its private manifest, then derives the
existing guarded installer. The new shell uses the distinct
`a53-service-ram-deployment-1` receipt name and `a53-service-ram-regression`
experiment field. It requires the supplied preceding Gemian boot ID before
entering the device gate; its strict receipt parser also requires that boot ID.
The historical installers and receipt parsers remain unchanged.

The [focused tests](test-a53-ram-installer.py) pass on macOS and the Linux RE VM.
Their inert transport covers three success/skip/shutdown-disconnect cases,
21 failure/interruption cases, changed boot and old receipt-name refusals,
changed local validator inputs and twelve receipt mutations. Reversing the
adapter's six substitutions reproduces the entire original generated shell,
including the live-GPT guard, private tmpfs staging, single write, independent
full readback and clean-shutdown sequence. Shell syntax and full ShellCheck pass.
The [test receipt](results/a53-service-ram-installer-tests.json) also records a
passing real-candidate validation and eight negative candidate/UUID cases.

The validated seven-file private candidate has now been fetched to the host.
Its complete inventory, hashes, permissions and exact zero padding were checked
again after transfer. Neither the image nor its embedded private key is published.
The generated installer bundle uses a synthetic fixture boot ID; it must never
be executed against the PDA. The adapter CLI offers offline `prepare`,
`validate` and `receipt` operations only. Preparation writes an exclusive private
bundle and does not call SSH, execute the installer or supply a device budget.
Actual installation still binds a fresh observed Gemian identity and uses the
existing [bounded installer runner](../2026-09-05-owner-away-experiment-preparation/baseline/scripts/install-boot2.py).
The host runner below begins only after its verified deployment receipt and the
owner's physical selection are available.

## Finite session

The proposed board question is whether the service configuration preserves
CPU0–7 startup, authenticated USB, console availability and complete logging
on the existing device description. Namespace/BPF behavior on the PDA needs
its own declared measurement; the RAM shell alone cannot demonstrate Debian
service behavior. Missing identity or logs must remain inconclusive.

Prepare one physical selection, one 45-second observation invocation, at most
one 15-second bound identity probe, one 30-second log-export invocation and
one 15-second normal recovery request. Use the existing bounded host runner
with 128 KiB observation/probe output, 3 MiB framed log-export output and
16 KiB stderr limits. The unchanged logger has a 600-second/2 MiB RAM limit;
export may signal it once and inspect termination at most ten times. These
limits do not bound blocked kernel I/O or prove that a restart completes.

Live preparation must bind the actual guarded deployment receipt, preceding
Gemian boot and exact host-key bundle before connecting. Preserve each command,
bounded raw stream, process result and parsed log file privately; sync and
read back the saved evidence before a recovery request. Ordinary recovery
requires verified complete preservation of all available bounded RAM evidence,
even when the logger's own result failed. Incomplete preservation, failed
identity or failed RAM guards require a separate reviewed recovery decision;
they never select an automatic retry. A returned helper is not a successful
restart. Confirm a changed boot in known-good Gemian afterward, independently
of the USB connection's exit status.

The host entry point and separate return collector below implement this sequence.
No keyboard event capture, eMMC partition read, namespace/BPF
operation or repetition is added to this session. Its success branch requires
the attributable baseline observation, complete log and confirmed recovery;
a refusal selects diagnosis from preserved evidence. Do not reactivate the
consumed baseline, keyboard or eMMC budgets.

After a reviewed first board regression pass, the conditional
[ten-cold-boot protocol](A53_COLD_BOOT_PROTOCOL.md) defines the later repeated
serviceability gate. This one session cannot count as that series: its selected
kernel had no prior PDA runtime pass at selection, and no per-cycle keyboard
observation or cold-start sequence was admitted here.

The [later Wi-Fi observation](../2026-09-07-mt6797-wifi-observer-feasibility/BOOT_CPU_LIMIT.md#later-owner-selection)
resolved the device state. Any later boot2 write still uses the reviewed
live-GPT guard, full readback and clean
shutdown, followed by owner-operated physical selection. No installation,
collector or physical-selection budget is supplied by this preparation record.

## Host execution and evidence preservation

The [host runner](a53-ram-host.py) validates the exact candidate and guarded
deployment receipt, verifies USB credentials against the packaged authorization
and host key, and checks the Gemian return credentials. Its default is offline
validation. After physical selection and session admission, execution requires
the existing direct USB route before consuming one fixed private session.
Each of the four phases uses the existing bounded host runner once, with the
budgets above. Route and credential checks precede every connection; no phase
is retried. Local route inventories add at most two five-second command bounds
per phase and send no device packets.

The runner saves the observation and probe before sealing and exporting the log.
It retains the original streams and all decodable log files even when the export
fails. Before requesting recovery it writes and reads back a checksum manifest,
verifies every saved file, reclassifies the saved observation/probe/export and
requires complete preservation. It then runs the unchanged native recovery
script and the separate Gemian return collector. A failed logger can be fully
preserved and safely returned without passing the regression; a partial export,
changed saved evidence or failed identity stops before recovery.

The [host test receipt](results/a53-service-ram-host-tests.json) records thirteen
sequencing/refusal test groups and eleven real-candidate binding refusals on
macOS and the Linux RE VM. The integrated fixture uses the real candidate,
credential verification, script generators, parsers and return constructor;
device responses are injected. All four generated scripts remain byte-identical
to the earlier ARM64 shell-test receipt. No new kernel or remote shell behavior
was introduced by the host runner.

Actual execution binds the private `session-1/deployment-summary.txt` receipt
before starting. An occupied or interrupted execution is consumed, and its
evidence remains in place. The aggregate pass requires the baseline observation,
complete sealed log and changed-boot Gemian confirmation. It does not establish
Debian service behavior, a persistent filesystem or the ten-cold-boot release gate.

The [September 25 live preflight](results/a53-service-ram-live-preflight-20260925.json)
revalidated the exact private candidate and generated the guarded installer
bound to authenticated Gemian boot `a3eb4157-ef96-45d2-a8e0-405b1ef46572`.
Syntax and ShellCheck passed. The device then reported 98% battery, `usb/online=0`
and `ac/online=0`; cable-power and the direct USB host route remain unresolved.
No installer ran, boot2 write or shutdown occurred, and no physical A53 session
was selected. A fresh live power/route check remains necessary before deployment.

## September 25 first board session

The [sanitized runtime receipt](results/a53-service-ram-runtime-20260925.json)
pins the exact image, deployment receipt and boot identities. In Gemian, the
reviewed installer passed the live-GPT and block-device guards with 85% battery,
wrote boot2, matched a full independent readback, and shut down cleanly. The
first armed host window expired before an owner start report and saw no new USB
device. It made no mainline connection and consumed no physical selection.

The owner then reported one boot2 start. A direct USB route and the expected
gadget appeared, and the host runner used its one session. The authenticated
observation and bound identity probe passed for release
`7.1.3-gemini-a53-service-facilities`. The complete saved log covers sequence
zero through explicit seal: 1,823 records and 126,413 bytes. Its startup record
shows CPU0 through CPU7 and eight activated processors. The normal native
recovery request was sent once after evidence preservation.

The first Gemian return attempt timed out before authentication. Its SSH error
ended in CRLF, which the then-pinned return classifier rejected because it
accepted only LF for exact connection failures. The consumed runner result is
`session-inconclusive`; it is not rewritten. A separate, read-only probe using
the pinned Gemian host key verified Linux `3.18.41+`, the expected board and
Debian identity, `systemd` running and a stable boot ID different from both
the preceding Gemian and mainline boots. This confirms the actual return.
The private request, response, process record and checksums remain retained.

The [parser correction receipt](results/a53-return-crlf-parser-20260925.json)
records the exact stderr digest and focused validation. The classifier now
accepts LF and CRLF only for its five named pre-authentication connection
failures. Authentication, host-key,
partial-output and unknown failures still stop; the focused return and host
fixtures pass. This repairs later sessions without replaying this consumed
window. The device result establishes this kernel's first CPU/USB/log boot,
not Debian services, owner console acceptance or the ten-cold-boot gate. No
unchanged-image retry is selected.

## Bounded Gemian return confirmation

The [return helper](a53-ram-return.py) binds the exact candidate and installer
adapter, guarded deployment receipt, preceding Gemian boot, native recovery
script and request transcript before any connection. Its default operation is
offline validation. An explicitly admitted execution consumes one fixed private
output directory before starting the existing bounded SSH runner. It requests
no restart and never replaces existing evidence.

The helper allows at most twelve 15-second slots within a 180-second connection
window. Only five exact pre-authentication connection failures permit the next
scheduled slot. Authentication, host-key, partial-response and unknown failures
stop the window. Credentials are checked before every connection. Each response
is limited to 4 KiB stdout and 16 KiB stderr, and checks Gemian identity plus a
stable nonzero boot UUID distinct from both preceding Gemian and mainline.
The health command must succeed before the probe can finish its frame.

The [test receipt](results/a53-service-ram-return-tests.json) records eight test
groups passing on macOS and the Linux RE VM. These exercise the actual host
runner with inert children, the probe shell with fixture files, consumed-window
refusal, timing, credential changes, response limits and evidence readback.
Fourteen altered deployment/request/source/trust cases also refuse on both
platforms with the real candidate and synthetic receipts; child processes are
forbidden during those binding tests. No test contacts the PDA.

A confirmed return proves that known-good Gemian is running. It does not promote
an incomplete baseline or log capture to success. Any later device session
requires current device custody, a fresh live deployment binding and its own
pre-boot handoff.
