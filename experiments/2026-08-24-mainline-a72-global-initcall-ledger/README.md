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
The exact isolated Buildbox build of profile `a72-global-initcall-ledger`
passes and produces release `7.1.3-gemini-a72-initcalls`. Its fetched package
validates against the signed repository commit and exact config, Image, DT,
System.map, and manifest identities. Two deterministic Android-v0 assemblies,
two independent 16 MiB padding constructions, and an independent analyzer all
agree; all 32 LK gates pass. The accepted raw candidate is
`41a181f631456be55ae28b75ee525226dd7b41da844c5c4ed5a0acd3f13c5156`
and its exact padded Boot2 image is
`e9d565021de9ed1164aa78a78795d6a3dabd7af656aaa3df791e23424e66125a`.
Guarded deployment resolved inactive `boot2` from the live GPT as
`/dev/mmcblk0p30`, with Gemian rooted on `/dev/mmcblk0p29`. The predecessor
hash was recorded without creating a redundant backup. After write, sync, and
flush, a full 16 MiB readback matched the padded candidate exactly. Both
retained headers were exact empty immediately before the write, no retained
RAM was modified, and the device then shut down cleanly without reboot. The
[sanitized deployment receipt](results/deployment-20260824.txt) records the
exact identities and gates.

The read-only recovery path was frozen and mutation-tested before the boot. It
requires changed-ID exact Gemian, the unchanged full `boot2` checksum, live GPT
agreement, two direct 4 KiB retained reads, mounted pstore, and zero memory or
partition writes. Its three intended branches and 16 unsafe mutations pass;
see the [tooling receipt](results/recovery-tooling-validation-20260824.txt).

Runtime attempt 1 returned automatically to changed-ID Gemian. Read-only
recovery verified unchanged `boot2`, mounted but empty pstore, and both
`subsys-init` and `fs-init` records exact empty. Thus neither checkpoint was
retained. The result excludes the later observer registration and all source,
provider, publication, owner, and CPU actions from the implicated region, but
does not distinguish an unreached subsys initcall from writer refusal. Because
the prior positive first-record retention test used a controlled native
reboot, this result also does not independently prove retention across this
automatic reset. See the
[runtime receipt](results/runtime-attempt-1-before-subsys-or-unretained-20260824.txt).

This exact candidate is retired. The selected successor moves independent
records to the earlier pure and core initcall levels and adds writer/refusal
attribution, while retaining first-dmesg placement, signature-last writes, and
the complete zero-hardware-action contract. Screen color and reset timing
remain excluded from the inference.
