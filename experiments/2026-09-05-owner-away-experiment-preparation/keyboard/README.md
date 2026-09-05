# Targeted keyboard coverage packet

## Record

| Field | Value |
| --- | --- |
| Queue ID | `keyboard-coverage` |
| Status | Preparing; device unselected; no runtime execution |
| Parent | `2891e041fbc5291956bd90882f0f52fea11f2504` |
| Device | Named Gemini development unit; US printed layout from prior record |
| Implementation | A53 serviceability keyboard worker; reviewer and custodian unassigned |
| Date | 2026-09-05 |
| Parent packet | [Owner-away preparation](../README.md#keyboard-coverage) |

## Question and evidence

Does the exact authenticated A53 baseline produce the declared matrix events
and VT bytes for F1–F10, Home, Page Up, Page Down, End and the selected modifier
release sequences, while the owner can read its screen and authenticated USB
remains available?

The historical [AA-r1 acceptance](../../2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt)
left F1–F10 and Page Up/Page Down unconfirmed because the console supplied no
visible discriminator. Its retained map checksum is
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`.
The [layout record](../../2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt)
supports the function/navigation policy. The
[active-binary matrix](../../2026-07-12-input-backlight-recovery/results/keyboard-keymap-active-boot.txt)
supplies coordinates, including physical Fn as keycode 125; the older
source-labelled `KEY_FN` coordinate is not the oracle. These are historical
inputs, not proof that the new baseline includes or executes the same map.

This packet intentionally covers 25 distinct keycodes and 20 exact cases, not
all 52 assigned matrix positions. Independent raw evdev and raw VT streams
distinguish input-path or physical-sequence mismatch from VT mapping mismatch.
The helper displays each instruction so the owner sees a test prompt; captured
function escape bytes provide the missing discriminator. Each modifier case
ends with unmodified A, which also tests return to the plain VT table.

## Dependencies and exact identities

[expected-contract.json](expected-contract.json) is deliberately unfilled and
refuses classification. Fill it only from reviewed exact package, candidate,
helper, launcher and runtime identity evidence. It is not a default candidate.
Its state may become `conditional` only after the complete offline gates pass;
the queue integrator owns the corresponding shared metadata change.

Required runtime predicates are the exact new baseline's first authenticated
USB/console/input serviceability pass and its subsequent attributable known-good
recovery. Ten cold boots are not required. A later admitted boot of matching
inputs can run this packet; the first baseline boot cannot satisfy its own
already-completed recovery prerequisite. Cumulative cold-boot acceptance stays
separate. No PWRAP historical profile, similarly named moving profile, or
quarantined eMMC profile is selected by this packet.

Relevant unchanged resource contract is CPU0–7 online and CPU8/9 offline, the
AW9523 provider and matrix consumer, the normalized matrix, 20 ms polling and
2 us column delay, the accepted eight-table map, and readable foreground tty1.
The parent must verify these against the candidate's composed DT, configuration
and userspace. No kernel or DT change is requested by this packet.

Candidate, Image, DT, configuration, initramfs, exact helper and launcher hashes,
kernel release, real input sysfs path, capability digest, and baseline/recovery
result hashes remain missing. So do an exact ARM64 helper build, the complete
launch/receipt wrapper, an exact-userspace execution fixture, independent review,
and combined session/power-duration review. These missing gates prevent both
conditional readiness and physical admission.

## Frozen proposed observation protocol

[protocol.json](protocol.json) is the reviewable v1 sequence. It contains 142
press/release transitions (71 presses) in 20 ten-second windows after a
two-second no-input check: 202 seconds of timed input windows. The launcher must
send TERM by 210 seconds and reap the process group by 215 seconds, recording
any forced interruption as inconclusive. It requests no added
boot, load, thermal samples, storage reads/writes, mount, LED, wake, suspend,
clock, rail or CPU-admission action. The 10-second window is an engineering
ceiling, not measured owner timing; its usability and the baseline's existing
time/power limits must be reviewed before readiness. No retries are admitted.

| Cases | Owner interaction | VT discriminator |
| --- | --- | --- |
| 1–10 | Hold left Shift, then Fn; tap digit 1 through 0; release Fn then Shift; tap A | F1 through F10 escape string, then `a` |
| 11–14 | Hold Fn; tap Left, Up, Down, Right respectively; release Fn; tap A | Home, Page Up, Page Down, End escape string, then `a` |
| 15–16 | Hold left/right Shift respectively; tap A; release Shift; tap A | `Aa` |
| 17 | Hold Ctrl; press A; release Ctrl before A; release A; tap A | byte `01`, then `a` |
| 18 | Hold Alt; tap A; release Alt; tap A | Escape, `a`, `a` |
| 19 | Tap Fn and release; tap A | `a` only |
| 20 | Tap H, E, L, P, Enter; release each before the next | `help` and carriage return; no shell command executes |

Follow only the current displayed case; never catch up after missing a window.
Release every key between cases. Deliberate short taps are required; auto-repeat
is an inconclusive protocol violation, not automatic hardware failure. The
four unassigned contacts and unlisted combinations are outside this budget.

One observation claim per admitted boot is required, consumed at launch even
on refusal/interruption. The baseline launcher must create its exclusive claim
in verified RAM-only `/run`, refuse existing claims, and retain partial evidence
without rerunning. An SSH disconnect, owner interruption, unreadable prompt,
lost input device, held key at a boundary, resource error, unexpected heat or
changed recovery behavior stops this packet and affected dependents. The owner
releases all keys. There is no automated reset or transition to another packet.

## Observer and launcher contract

[keyboard-observe.c](keyboard-observe.c) is a narrow Linux evdev/VT reader:

- Explicit `--capture eventN 13 MINOR`; exact character-device identity and
  `keyboard-matrix` descriptor name, no symlink following and no evdev grab.
- Foreground tty1, `K_UNICODE`, `K_ESCPREFIX`, exact function strings queried by
  `KDGKBSENT`, and no held evdev keys before/after each window. Meta mode is
  checked, never changed. The baseline must separately audit its meta policy.
- No keyboard-map, CPU, regulator, storage or VT-selection writes. It changes
  tty1 termios temporarily to capture control keys without invoking a shell,
  then restores the saved attributes on normal exit and handled INT/TERM/HUP.
- Two input descriptors, 64 input records and 128 VT bytes per window, at most
  1,280 input records and 2,560 VT bytes. `SYN_DROPPED`, EOF, partial records,
  poll errors and exceeded bounds withhold the complete footer.
- stdout is the private machine transcript over authenticated SSH; instructions
  go to tty1. stdout is nonblocking and output saturation stops capture. Raw
  test bytes are not sent to the kernel log or interpreted as
  commands. Linux evdev/VT ABI and signal behavior still need target validation.

The admitted baseline launcher must provide exclusive tty1 ownership. Merely
opening `/dev/tty1` does not establish exclusivity. No local shell, getty, competing
observer or old automatic capture may read input throughout this session. The
baseline may use a passive console-status display, but the launcher must quiesce
its writes while instructions are displayed. It must verify the unique matrix
event sysfs ancestry and matrix provider, compare capabilities and device numbers
to the frozen contract, and run the reused
[console-keymap verifier](../../2026-07-20-keyboard-console-map-diagnostic/src/console-keymap-verify.c)
with `--verify` before and after capture. An absent or changed table refuses.
Kernel logging onto tty0/tty1 refuses; a lower loglevel alone is insufficient.

If raw tty restoration fails, do not start a shell. Preserve the SSH management
path and use the baseline's reviewed recovery. SIGKILL/power loss cannot restore
tty attributes; the exclusive RAM claim must still prevent silent restart.
Physical power/reset recovery remains the owner's action when USB is unavailable.

No installer is added. Use only the selected baseline's current guarded live-GPT
boot2 installer, full readback receipt and clean shutdown, with known-good recovery
already verified. This packet does not select or deploy a candidate itself.

## Capture and classification

The future launcher captures bounded raw output privately, mode 0600 below an
access-restricted ignored artifact directory. Do not publish arbitrary VT bytes:
an owner may accidentally type unrelated personal text. Publish only reviewed
identities, checksums, counter summaries and per-case classifications. Partial
observations are evidence and must not be overwritten or treated as temporary
cleanup targets.

The sidecar receipt must include every matching contract field, deployment and
recovery reference digests, stable mainline `boot_id_before`/`boot_id_after`
different from `known_good_boot_id`, before/after CPU-online strings, exact map
hash, event basename and minor number, capture digest and exit status. Required
true witnesses are `baseline_dependencies_verified`, `map_verify_before`,
`map_verify_after`, `console_logs_separated`, `tty1_exclusive`,
`owner_sequence_complete`, `owner_screen_readable`, `post_capture_usb_pass`, and
`budget_claimed_once`. The wrapper and reviewer must verify the referenced
records; these booleans alone cannot authenticate a receipt or prove a recovery.

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/keyboard/classify.py \
  --contract FROZEN_CONTRACT.json --receipt PRIVATE_RECEIPT.json \
  --capture PRIVATE_CAPTURE.txt
```

The current unfilled contract refuses. Strict framing validates each evdev scan
and key pair, complete synchronization frames, per-window counters, VT hex bytes,
the restoration footer, and absence of trailing records. Dropped events, repeat,
truncation, malformed input or missing witnesses are inconclusive. Exact events
with incorrect VT bytes isolate the VT/userspace question. Event/coordinate
mismatch requires review of the owner's actual physical sequence before a
hardware conclusion; an incorrect or missed physical key can give the same trace.
Only all 20 exact cases plus attributable recovery can support the scoped
once-only hardware result. The classifier never promotes hardware support.

## Offline validation and result handoff

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/keyboard/test_packet.py
python3 experiments/2026-09-05-owner-away-experiment-preparation/keyboard/render_protocol.py
```

The [offline result](results/offline.txt) records actual checks. Synthetic fixtures
cover full pass, input/VT mismatch, missing input identities, missing dependency
witnesses, every step's truncation, interruption evidence, key repeats, sync loss,
wrong device/boot, CPU8/9 online, restoration failure and checksum mismatch. The
coordinate oracle is checked independently against the retained active-binary map.
Those tests do not execute target ioctls or establish hardware behavior.

After target packaging and exact-shell tests, an independent reviewer must freeze
the candidate contract and all receipt/launch identities. The integrator then
records only the appropriate preparation state. After an admitted runtime, retain
the deployment receipt, boot ID, consumed one-shot claim, per-case result and
known-good recovery. Any relevant input or protocol change, consumed budget or
withdrawn prerequisite makes readiness stale. Shared-boot compatibility with eMMC
or another packet requires advance ordering/interference/combined-budget review.

## Owner session card (prepared wording; not an action request)

After the custodian confirms installation and admission, select the named boot2
candidate physically. Wait for the authenticated baseline screen. The operator
will confirm the USB and recovery prerequisites before starting the keyboard
check. It takes about three and a half minutes once started.

Follow one numbered instruction every ten seconds. Use only the displayed keys,
release all keys after each instruction, and wait for the next number. The last
case is HELP and Enter; it is captured as test input. If you miss an instruction,
cannot read the screen, or the device behaves unexpectedly, release every key
and tell the operator. Do not repeat the test or select another queued candidate.
Recovery follows the baseline's separate reviewed card; another physical boot
selection is never automatic.

## Conclusion

Protocol and host classifier implemented; new keyboard hypothesis untested.
Preparation is not complete, and no physical session is admitted. The
[keyboard hardware boundary](../../../docs/hardware/keyboard.md) and current
support claims remain unchanged. Scheduling belongs only to the
[roadmap](../../../docs/ROADMAP.md#owner-away-progress).
