# A41 partial fail-closed design record

## Claim boundary

`implementation_state=PARTIAL_FAIL_CLOSED` and `a41_complete=no` are normative
for this experiment. Patches
[0148](../../patches/v7.1.3/0148-arm64-add-a-fail-closed-late-CPU-profile-lifecycle.patch)
and [0149](../../patches/v7.1.3/0149-arm64-mediatek-register-blocked-MT6797-A72-profile.patch)
supply a generic lifecycle,
attestation schema, and an isolated MT6797 registration/profile description.
They do not supply the canonical arm64 capability inventory, a production
capability commit, late-CPU alternatives/vector installation, HWCAP
reconciliation, or a CPU_ON path.

The selected profile therefore has one permitted production outcome: BLOCKED.
The generic lifecycle's READY state exists as an interface for a future complete
profile, but is unreachable for this MT6797 profile.

## Source-level reachability argument

The fail-closed chain is:

1. Selecting the named manifest profile alone enables the MT6797 A41 Kconfig
   option; the repository default profile remains unchanged.
2. CPU0 activates the selected profile independently of whether either custom
   CPU8/9 operation is discovered. The framework treats missing, duplicate,
   inconsistent, or invalid registration as a blocker rather than “no profile”.
3. MT6797 preparation records the exact plan and installs every mandatory
   unresolved-proof blocker. Configuration and source identity stay mandatory
   until exact current proof exists; a topology mismatch adds its own blocker.
4. Preparation returns `-EAGAIN`. The framework publishes BLOCKED and returns
   before PREPARED.
5. System and user finalization return immediately for BLOCKED. Any callback
   that changes blockers or immutable identity is rejected before a later
   state can be published.
6. The public attestation accessor returns `NULL` unless READY was published.

The planned capability set is exactly:

- `ARM64_SPECTRE_BHB`, with `ARM64_LATE_CPU_BHB_LOOP` and `k=8`;
- `ARM64_WORKAROUND_1742098`;
- `ARM64_WORKAROUND_SPECULATIVE_AT`.

Those are entries in `draft->required_local_caps`, not writes to live arm64
capability state. The validator rejects additions that invoke PSCI CPU_ON,
delegate to the normal PSCI boot function, change live capability/HWCAP/BHB
state, apply alternatives, or install vectors.

## Existing veto contract

Patch [0092](../../patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch)
remains earlier in the selected series. Its MT6797 CPU operation
must continue to return `-EAGAIN` without calling the normal PSCI boot path, and
its hotplug predicate must continue to return `false`. Patch `0149` may attach
the profile but may not alter either function. Sequential application to the
pinned source baseline and inspection of the applied result prove this
contract.

The profile lifecycle runs at capability finalization, after ordinary secondary
bring-up. It is an attestation mechanism, not an early CPU admission gate.
Safety therefore still depends on the exact patch-`0092` veto and the inherited
`maxcpus=8` command line; neither may be relaxed by this milestone.

## Complete blocker model

[`results/blockers.tsv`](results/blockers.tsv) is exhaustive with respect to
the blocker definitions in the added arm64 header. Registration is guarded by
the framework and topology
is a conditional guard; configuration, source identity, and every remaining
proof are mandatory blockers in the selected MT6797 prepare callback. A source
definition without a matching table row, a table row without a source
definition, a missing mandatory blocker, or a blocker-clear operation is a
validation failure.

## Identity and lifetime model

`source_parent_identity` is the deterministic pre-A41 reject-gate source-state
digest, and `config_input_identity` is the repository's deterministic ordered
configuration-input digest. Both are non-circular inputs; neither is asserted
as current runtime proof. Expected target values and observed target values
occupy different fields, and each observation has explicit validity.
Immutable identity snapshots are checked across lifecycle callbacks. Init-only
profile pointers must not survive in permanent `__ro_after_init` storage.

The source-application check is independent of a generated kernel tree. It
reads the pinned baseline commit, verifies the exact preimage blobs, copies only
the touched files to a temporary directory, and applies `0148` then `0149` with
`git apply --check` before inspecting the result.

## Authorization boundary

The [validator](scripts/validate.py) and
[mutation suite](scripts/test_mutations.py) are offline source checks. Their
successful result sets none of the following: build authorization,
boot-candidate status,
deployment authorization, device-action authorization, CPU_ON authorization,
or hardware-support status.
