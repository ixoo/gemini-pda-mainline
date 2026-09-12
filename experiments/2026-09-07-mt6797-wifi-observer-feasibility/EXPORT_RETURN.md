# Export startup with one normal return

Status: startup refused the CPU-online preflight; its normal return retained
the exact failure marker. USB export was not reached. The one-selection budget
is consumed. Session
`3f6581cf-157e-45fc-aaef-bf1d23e15df7` follows the successful
[boot-entry control](BOOT_ENTRY_CONTROL.md). It does not repeat an earlier
export image or select a WLAN cycle.

## Hypothesis and decision

The same 46-patch native kernel reaches minimal PID1 and retains a marker
through its normal restart. Applying that observed return path to full startup
can reveal a caught mount, preflight or USB failure, or complete the snapshot
export. Kernel, DT, compact runtime and private firmware/calibration inputs
stay identical to the preceding export; only startup/transfer code, session
identity and the explicit `wifi_return=1` argument change.

One physical boot2 selection has these decision branches:

* A complete host snapshot, matching receipt and retained `outcome=preserved`
  marker demonstrate the exchange and acceptance of the host save reply.
  This does not authorize clearing or establish Wi-Fi support.
* A retained `outcome=stopped` or `outcome=shell-stop` marker identifies a
  caught failure. Use its preceding stage to choose a correction; do not
  repeat unchanged bytes.
* A host save without the final marker proves preservation only. An earlier
  attributable stage proves only that stage. Silence or no return cannot
  distinguish failure before PID1, execution handoff, blocking I/O, failed log
  output or a blocked restart.

Match the exact session UUID and a candidate boot UUID different from both
the preceding and returned Gemian UUIDs. File presence alone is not attribution.
Analyze retained bytes privately in the RE VM; separate observation from inference.

## Changed startup and finite effects

The `export-return` action requires exactly one `wifi_return=1`, one selected
`wifi_cycle`, and an unchanged shell-to-Python boot/session handoff. Other
actions reject the return flag. The shell arms return only after proc, boot
identity and argument checks; Python rechecks them before its one request.
Both require root PID1/AArch64/Linux `3.18.41+`, the current boot and a successful
kernel-log marker before invoking the previously traced BusyBox `reboot -f`.
That utility requests the normal kernel restart path; it does not directly
program a reset register. No capture claim or controller takeover occurs, so
the existing [restart gate](RESTART_GATE.md) permits this path. A returned or
refused request parks PID1 without retry.

The shell emits at most 21 records, and Python at most eight including its
return marker, each at most 192 bytes through the checked kernel-log descriptor.
The additional terminal record is:

```text
<11>wifi-export-return-v1 boot=BOOT_UUID cycle=SESSION_UUID outcome=OUTCOME
```

`OUTCOME` is `shell-stop`, `stopped` or `preserved`. Existing stage markers
locate the last operation. The existing console ring may wrap; the control's
successful normal retention does not guarantee that every earlier line survives.

The [bridge](capture-device.py) reads the initial immutable 65,536-byte raw
PMSG snapshot, makes the same three ACM configuration writes and sends one
65,624-byte frame after one 52-byte request. The new optional 84-byte `WFA1`
reply binds the candidate boot UUID, session SHA-256 and snapshot SHA-256.
The host sends it only after complete snapshot readback, both file syncs and
both directory syncs. The device checks it after its existing post-send
capture-state check. It is evidence of the cooperating host's save procedure,
not a clear command or an independent kernel attestation.

Request, data and acknowledgement share each endpoint's existing 60-second
deadline. There is no retry, background watchdog or additional raw read.
Filesystem sync and arbitrary kernel I/O are not bounded by this deadline;
the native serial close path may also wait up to 15 seconds. A successful
device export retains its descriptor until restart. A caught failure closes
it before the stopped marker/return request.

The return covers caught failures only. A pre-PID1 hang, failed devtmpfs/proc
setup before arming, missing/invalid log channel, Python execution failure
after the shell is replaced, blocked kernel operation or failed restart can
still leave no automatic return. The injected missing-Python test explicitly
observed this handoff gap. This is not a general recovery watchdog.

On a failed or unacknowledged transfer, available host files and stage evidence
are preserved, but the complete raw snapshot may remain unretrieved. Returning
to Gemian can change the underlying PMSG header. Record that loss explicitly;
do not infer zero capture bytes, successful preservation or clearing admission.
There is no PMSG clear, WMT request, firmware load or WLAN cycle in this session.

