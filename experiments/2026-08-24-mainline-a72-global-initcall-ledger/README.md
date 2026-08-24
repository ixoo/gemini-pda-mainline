# Experiment: A72 global initcall ledger

## Status

Definition frozen. The rejected predecessor left both observer `driver-init`
and `probe-enter` records exact empty after a changed-ID Gemian cycle. This
non-identical successor moves both records out of the observer and into the
retained-ledger translation unit at two earlier global initcall levels. The
observer remains linked but is deliberately not registered.

## Hypothesis

The failing kernel reaches global `subsys_initcall` and then `fs_initcall`
before the later observer device initcall region. Two independent retained
records distinguish progress across those levels without relying on USB,
console, ordinary dmesg, or observer binding.

## Exact evidence

1. `GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A checkpoint=subsys-init
   slot=1 crc32=cf2a6946`
2. `GEMINI_A72_INITCALL_V1 token=GAIC-20260824-A checkpoint=fs-init
   slot=2 crc32=91ac2a49`

Both reuse the qualified first-dmesg raw writer: all-ones precondition,
payload-before-metadata, valid signature last, barriers, full local readback,
no overwrite, no clear, and no retry.

## Decision table

| Retained result | Interpretation | Next action |
| --- | --- | --- |
| Neither | `subsys_initcall` was not reached, or the first writer refused | Move to an earlier independent writer boundary and expose refusal attribution |
| `subsys-init` only | Subsystem init ran; filesystem init was not established | Split postcore/arch/subsys/fs ordering |
| Both | Both global levels ran; the failure is later, before the observer device init checkpoint | Split the device-init region with independent boundaries |
| Malformed or foreign | Attribution failed | Reject without ordering inference |

## Safety and build contract

- At most two short writes occur only in retained slots 1 and 2.
- The enabled experiment performs no observer registration, allocation,
  source lookup, physical snapshot, provider transaction, clock/BigiDVFS
  operation, publication, owner mutation, or CPU request.
- Historical physical-source modes remain unchanged when the new option is
  disabled.
- Patch generation and kernel compilation use exact clean, signed, pushed
  commits on Buildbox. A native VM build is not authorized.
- A successful compile is not a boot candidate. Package, configuration, DT,
  Android-v0, marker, padding, and independent validation remain mandatory.

## Current result

The canonical parent is exact patch `0360`. The managed Buildbox parent source
state, integrity, three touched-file hashes, and predecessor runtime receipt
are pinned in `contract.json`. The next action is one exact Buildbox generation
of canonical patch `0361`, followed by replay, strict style, and invariant
checks before admission.
