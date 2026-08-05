# A41 ABI-7 kernel-identity binding design

## Scope and exact claim

ABI 7 adds one architecture-owned producer for three kernel identities and
binds them to an exact expected record from the static Open Firmware tree. The
positive source-contract claim is `PARTIAL_KERNEL_IDENTITY_BINDING`: complete
expected/running IKCONFIG, GNU build-ID, and forced-command-line pairs can be
published as `SEALED_IDENTITY` before capability finalization.

This is not complete runtime evidence. It publishes no CPU8/CPU9-local
registers, target capability record, system capability record, canonical
evidence identity, immutable plan, capability mutation, READY token, or CPU
admission authority. The profile, commit, boot, disable, and `maxcpus=8` gates
remain closed.

## ABI-6 missing-producer boundary

ABI 6 established a private arm64 record, rejected profile-authored RUNTIME
observations, and sealed the empty record. Its `SEALED_RUNTIME` label was
reserved but unreachable, and its future producer design did not distinguish a
verified kernel identity binding from target-local runtime evidence.

ABI 7 makes that distinction explicit. A kernel identity match is useful
attribution, but it cannot stand in for observations made by CPU8 or CPU9.
Therefore the only new positive state is `SEALED_IDENTITY`; there is no
`SEALED_RUNTIME` state in the kernel owner.

## ABI-7 state machines

The private evidence owner has these states:

| State | Meaning | ABI-7 reachability |
| --- | --- | --- |
| `OPEN` | The architecture seal has not run. | Initial only. |
| `SEALED_EMPTY` | Collection failed cleanly and the private identity storage remained all-zero. | Expected fail-closed result for a missing or mismatched record. |
| `SEALED_IDENTITY` | All three identity pairs matched and only their binding was sealed. | Positive identity-only result. |
| `FAULT` | Ordering, ownership, storage, or completeness was inconsistent. | Fail-closed error. |

Collection has a separate private state:

| State | Meaning |
| --- | --- |
| `UNCOLLECTED` | No collection attempt has occurred. |
| `FAILED` | One attempt failed; no partial global identity was published. |
| `VERIFIED` | A complete stack-local candidate was copied to private storage. |

Repeated collection, collection after finalization, an uncollected seal, a
nonzero failed record, and a partial verified record fault rather than
degrading to a positive state.

## Exact hook and ordering

The arm64 order is:

```text
smp_cpus_done()
  hyp_mode_check()
  arm64_collect_late_cpu_runtime_identity()
  arm64_seal_late_cpu_runtime_evidence()
  arm64_prepare_late_cpu_profile()
  setup_system_features()
```

Collection is post-hyp and pre-finalization. It additionally rejects execution
after `system_capabilities_finalized()` or after `ARM64_ALWAYS_SYSTEM` appears.
The seal release-publishes its state and preparation acquire-loads it.

## Expected OF record and topology

The expected record is exactly one static leaf at
`/chosen/gemini-late-cpu-provenance`. The parser requires the exact root and
`chosen` relationship, `chosen == of_chosen`, exact unit names without unit
addresses, no child below the provenance node, and one globally matching
compatible node. Dynamic, detached, overlay, dead, or dynamically supplied
properties are rejected.

The explicit DT record contains these 15 properties:

```text
compatible = "planet,gemini-a72-runtime-binding-v1"
schema-version = 1
profile-id = "mt6797-a53-a72-a41-v7"
target-cpus = 8, 9
target-mpidrs = 0x200, 0x201
expected-ikconfig-identity
expected-gnu-build-id-identity
expected-cmdline-identity
upstream-source-sha256
patch-series-sha256
config-inputs-sha256
resolved-config-sha256
package-image-sha256
build-provenance-sha256
record-identity
```

OF unflattening synthesizes the required sixteenth property, `name`, whose
exact value is `gemini-late-cpu-provenance\0`. Every property is required once.
Unknown, duplicate, `running-*`, malformed, zero-digest, or dynamic properties
fail closed. Property traversal order is irrelevant; the ordered property list
is retained only so duplicates cannot disappear into a map.

## Identity domains and record serialization

All domains begin with `gemini-a41-runtime-binding-v1\0`:

```text
SHA256(prefix || "ikconfig\0" || be64(length) || exact gzip bytes)
SHA256(prefix || "gnu-build-id\0" || be32(20) || exact build-ID bytes)
SHA256(prefix || "cmdline\0" || be64(length) || exact bytes without final NUL)
```

The record identity excludes itself and hashes:

```text
prefix || "record\0" ||
be32(1) ||
be16(profile_length) || profile_bytes ||
be32(2) || be32(8) || be32(9) ||
be32(2) || be64(0x200) || be64(0x201) ||
the nine 32-byte identity/provenance fields in declared record order
```

The independent frozen vector is 384 bytes with identity
`acef213ee86902f149a0ad6efbbc706905538a5d1ed411182ae8ec9a1d71e078`.
Raw digest bytes become `u64[4]` identities by big-endian numerical decode;
native-endian copying is forbidden.

