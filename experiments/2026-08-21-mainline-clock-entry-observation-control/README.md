# Clock-entry observation control

## Status

Source/evidence audit complete; exact non-identical control selected,
constructed, independently validated, and deployed to inactive logical
`boot2`. The full readback matched and Gemian is confirmed shut down. No new
kernel build occurred. The exact USB collector must be armed before one
physical selection.

## Question

Can the exact clock-entry Image, configuration, initramfs, and retained writer
reach a known serviceable runtime and positively prove its first checkpoint
when the only failed-candidate DT change—the clock-backend node enablement—is
removed?

## Selected control

Reuse the exact Buildbox package from commit `c3fd5d9`, including the same
Image, configuration, linked checkpoint code, initramfs, command line, and CPU
closures. Append that package's exact base Gemini DTB instead of its derivative
clock-entry DTB. Decompiled comparison proves exactly two source-level changes:

1. the descriptive pre-LK model string returns to the base label; and
2. `dvfsp-clock-backend@1001a000` changes from `okay` to `disabled`.

Pinned LK is already runtime-proven to replace the root model with `MT6797X`.
The built-in clock driver still executes its init function even with no enabled
matching device. Its platform-driver directory can appear only after the
`driver-init` checkpoint returns success and registration completes. Live USB
therefore provides an observation independent of returned empty RAM:

| Live result | Meaning | Next action |
| --- | --- | --- |
| Exact USB plus driver directory | First checkpoint wrote and read back; driver registration completed | Reboot once through the USB shell and test cross-version recovery of `driver-init` |
| Exact USB without driver directory | Image reached userspace but checkpoint or registration refused | Split the shared checkpoint gates; do not re-enable the clock node |
| No exact USB and automatic return | The exact Image/base-DT control did not establish serviceability | Stop; move to the last runtime-proven Image/DT baseline |
| Any CPU, identity, DT, or safety mismatch | Attribution failed | Reject without inference |

If the live control passes, returned Gemian should recover exactly
`driver-init` and not `probe-enter`. That is a positive cross-version recovery
test; an empty returned ledger cannot erase the stronger live driver-directory
proof.

## Source findings

- The failed candidate contains the checkpoint function and clock init/probe
  symbols in its linked Image, with the driver init at device-initcall level.
- Its packaged DTB contains the exact compatible, reservation address/size,
  `ramoops`, `no-map`, zone sizes, memory type, and enabled clock node required
  by the source.
- Linux 7.1.3 arm64 rejects `ioremap_wc()` only for map-memory PFNs. The exact
  `no-map` reservation makes `memblock_is_map_memory()` false, so this mapping
  primitive is permitted for the selected range.
- Known-good Gemian has previously recovered a real mainline ramoops record,
  but no device run has positively controlled this manual two-record writer.
- Earlier serviceable mainline runs prove that returned empty slots alone do
  not establish that a checkpoint call site was not executed.

The full frozen audit is in
[`results/observation-path-audit-20260821.txt`](results/observation-path-audit-20260821.txt).

## Safety

The control makes no protected read, secure call, MMIO access, clock enable,
storage operation, CPU request, owner registration, retry, reset, reboot, or
power request in the changed runtime path. It retains the same maximum of two
short writes, but with the clock DT node disabled only `driver-init` can be
called. The live probe is read-only. If serviceable, one exact boot-ID-gated
native reboot may be sent through the established USB shell so Gemian can
recover the retained record.

Any later installation must use the repository's standing guarded `boot2`
workflow: live GPT resolution, inactive/unmounted exact target, stable power,
predecessor checksum without a new backup, exact padding, sync/flush, full
readback, and clean shutdown.

## Next action

Push the sanitized deployment evidence and arm the exact USB collector before
one physical selection. Do not repeat the artifact. If exact USB appears, the
collector will classify the live driver-registration oracle and one
boot-ID-gated native reboot will return to Gemian for retained recovery.

See [`results/candidate-a36425f3.txt`](results/candidate-a36425f3.txt) for the
exact package, container, DT-delta, and mutation evidence.

Deployment attempt 1 replaced exact predecessor `444ffc4a...278de` with full
control `fc2a9a1a...30bf` on live-GPT-resolved inactive p30 while Gemian used
p29. External power was present at 100%/Good, both TEE identities remained
exact, all four retained slots were valid-empty, the full readback matched,
no fresh backup was made, and shutdown is confirmed. See
[`results/deployment-attempt-1-success.txt`](results/deployment-attempt-1-success.txt).
