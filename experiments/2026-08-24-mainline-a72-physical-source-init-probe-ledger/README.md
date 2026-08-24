# Experiment: A72 physical-source init/probe ledger

## Status

Definition frozen. The rejected pre-capture candidate left both records exact
empty, so it did not establish its first probe checkpoint. This non-identical
successor moves record 1 into the observer's built-in init path before
`platform_driver_register()` and makes record 2 the first probe operation. A
successful probe record returns immediately, before allocation or any source
lookup.

## Hypothesis

The physical-source observer reaches its built-in driver init. If driver
registration binds the enabled DT node, its probe also begins. The two retained
records distinguish those boundaries without depending on USB, console, or
ordinary dmesg survival.

## Exact evidence

1. `GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A checkpoint=driver-init
   slot=1 crc32=85e5f336`
2. `GEMINI_A72_INIT_PROBE_V1 token=GAIP-20260824-A checkpoint=probe-enter
   slot=2 crc32=85116721`

Both use the already-qualified first-dmesg slots, payload-before-metadata,
signature-last commit, barriers, and full readback. There is no overwrite,
clear, repair, or retry.

## Decision table

| Retained result | Interpretation | Next action |
| --- | --- | --- |
| Neither | Observer init was not reached, or its first checkpoint refused | Move to an earlier independent init/writer boundary; do not repeat |
| `driver-init` only | Built-in init ran; probe entry was not established | Isolate registration return and match/bind before source work |
| Both | Built-in init and probe entry ran | Split allocation and the three source lookups in a later candidate |
| Malformed or foreign | Attribution failed | Reject without path inference |

## Safety and build contract

- At most two short writes occur only in retained records 1 and 2.
- The enabled probe path returns before allocation, phandle parsing, device
  reference acquisition, platform/provider/clock/BigiDVFS reads, direct-source
  registration, publication, owner mutation, or CPU requests.
- The normal physical-source path remains unchanged when the experiment mode
  is disabled.
- Patch generation and kernel compilation use Buildbox from exact clean,
  signed, pushed commits. A native VM build is not authorized.
- A package is not a boot candidate. Independent package, configuration, DT,
  Android-v0, marker, and padding validation remains mandatory.

## Current result

The canonical parent is exact patch `0359` and the managed Buildbox source
state and integrity are pinned in `contract.json`. The next action is to
generate the one logical `0360` patch on Buildbox, fetch only its validated
review package, and admit the byte-identical patch after replay and invariant
checks.

Generation attempt 1 from exact commit `4c28d9c7` passed source semantics, the
three-file boundary, format-patch validation, and byte-identical replay. Strict
checkpatch stopped on two style checks: a blank line after the platform-driver
declaration and a register call split before its sole argument. No patch was
admitted and no compile, candidate, or device action occurred. The
[stopped-attempt receipt](results/generation-attempt-1-checkpatch.txt) selects
only those two formatting corrections before regeneration.

Generation attempt 2 from exact signed commit `4d223912` passes parent source
integrity, the three-file boundary, source semantics, byte-identical replay,
and strict checkpatch with zero errors, warnings, or checks. The fetched patch
is byte-identical to canonical `0360`; see the
[generation receipt](results/buildbox-generation-4d223912.txt). The next action
was to commit and push that admission, then compile the exact isolated profile
on Buildbox.

That exact Buildbox compile now passes from signed, pushed commit `0023bd92`.
The fetched package is
`linux-7.1.3-gemini-a72-physical-source-init-probe-ledger-fc79cccb-4de8297d`,
with kernel release `7.1.3-gemini-a72-init-probe`; all package checksums and
provenance checks pass. See the
[build receipt](results/buildbox-kernel-0023bd92-pass.txt).

Offline deterministic assembly computes raw Android-v0 identity
`36631648...d81e3` (6,909,952 bytes) and exact 16 MiB padded identity
`4185b851...a03c`; the LK analyzer passes all 32 gates. The next gate is to run
the source-pinned builder and independent validator against those exact
identities. No device access or write has occurred for this successor.

That independent admission now passes. The two raw assemblies and two padding
constructions are byte-identical, both retained records occur exactly once,
all predecessor experiment markers are absent, and every effect after probe
entry is zero. See the
[candidate receipt](results/candidate-validation-36631648-pass.txt) and exact
[predeployment decision record](results/predeployment-hypothesis-20260824.txt).
The candidate is eligible for one guarded write to the live-GPT-resolved,
inactive `boot2`, followed by a clean shutdown; it is not a CPU-support claim.