## Validation and physical procedure

The host and exact packaged ARM64 Python runtime pass 22 startup, 14 stream and
five device-bridge tests. They cover bound acknowledgements, refusal after each
failed sync, a real local duplex pseudo-terminal exchange, return identity/log
gates, successful export routing and one restart request after a caught failure.
Every restart is injected. The existing private ARM64 mount/PID-namespace
fixture also exercises 12 shell paths with the pinned BusyBox, injecting the
log sink, restart, console/sysctl effects, command line and kernel release.
It verifies both environment handoffs and records the execution-handoff limit.

The [selected receipt](results/export-return-20260912.json) freezes all input
and package identities. Archive comparison verified 723 members, with only
the five expected startup/session members changed. Container reconstruction
was byte-identical; the validator rejected 17 container and six input mutations.
The 16,300,032-byte container fits the exact 16,777,216-byte padded partition
image. No new kernel build was needed. Shell syntax and ShellCheck passed.

Reuse the guarded live-GPT boot2 installer, preserve predecessor
and full readback evidence, and shut down cleanly. The owner selects boot2 once.
The agent is the sole device custodian. Standing
[project authorization](../../docs/SAFETY.md#standing-project-device-authorization)
covers this reviewed session and its one normal return.

Before selection, arm the existing attributed-USB watcher with the exact new
receiver digest/session, preceding Gemian UUID and `--acknowledge`. Its device
selection and one-invocation rules remain those of the
[original session](EXPORT_SESSION.md#host-preparation-and-one-request).
Also arm the existing 180-second changed-boot Gemian collector. It preserves
one console payload of at most 65,536 bytes with before/after identity checks;
an absent payload consumes no read. Preserve host status, partial evidence and
the console before any additional recovery. A timeout authorizes no repeat.

## Deployment and runtime result

The exact inputs were published at
`b127aff8c09fc561f2e54b53b602b6c5db43c859`, and the
[hosted checks](https://github.com/ixoo/gemini-pda-mainline/actions/runs/34663192255)
passed. Fresh inspection confirmed preceding Gemian boot
`57a8683b-b9dc-4643-99c1-aca916d3ae54`. The guarded installer resolved boot2 as
`179:30`, distinct from root `179:29`; its power samples were stable with a
present, healthy, fully charged battery. The predecessor was the completed
boot-entry control. After writing, both full checksums matched `3064aeba…4bff5`.
Clean poweroff closed SSH with status 255; the endpoint then became unreachable.
No fresh backup or automatic boot2 selection was performed.

Both collectors were armed before the owner confirmed one physical selection.
At `00:58:54 UTC` on 2026-09-12, the return collector authenticated Gemian boot
`a1efb6e0-4c7e-43f6-9b56-0ba6086bd8c2`. Before/after identity checks matched.
Its single console read preserved 65,524 bytes, SHA-256
`856cca9d179b0d61f4e82dd18e3f3d3f57c904e4f82b8f8a523a98c615a36037`.

RE-VM analysis found one exact session return marker at byte 61,288, with
candidate boot `606245b9-5e6f-45a7-bc8b-a5e6d09dc160` and `outcome=stopped`.
It is timestamped `2.693203` seconds and is followed by a normal restart line.
The retained sequence includes sysfs/pstore setup, all read-only input mounts,
the Python handoff and `python-entry status=entered`. Its final stage is:

```text
python=runtime:sys/devices/system/cpu/online status=stopped
```

This establishes that the full shell and Python runtime ran and that preflight
stopped at the required `0-7` CPU-online check. The exact online-list value was
not logged, so it cannot be reconstructed from this marker alone. Earlier
retained messages show active native HPS CPU policy and 13 `CPU8: failed to
boot: -1` messages between `1.634960` and `2.686638` seconds. Those observations
motivate auditing native CPU policy before the next candidate; they do not
prove the precise online set at the failed check. Do not weaken the check or
repeat this image merely to reach USB.

The host watcher completed its 180-second window without an attributed ACM
terminal and invoked no receiver. The observed startup failure precedes bridge
import, so application snapshot acquisition and ACM writes were not reached.
No host request, acknowledgement, clear or WLAN cycle occurred. The initial
raw snapshot remains unretrieved; this is not an export pass. The normal return
and retained-stage diagnosis passed for this one session. Gemian is left
running, and no additional recovery or device action followed collection.
