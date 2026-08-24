# Experiment: A72 global initcall ledger

## Status

Patch generated, validated, and admitted as canonical `0361`. The rejected
predecessor left both observer `driver-init`
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

The canonical parent is exact patch `0360`. Buildbox generated patch `0361`
from the pinned parent source state and three touched-file hashes. Source and
patch semantic checks, exact three-file scope, byte-identical replay, and
strict checkpatch all pass; checkpatch reports zero errors, warnings, and
checks. The fetched patch is admitted byte-for-byte with SHA-256
`ec7e185fdcbf7eedb55652b25173a431e0e02157e05c8a7a534478d4b2ee5b7b`.
The next action is an isolated Buildbox kernel build of profile
`a72-global-initcall-ledger`; no candidate exists yet.
