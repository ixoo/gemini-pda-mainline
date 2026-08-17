# Experiment: MT6797 LK SCP handoff node

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-16-mainline-scp-handoff-node` |
| Status | strict LK stop isolated; exact one-node DT candidate validated offline |
| Subsystem | Planet LK DT fixup, MT6797 SCP handoff, USB observation |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-16 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline serviceability prerequisite to CPU8 work |

## Question or hypothesis

Does the absent disabled `mediatek,scp` node explain why the current DT never
reaches the mainline USB observation path? Keep the exact stopped kernel,
initramfs, Android-v0 container policy, three USB observation properties, and
every other current-DT property unchanged. Add only the exact disabled SCP node
present in the runtime-proven Stage-27 DT.

In the pinned public MT6797 LK source, `platform_fdt_scp()` returns `1` when no
`mediatek,scp` node exists. `platform_atag_append()` propagates that value, and
the caller asserts and returns before the final Linux handoff. When the node
exists, LK updates only its `status` and returns success. The node can remain
disabled in the input and Linux will not probe it.

## Provenance and environment

- Exact stopped predecessor is the three-property USB-observation candidate,
  full boot2 SHA-256
  `fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87`.
- Exact current kernel package remains repository commit
  `98996fdfbf09f8de2a6b86e488defef22fcc7968`, release
  `7.1.3-gemini-entryled-a`.
- Exact current USB-observation DT SHA-256 is
  `e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331`.
- Runtime-proven Stage-27 DT SHA-256 is
  `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806`.
- Public Planet LK source-contract reference is exact commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
- No kernel compilation is needed. No native VM build is permitted or run.

## Safety assessment

The new node is input-disabled and describes existing SCP address and interrupt
resources only. Linux will not bind it. The candidate adds no register-data
write, regulator action, CPU admission, or storage access. USB stays
peripheral-only, xHCI stays disabled, and CPU8/9 remain offline.

Any installation remains limited to standing-policy logical `boot2` gates:
resolve the live GPT, require the sole inactive and unmounted 16 MiB target,
record but do not back up its predecessor, require stable power, write and
flush only the exact payload, verify a full readback, and shut down cleanly.

## Associated code

- `scripts/build-scp-handoff-dtb.sh`: source-pinned current USB DT derivation
  plus one exact disabled SCP node and fixed output identity.
- `scripts/build-candidate.sh`: source-pinned assembly with two independent raw
  images, two padding constructions, and a fixed complete manifest.
- `scripts/test-candidate.py`: independent DT, container, manifest, package,
  and negative-mutation validation.
- `scripts/install-boot2.sh`: exact-identity guarded boot2 deployment and clean
  shutdown wrapper.
- `results/strict-lk-scp-boundary-20260816.txt`: exact public LK call chain,
  remaining semantic partition, and candidate selection.
- `results/offline-candidate-validation-20260816.txt`: fixed candidate
  identities and completed independent gates.
- `results/predeployment-hypothesis-20260816.txt`: one-attempt evidence and
  decision map frozen before device deployment.

Generated candidates remain below the ignored `artifacts/` tree.

## Procedure

1. Decompile the stopped current USB DT and runtime-proven Stage-27 DT, then
   remove phandle-renumbering noise from the semantic partition.
2. Map each real remaining group to exact public LK or early-kernel consumers.
3. Select the strict missing-node LK failure before unrelated serviceability
   groups.
4. Derive the DT twice from exact inputs and require only one added node with
   four exact properties.
5. Assemble twice, pad twice, run all existing LK/container gates, and reject
   independent mutations before any deployment.
6. If every offline gate passes, publish exact identities, perform one guarded
   boot2 deployment, shut down, and pre-arm USB/preloader/Gemian observation.

## Observations

The stopped DT and Stage-27 DT differ in several real groups plus widespread
phandle renumbering. Keyboard/I2C5 and later DVFSP/nvmem ownership changes are
not loader prerequisites. CPU `clock-frequency` absence is logged and skipped.
`/chosen` already exists and accepts LK properties. Reserved-memory ranges are
identical. In contrast, the absent `mediatek,scp` node produces a nonzero return
that reaches an LK assert.

The exact derivation adding only the disabled SCP node produces DTB SHA-256
`53ceeaddcae13ff10ddc219441ac46a300324e5490e436626601f0d928c1558b`.
Its raw Android-v0 container SHA-256 is
`d13f110ad38e3a515d2f339619f32d529c76612543e89d3fe2df45689141c3a4`;
the exact 16 MiB boot2 payload is
`73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7`.
Two assemblies and two padding methods are byte-identical. All 32 LK gates,
the complete candidate manifest, four entry-ledger markers, exact SCP closure,
and six independent corruption tests pass.

## Analysis

This is a stronger boundary than a broad DT bisection: the source contract
contains a direct success/failure branch on precisely the missing node, and the
working DT contains the required node. A positive runtime would attribute the
repair to the LK SCP handoff contract. A negative remains useful because it
removes that strict stop while leaving all other current-DT differences intact.

## Conclusion

Confirmed offline: the current DT violates one strict public MT6797 LK input
contract that the runtime-proven Stage-27 DT satisfies, and the exact one-node
repair is a validated boot candidate. Hardware behavior remains untested.
CPU8 and CPU9 remain closed.

## Follow-up

Publish the exact candidate definition, then perform one guarded boot2 write,
clean shutdown, and pre-armed attempt. The ordered project action remains in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