## Generic exact build-ID helper

Patch 0156 adds `build_id_parse_buf_exact()` without changing the legacy
parser. It scans the complete bounded note buffer and requires exactly one GNU
type-3 note, an exact caller-selected descriptor length from 1 through 20, and
a nonzero descriptor. It rejects malformed arithmetic, truncated padding,
trailing bytes, duplicates, a wrong length, and an all-zero ID. Output is
zeroed on every failure and staged before output clearing so an output buffer
may safely overlap the input.

The accompanying KUnit source has nine cases for neighbors, short valid IDs,
rejected candidates, truncation, 32-bit overflow, unaligned input, invalid
arguments, and success/failure aliasing. This experiment reviews that source
and wiring; it does not build or execute KUnit.

## Running IKCONFIG producer

The architecture producer hashes exact bytes between `kernel_config_data` and
`kernel_config_data_end`. The range must be nonempty, ordered, and no larger
than 4 MiB. It does not substitute a raw `.config` digest. The expected record
and running core independently supply the two halves.

## Running GNU build-ID producer

The producer parses the in-memory `__start_notes..__stop_notes` range, bounded
to 64 KiB, with the exact helper. It requires one nonzero 20-byte ID and hashes
that ID in its own domain. This is linked-image attribution with the collision
strength of the underlying SHA-1 build ID, not a measurement of mutable live
text.

## Running forced-command-line producer

The profile selects a producer that depends on `CMDLINE_FORCE`. The producer
requires nonempty `saved_command_line`, an exact length equal to compiled
`CONFIG_CMDLINE`, and byte equality including the stored terminal NUL. It then
hashes the bytes excluding that NUL. Whitespace, ordering, truncation, or
bootconfig drift is a mismatch.

## Atomic collection and failure behavior

Expected parsing and all running derivations write only a zero-initialized
stack candidate. The private global identity is assigned once, after all
operations succeed and the three equality checks are complete. A failure
leaves the global object all-zero and marks collection FAILED. No profile sees
a writable pointer to either private object.

## Seal transition and SEALED_IDENTITY semantics

A FAILED collection plus all-zero private identity adds
`ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING` and seals empty. A VERIFIED, structurally
complete identity copies only its six-field binding into the private evidence
record and seals identity. Anything else faults.

`SEALED_IDENTITY` means the running kernel matches three independently
expected identities. It does not count as `SEALED_RUNTIME`, does not publish a
target observation, and cannot by itself make a production plan or READY token.

## Profile cross-binding and binding-only overlay

After the profile supplies expected-only source inputs, the core independently
checks the sealed record's profile ID, ordered configuration-input identity,
CPUs 8 and 9, MPIDRs `0x200` and `0x201`, registered target mask, nonzero record
identity, and complete identity binding. Only then may it copy the binding to
the draft and clear only `ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING`.

The selected configuration-input identity is
`4dca4e50ab039fbc60593e86d20d02e74e257dc6b5bb1afa94b38be6295b5203`.
No target identity, target capability, policy, system evidence, or evidence
identity is overlaid.

## Fixture and production separation

The selected ABI-7 fragment explicitly disables fixture evidence. The retained
fixture code still declares origin FIXTURE and is usable only by the pure
source evaluator. A fixture never receives the runtime binding overlay and
cannot claim architecture runtime authority.

## Current fail-closed reachability

Even a verified identity leaves target evidence, capability inventory,
effects, plan validation, and commit blockers. The MT6797 preparation and plan
validator return `-EAGAIN`, the core adds COMMIT_PATH, the architecture commit
panics if reached, patch 0092 keeps CPU boot at `-EAGAIN`, CPU disable remains
false, and the selected command line retains `maxcpus=8`.

## Remaining blockers

- CPU8/CPU9-local register, cache, GIC, hyp, firmware, ASID, granule, and VA evidence.
- A bounded evidence-only target transaction and verified OFF receipts.
- Complete system/nonlocal capability and HWCAP evaluation.
- Canonical evidence and plan identities.
- Architecture-owned capability/effect mutation and post-commit verification.
- READY consumers and normal late-CPU revalidation.
- A Buildbox build, package record emission, validated container, deployment,
  and attributable runtime evidence after source gates allow those actions.

No item here authorizes a build or device operation.

## Rejected shortcuts

- Treating expected DT values as running observations.
- Requiring DT property order or allowing duplicate properties to collapse.
- Accepting a dynamic property, unit-address alias, child node, or second compatible node.
- Hashing raw `.config` in place of embedded IKCONFIG.
- Using the legacy first-match build-ID parser.
- Copying digest bytes into native-endian words.
- Publishing any partially populated identity object.
- Treating `SEALED_IDENTITY` as target runtime evidence.
- Clearing blockers other than RUNTIME_BINDING during identity overlay.
- Letting a fixture, build result, userspace report, or CPU0 value substitute
  for CPU8/CPU9-local evidence.
- Relaxing the commit, CPU boot, disable, or `maxcpus=8` gates.
