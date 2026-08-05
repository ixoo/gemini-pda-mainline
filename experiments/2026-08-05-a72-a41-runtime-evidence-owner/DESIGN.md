# A41 ABI-6 runtime-evidence ownership design

## Scope

ABI 6 separates profile expectations from architecture-owned runtime
observations. This milestone implements only the ownership, seal, and rejection
boundary. It deliberately has no runtime producer and therefore seals an empty
record.

The exact claim is `PARTIAL_RUNTIME_EVIDENCE_OWNER_BOUNDARY`. It is not a
target collector, DT provenance parser, runtime identity verifier, complete
A41 evaluator, mutation transaction, or admission path.

## ABI-5 ownership defect

ABI 5 placed the runtime binding and target observations in the same writable
object passed to `profile->prepare()`. The core required origin RUNTIME, all
six valid identity fields, and equality of the three expected/running pairs,
but did not independently own either side. A profile could therefore act as a
paired oracle: write both members, label the result RUNTIME, and satisfy the
shape check without an independent producer.

ABI 6 keeps the evidence schema for fixture/evaluator compatibility but
changes write authority. The profile may provide expected-only production
input or an explicit FIXTURE. It may never author RUNTIME observations.

## Core-owned state

The arm64 core owns one private `late_runtime_evidence` object in `__initdata`.
No profile receives its address and ABI 6 exports no producer API.

| State | Meaning | Current reachability |
| --- | --- | --- |
| `OPEN` | Core record has not reached the seal point. | Initial state only. |
| `SEALED_EMPTY` | Seal completed with origin NONE; runtime-binding blocker is set. | The only successful seal result in ABI 6. |
| `SEALED_RUNTIME` | A core-owned record with a complete RUNTIME identity binding was sealed. Whole-record evidence completeness is not implemented yet. | Reserved for a later producer; unreachable now. |
| `FAULT` | Seal ordering, ABI, origin, or runtime-binding completeness was invalid. | Fail-closed error state. |

The initial object has ABI 6. Static zero initialization gives it origin NONE,
zero validity, zero identities, zero observations, and zero blocker while
OPEN. This is not evidence yet; it is only empty storage under core ownership.

The seal accepts only OPEN state before system capability finalization and
before `ARM64_ALWAYS_SYSTEM` is present. It accepts origin NONE or a complete
RUNTIME binding. Because ABI 6 has no writer, origin remains NONE. The seal
adds `ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING` and release-publishes
`SEALED_EMPTY`.

Preparation acquire-loads the state. Any OPEN or FAULT state blocks before
profile planning. This release/acquire pair orders every private evidence
field before any future overlay.

## Exact hook and ordering

The current arm64 boot order is:

```text
smp_cpus_done()
  hyp_mode_check()
  arm64_seal_late_cpu_runtime_evidence()
  arm64_prepare_late_cpu_profile()
  setup_system_features()
    setup_system_capabilities()
      arm64_commit_late_cpu_profile()
  arm64_verify_late_cpu_profile_system()
  setup_user_features()
  arm64_finalize_late_cpu_profile_user()
```

The seal is therefore post-hyp and pre-finalization. Hypervisor mode and KVM
layout/relocation decisions have been established by `hyp_mode_check()`, while
system capabilities, system alternatives, and user HWCAPs have not been
finalized. The seal itself additionally rejects a call after finalization or
after `ARM64_ALWAYS_SYSTEM` appears.

A future collector would have to run after the facts it consumes are stable
and before this seal. The current sequence intentionally contains no collector
call.

## Profile/core merge contract

The profile callback still writes a separate scratch object. The core applies
this decision table before planning:

| Profile result | Core state | Result |
| --- | --- | --- |
| origin RUNTIME, any contents | any sealed state | Immediate RUNTIME_BINDING block: `profile declared runtime evidence`. |
| origin other than NONE, FIXTURE, or RUNTIME | any sealed state | Immediate RUNTIME_BINDING block: `profile declared an invalid evidence origin`. |
| origin NONE with any binding, evidence identity, observed target identity, target capability, target policy, or system capability | any sealed state | Immediate RUNTIME_BINDING block: `profile supplied runtime observations`. |
| origin NONE and runtime fields empty | `SEALED_EMPTY` | Keep profile expectations, add runtime-binding blocker, continue only to blocked planning. |
| origin NONE and runtime fields empty | future `SEALED_RUNTIME` | Core may overlay its private runtime fields, then independently require a complete matching binding. |
| explicit FIXTURE | either accepted sealed state | Preserve the fixture for pure evaluation; never overlay or publish it as runtime. |
| any accepted profile result | OPEN or FAULT | Immediate RUNTIME_BINDING block: `runtime evidence was not sealed`. |

