# Attended targeted keyboard session

Status: conditionally prepared; device unselected; both execution bindings disabled.
The primary integration coordinator owns preparation and review and will take
exclusive device custody at the attended handoff. This is one new boot containing
its own prerequisites and the existing 20-case keyboard observation. No physical
selection or capture is admitted by this document alone.

## Inputs and question

Use only the candidate in the
[console-ownership validation](../../2026-09-08-keyboard-console-ownership/validation.json):
raw boot `7dfc3b1f771a12b8e711f699cf8fcfd2678aedc15bc9d8bcc98554f9c6654cdb`.
[session-preparation.json](session-preparation.json) pins its padded identity,
corrected enabled monitor package, current source closure, duration receipt,
installer and command-validation evidence. The verified console baseline and
recovery remain prerequisites; the
[passing disconnect result](../../2026-09-08-keyboard-console-ownership/DISCONNECT_RETEST.md#attended-result)
establishes the corrected mechanism but cannot supply this new boot's reader state.
No kernel, DT, keymap, CPU policy or device image change is proposed.

The hypothesis is that the retained matrix driver and accepted VT map produce
all declared evdev transitions and VT bytes for F1–F10, navigation and the
selected modifier releases. The independent streams distinguish a mapping
failure from a physical-sequence/input mismatch. A complete 20-case result,
owner report, preserved log and attributable recovery support only the stated
25-keycode coverage. Incorrect physical input must be reviewed before blaming
hardware. A failed prerequisite stops capture; no replacement test is selected.

## Handoff and finite sequence

1. When the owner is available, use the existing guarded installer with
   `--purpose keyboard-capture`. Its fresh fixed receipt is
   `a53-keyboard-capture-deployment-1`; only the receipt namespace differs from
   the previously exercised installer. Revalidate known-good Gemian, live GPT,
   inactive boot2, power and full-partition identity. Skip an exact match and
   shut down cleanly. Do not reuse the consumed disconnect deployment receipt.
2. The owner selects boot2 once and reports the readable baseline screen. Admit
   one 12-second identity connection, bounded to 1 KiB stdout/16 KiB stderr.
   Require a fresh ID excluding the dependency boots, the last mainline
   `fe849250-5d28-4f67-88db-cc3e38413dcd`, and last recovered Gemian
   `1128b013-25b3-4e9c-9a94-398df98c2471`. Recheck the current predecessor at
   the real handoff; a changed predecessor invalidates the prepared identity card.
3. Prepare and publish one actual boot-specific disconnect admission. Run the
   existing two-second deliberate disconnect and sole 30-second strict export.
   Require the complete semantic pass, terminal/reaped child and empty reader
   inventory. Preserve the seven evidence members under that admission ID.
4. Run [metadata.py](metadata.py) once with the same admission/package and
   explicit `--execute`: 30 seconds, 16 KiB per stream. It requires the passing
   proof before transport. Reparse its actual output and exact command; retain
   the generated runtime receipt. Record the actual continuous custody and owner
   readiness separately. The owner must be ready to follow the screen for about
   three and a half minutes before capture begins.
5. Fill the actual classifier contract from the validated candidate plus this
   metadata. The tracked unfilled contract remains a template. Use the same
   admission ID and fresh boot throughout; do not edit prior evidence. The
   capture preparer must accept duration, metadata, custody and disconnect
   receipts and the exact package. Publish the complete capture binding and
   freeze generated delivery/capture/export command hashes before execution.
6. Run one delivery (30 seconds, 4 KiB stdout), then one capture (240 seconds,
   128 KiB stdout). Each initial guard requires boot age below 240 seconds.
   Follow the existing [20-case protocol](README.md#frozen-proposed-observation-protocol):
   202 seconds of input windows; monitor TERM/KILL/reap bounds remain 210/214/215
   seconds. Never catch up, repeat a missed case or run commands on the device.
7. Independently export the four fixed capture files once (30 seconds,
   278,528-byte stdout cap). Reparse and preserve all available members even if
   classification fails. Obtain the actual owner's completion/readability report
   and classify using the exact admission. A classifier result alone is not final
   hardware acceptance. No second capture is allowed.
8. Disable the consumed bindings, preserve and seal the original logger once,
   then make one guarded native recovery request after unique evidence and
   terminal child state are established. Confirm authenticated changed-ID Gemian.
   The [combined budget](CAPTURE_ADMISSION.md#combined-budget) leaves the logger
   seal below boot age 540 seconds at the latest permitted capture start;
   preparation/owner delays are not additional budget.

Every phase has one claim and no retry. The private session helper has prepared
only the identity command and revalidated offline dependencies/duration; no
future runtime or custody receipt exists. Actual boot-specific source checks
must still pass before publication and execution. Any source/package/protocol
change, consumed claim or changed predecessor invalidates the prepared state.

## Failure and preservation

On a missed/unreadable instruction or owner interruption, release every key and
stop capture. The local transport runner handles interruption; the measured
monitor disconnect path attempts bounded child cleanup. Its actual retained
status decides whether termination/reaping is established. A host timeout alone
does not establish remote termination or restored termios. Do not start a shell.

A metadata/delivery refusal before capture can use the completed same-boot proof
files and then the ordinary logger/recovery path. If capture started, preserve
the complete available fixed-file export and require attributable terminal state
before recovery. If strict export or preservation is incomplete, retain RAM and
stop for bounded diagnosis; do not reboot away unique evidence or treat missing
files as a clean reader inventory. There is no fallback scan or proof retry
silently added to this packet. Unexpected heat, charging anomalies or changed
recovery behavior stop this session and affected dependents.

## Validation and limits

The unchanged candidate and newly namespaced installer passed local validation,
Bash syntax and ShellCheck; 12 installer methods pass. The new generated installer
is byte-identical to the exercised disconnect version after normalizing only
its fixed receipt name. No live handoff has run for this session.

Buildbox verified the pinned Ubuntu BusyBox package and binary, then checked
all four generated metadata/delivery/capture/export commands with ARM64 BusyBox
`sh -n` under the pinned QEMU. These are syntax checks with synthetic runtime
values, not device execution or ioctl tests. The generated commands remain
private. Existing metadata, capture, disconnect and prerequisite fixtures passed;
repository publication checks passed. No kernel or userspace rebuild was needed.

## Owner card (wording for the later verified handoff)

Keep USB connected. After shutdown is confirmed, use your established silver-button
boot2 selection and report the baseline screen immediately. Do not type yet.
When the keyboard check starts, follow one displayed instruction every ten seconds,
release all keys between cases, and wait for the next instruction. The final
HELP-and-Enter sequence is captured as test input. If you miss a case or cannot
read it, release all keys and tell the operator; do not repeat it or reboot.
