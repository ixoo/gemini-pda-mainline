# Enabled runtime boundary and same-process storage session

Status: implementation and synthetic verification, coordinator review required
before any live execution. The earlier disabled-only test did not model the
locally enabled gate: it raised an incidental TypeError for a missing context.
That review failure is preserved here and is not treated as an accepted refusal.

## Callable boundaries

`collect` now requires an exact prepared-context shape, matching raw admission
bytes and a fully revalidated admission, including independent custody, physical
selection and power facts, before dependency revalidation or permanent claim.
`perform` similarly reparses the complete completion admission and its evidence
before claiming. Unknown/missing contexts raise an explicit ValueError. Disabled
behavior is retained through an explicitly injected disabled gate in tests; it
is no longer inferred from whichever gate happens to be in the worktree.

[mainline_host.py](mainline_host.py) retains the exact original one-shot identity
command and ten-second, 4096-byte stream bounds. The new `identity_window` wrapper
starts both host clocks before all local prerequisite and transport work. Only
successful transport, exact identity framing, expected kernel release and a new
boot outside the baseline/recovered identities produce a process-local receipt.
No new connection or device command has been added.

[live_window.py](live_window.py) binds that receipt to candidate manifest digest,
new boot, observation admission UUID and exact admission bytes. It counts device
uptime plus the maximum of elapsed wall and monotonic host time, conservatively
including identity duration, coordination and host sleep. Invalid/nonfinite or
reversed clocks refuse. The small receipt is held only in this process; the
runner has no serialization or resume operation. Trusted Python orchestration
is the boundary, not a sandbox against code that rewrites its own objects.

Collection requires age below 400 seconds and strictly more than 164 seconds
remaining in the original 600-second lifetime: pre/read/post plus separate seal,
including one second of existing process-metadata tolerance for each transport.
Before each phase claim it rechecks the remaining phase-plus-seal allowance
(164, 118, 77 seconds respectively). Preflight must match the receipt's boot.
Preservation requires the same receipt/session/boot and strictly more than 31
seconds remaining. Ordinary recovery after preservation and the later known-good
probe do not require an unexpired logger; their own proof gates remain intact.
No claim about replayable offline authentication of host timestamps is made.

## Actual orchestration

[session.py](session.py) is the concrete runner. Default invocation has no I/O
or transport. Only after coordinator review and actual owner selection/power,
prepare an observation admission with current source pins and start:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/emmc/session.py \
  --execute --admission PRIVATE_ADMISSION
```

It authenticates identity once, reports readiness and waits. Send one newline-
terminated JSON action on its standard input to collect:

```json
{"action":"collect"}
```

The runner returns the classification and waits again. After separate review
and preparation of the preservation admission bound to the new observation
manifest, send:

```json
{"action":"preserve-log","admission":"PRIVATE_PRESERVATION_ADMISSION"}
```

Only explicit collection and preservation are supported. No keyboard, recovery,
reboot or next test is automatically run. Do not type placeholder paths literally.
No live invocation of this command was made during preparation.

A handled failed/incomplete read returns an attributable negative result, keeps
the timing receipt and allows only separately admitted preservation, with no
postflight or second collection. The completion protocol still requires a sealed
observation manifest and attributable preflight. An unknown boot, failed identity,
unhandled interruption or admission/timing refusal stops the process and discards
the receipt. EOF also discards it. The identity directory is derived solely from the admitted session UUID under
the fixed experiment identities root; no directory override exists. Restarting
that admission therefore refuses before another identity connection. No automatic new directory/UUID is
created to reset an observation budget.

If interruption prevents a sealed attributable observation archive, this adapter
cannot export the log using a guessed identity. Preserve all existing private
files and refer the exact interruption to the coordinator for separate recovery
or evidence-preservation admission; no automatic recovery or acknowledgement of
unique RAM loss follows. Handled read failures do not enter that exception path.

## Verification

The new tests block real subprocess creation and use existing synthetic private
archive/transport fixtures. `test-session.py` runs actual identity wrapper,
collector and completion logic through fake transports, checking exact identity
command bytes and independent claims. It covers explicit identity/read/seal,
failed read followed by preservation without another observation, invalid identity,
failed identity transport, elapsed identity duration, expiry before claim, CLI
interruption and restart refusal. The test consumes no device budget.

Launcher/completion fixtures now exercise enabled missing/false admissions,
changed source identity, raw/context divergence, missing/invalid/expired timing,
reversed clocks and candidate/boot/session mismatch before claim or subprocess.
Results: launcher 18 PASS; completion 22 PASS; orchestration 8 PASS;
disabled/runtime boundary 2 PASS; host route prerequisite 3 PASS; explicit
prerequisite selector 3 PASS. Packet suite ran 28 tests: 26 PASS and two
exact BusyBox/QEMU-only cases skipped because those binaries were not supplied.
The original one-shot and raw-evidence suites remain relevant. Exact BusyBox/QEMU
and kernel/device behavior are outside this host-only run.

New source bytes invalidate the earlier private draft's source identity. Keep
that draft and all consumed receipts unchanged; finalize a new current admission
only after coordinator review and actual facts. The old ENABLEMENT.patch remains
historical and must not be applied to the revised source closure.

The shared host helper bytes changed while its identity command bytes remain
unchanged. Any other prepared package that pins mainline_host.py (including a
keyboard capture package) must be re-evaluated against its exact source closure;
old source-matched readiness cannot silently transfer to these bytes.

Final local verification also ran runtime-boundary and orchestration suites with
Python optimization enabled; both passed. The common repository gate passed
(189 profiles, eight invariant mutations), with its Linux-only provenance checks
explicitly skipped on this host. No kernel build, hardware probe or identity
connection was performed. The complete local repair commit includes the original
three-file enabled state by coordinator instruction; source enablement is still
independent of the unfilled runtime admission.