The profile may still provide `source_parent_identity`,
`config_input_identity`, target slot expectations, expected MPIDR/MIDR, and
its own conservative blockers. Those are expectations and source inputs, not
observations. The architecture core owns the final runtime origin, binding,
observed identities, target capability records, system evidence, canonical
evidence identity, and seal state.

## Current fail-closed result

The default production path has no core producer. It reaches SEALED_EMPTY,
then profile preparation supplies only expectations and returns `-EAGAIN`.
The core restores or retains RUNTIME_BINDING and always adds COMMIT_PATH.

The fixture profile still supplies origin FIXTURE and the exact synthetic
CPU8/CPU9 record. The pure classifier and typed-effect evaluator may calculate
the same scratch result as ABI 5, but the profile validator still returns
`-EAGAIN`; no plan identity is written and the fixture cannot become runtime
evidence.

Thus neither path can publish PLAN_FROZEN. The architecture commit remains
unimplemented, READY remains unreachable, `maxcpus=8` remains selected, and
the patch-0092 boot and disable vetoes remain unchanged.

## Future DT expected-identity record

The boot provenance record is a separate future contract. ABI 6 neither emits
nor parses it. Its purpose is to supply only the expected halves of three
identity pairs from a validated package; it must never supply a `running-*`
value or target-local register observation.

The candidate builder should emit exactly one node at
`/chosen/gemini-late-cpu-provenance` after the plain kernel Image is complete:

```dts
gemini-late-cpu-provenance {
        compatible = "planet,gemini-a72-runtime-binding-v1";
        schema-version = <1>;
        profile-id = "mt6797-a53-a72-a41-v6";
        target-cpus = <8 9>;
        target-mpidrs = /bits/ 64 <0x200 0x201>;

        expected-config-image-identity = [ /* 32 bytes */ ];
        expected-image-build-id-identity = [ /* 32 bytes */ ];
        expected-cmdline-identity = [ /* 32 bytes */ ];

        upstream-source-sha256 = [ /* 32 bytes */ ];
        patch-series-sha256 = [ /* 32 bytes */ ];
        config-inputs-sha256 = [ /* 32 bytes */ ];
        resolved-config-sha256 = [ /* 32 bytes */ ];
        package-image-sha256 = [ /* 32 bytes */ ];
        build-provenance-sha256 = [ /* 32 bytes */ ];
        record-identity = [ /* 32 bytes */ ];
};
```

All digest properties contain 32 raw bytes in digest order, not hexadecimal
text or native-endian words. The parser must require the exact path, one node,
one exact compatible string, exact profile, exact CPU/MPIDR ordering, exact
property lengths, nonzero digest values, and an allowlist containing no
`running-*` property. A duplicate node, unknown attestation property, malformed
length, reordered target, or changed profile must fail closed.

Use the domain prefix
`gemini-a41-runtime-binding-v1\0`. The three expected/runtime identities are:

```text
SHA256(prefix || "ikconfig\0" || be64(length) || exact IKCONFIG gzip bytes)
SHA256(prefix || "gnu-build-id\0" || be32(20) || exact 20-byte GNU build ID)
SHA256(prefix || "cmdline\0" || be64(length) || exact bytes without final NUL)
```

The configuration identity is the exact compressed IKCONFIG payload embedded
in the Image, not the separate raw `.config` SHA-256. The raw resolved-config
digest remains a provenance field. The linked-image identity is derived from
the GNU build-ID note; it is an attribution identifier, not a cryptographic
measurement of mutable live text and it retains the collision strength of its
underlying 20-byte SHA-1 build ID. The command line is byte-exact and order
sensitive. With `CONFIG_CMDLINE_FORCE=y`, the running producer must also prove
`saved_command_line` equals compiled `CONFIG_CMDLINE`.

Define `record-identity` as SHA-256 of this exact serialization, excluding the
`record-identity` property itself:

```text
prefix || "record\0" ||
be32(1) ||
be16(profile_length) || profile_bytes ||
be32(2) || be32(8) || be32(9) ||
be32(2) || be64(0x200) || be64(0x201) ||
the nine preceding 32-byte identity/provenance fields in DTS order
```

The record digest detects accidental field drift and gives external evidence a
stable cross-reference. It is not a signature or secure-boot trust anchor.

The plain package Image exists before this DT record, so its IKCONFIG,
build-ID, and full Image SHA can be embedded without circularity. The finished
DT, Android container, boot candidate, and full boot2 partition hashes must
remain external because embedding their own full hashes would be circular.

Before implementation, ABI field naming must explicitly map
`expected-config-image-identity` to the configuration pair or make a later ABI
rename; it must not silently pretend that the compressed IKCONFIG digest is
the raw resolved `.config` digest.

## Future core identity producers

At the same post-hyp/pre-finalization boundary, architecture code can
independently produce the running halves without userspace:

1. hash `kernel_config_data..kernel_config_data_end` with built-in scalar
   SHA-256;
2. parse the in-memory note range, require exactly one nonzero 20-byte GNU
   build ID, and hash it with the defined domain; and
3. hash exact `saved_command_line` bytes and enforce the forced-command-line
   policy.

Only core code may compare these values with the validated DT expectations and
populate binding origin RUNTIME plus the complete validity mask. It must stage
the result locally and publish the complete record atomically; any missing,
partial, zero, substituted, or mismatched value must publish no partial
runtime binding.

The full package Image, DT, container, boot candidate, and partition readback
hashes remain build/deployment evidence. Initramfs and userspace observations
such as `/proc/config.gz`, `/proc/cmdline`, `/proc/version`, boot ID, and pstore
occur after the A41 finalization boundary and are corroboration only.

## Future target-local collector

CPU8/CPU9-local registers cannot be authoritatively read by CPU0, and PSCI has
no remote register-read operation. A production record therefore requires
either a tightly quarantined collector executed by each target before Linux
admission or an independently trusted pre-Linux attestation with equivalent
binding and OFF proof.

A future Linux collector transaction must:

1. run only after boot/hyp/system requirements are frozen and before
   `arm64_seal_late_cpu_runtime_evidence()`;
2. bind one generation and request to exact logical CPUs 8 and 9 and expected
   MPIDRs `0x200` and `0x201`;
3. start one target at a time at a dedicated identity-mapped collector, never
   normal `secondary_entry` or `secondary_start_kernel`;
4. have the target record actual MPIDR, MIDR, REVIDR, conditional AArch64 and
   AArch32 ID registers, raw CTR and CLIDR, target EL, GIC SRE usability and
   ICC/ICH state, and target-local WA1/WA2/WA3 results with explicit validity
   and fault status;
5. publish through a release/acquire generation protocol, call `CPU_OFF`, and
   require bounded `AFFINITY_INFO` confirmation that the exact target is OFF;
6. have architecture code recompute derived CTR and capability/HWCAP outcomes,
   validate target mapping, combine core-owned current policy and system
   evidence, and only then form one canonical evidence identity; and
7. seal RUNTIME only after both independent target records and all three
   running identity producers are complete. A trap, timeout, partial record,
   stale generation, failed CPU_OFF, or remaining-on target must fault rather
   than seal runtime.

The transaction must not enter CPU hotplug, the scheduler, normal IRQ service,
per-CPU capability enablement, sanitized-register merging, generic secondary
callbacks, or online state. Profiles must never receive a writable pointer to
the collector record.

The standing A26/patch-0092 veto currently forbids every applicable CPU_ON
transaction. Calling PSCI directly to bypass that veto is not acceptable.
Therefore this collector is a design only until a separately reviewed policy
milestone authorizes one narrow evidence-only transaction or a trustworthy
firmware handoff is available.

## Remaining blockers

ABI 6 closes only producer ownership. It does not close:

- the missing DT parser, package-derived expected identities, and in-kernel
  running config/image/cmdline producers;
- actual CPU8 and CPU9 register, cache, GIC, hyp, firmware, ASID, granule, and
  active-VA evidence;
- a safe target-local collection transaction and exact OFF receipt;
- complete boot/nonlocal system-capability and per-target HWCAP evaluation;
- a canonical evidence identity and nonzero canonical plan identity;
- the architecture-owned capability/effect mutation implementation;
- post-commit system, alternatives, strict-capability, and user-HWCAP
  verification;
- A36/P17/P18 READY-token consumers and normal target revalidation;
- all existing CPU boot, disable, and `maxcpus=8` safety gates; and
- a Buildbox build, validated package/container, attributable boot, and
  deployment/readback evidence after source gates are actually closed.

No item in this design authorizes those later actions.

## Rejected shortcuts

- Allowing `profile->prepare()` to set origin RUNTIME.
- Treating SEALED_EMPTY as a partial success or clearing RUNTIME_BINDING.
- Copying expected DT values into running fields.
- Putting target register or firmware observations in DT.
- Treating a DT record digest as a signature or trust anchor.
- Calling PSCI behind the A26/patch-0092 veto.
- Using normal secondary boot, CPU hotplug, or scheduler admission to collect
  pre-admission evidence.
- Substituting CPU0/A53 registers or firmware responses for CPU8/CPU9.
- Accepting one target's evidence for both target slots.
- Encoding an unavailable or trapped register as a successful zero value.
- Treating build, initramfs, userspace, container, or partition evidence as a
  target-local pre-finalization observation.
- Making PLAN_FROZEN, COMMITTED, READY, or CPU admission reachable from a
  fixture or a partial runtime record.
