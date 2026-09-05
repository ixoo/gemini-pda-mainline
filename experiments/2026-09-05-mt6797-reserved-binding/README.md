# Experiment: passive Linux reserved-memory image binding

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-05-mt6797-reserved-binding` |
| Status | Completed offline proposal; kernel compilation pending integration |
| Subsystem | MT6797 connectivity firmware image ownership |
| Device variant | Gemini PDA target; no device accessed |
| Date | 2026-09-05 |
| Investigator | Codex-assisted implementation; non-certifying archive |
| Tracking | [Roadmap](../../docs/ROADMAP.md) |

## Question and provenance

Can the existing private image owner retain and revalidate a real Linux OF
reserved-memory descriptor without pretending that a descriptor grants hardware
ownership or access?

This extends the [immutable image binding](../2026-09-05-mt6797-image-binding/README.md)
in place. The exact parent, source hashes, unchanged parser/plan dependencies,
and regression fixtures are pinned in [inputs.json](inputs.json).
[public-sources.json](public-sources.json) identifies the upstream Linux API
sources at commit `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`.
[proposal.json](proposal.json) records the two-file kernel delta and future
compilation acceptance checks. No new registry, parser or build object is added.
No manifest, configuration, canonical series, or DT node changes occur here.

## Safety and contract

All operations are passive software operations. There is no mapping, physical
copy, region initialization callback, DMA setup, SMC, remap, MPU change, power
operation, registration, or device access. `begin` still returns an error on every
path. A successful descriptor or prevalidation call is not permission to start
firmware or access memory. This proposal admits no device boot.

The caller supplies a device and an explicit `memory-region` index. Binding
requires an idle existing owner. The descriptor retains device, consumer-node,
and target-node references; the boot `reserved_mem` pointer is borrowed. Linux's
lookup matches a boot record by node basename. The implementation corroborates
its extent with both `of_reserved_mem_region_to_resource` and
`of_address_to_resource`, requires the target's direct parent to be the canonical
`/reserved-memory` node, and requires one static `reg` tuple. It refuses dynamic,
detached or unavailable relevant nodes; reusable/fixup regions; DMA pools; and
records with region-specific `ops` or `priv` requiring their actual owner adapter.
It never invokes `of_reserved_mem_device_init_by_idx`, which can call DMA setup.

The boot extent must be at least 1 MiB with a 1 MiB-aligned base. Its first 1 MiB
must fit the 32-bit addressing contract, and its full inclusive extent must not
wrap. A valid physical base of zero is accepted: no public descriptor contract
establishes zero as an invalid address. The first 512 KiB is described as WLAN;
the next 512 KiB is described as WMT. Any larger reservation tail is preserved
in the full extent but neither assigned nor mapped, even if it extends above
4 GiB. The tests cover zero, the final valid 32-bit window, and such a larger tail.

References keep objects alive; they do not keep a driver bound, freeze OF
properties, claim exclusive resource ownership, or exclude overlapping consumers.
The caller must stabilize the device/OF configuration during each operation.
Revalidation between operations checks the current device node, selected phandle,
boot-record identity, properties, and full range against the retained descriptor.
It does not detect an intermediate change reverted between calls and does not
provide a notifier or an atomic future access boundary. Exclusive ownership,
overlap exclusion and a stable provider resource contract remain unproven gates
for any future effectful implementation.

The descriptor shares the existing persistent no-wrap generation domain. Stale
queries publish zeroed output. Images or client claims block descriptor removal
and owner destruction. Passive image release permits subsequent removal; a
fault-held image retains the descriptor and its references. The test's teardown
of deliberately fault-held allocations is fixture disposal, not a production
recovery or quiescence API. An owner with no descriptor retains the existing
format-only prevalidation behavior.

## Code and reproduction

- [Source](src/image-binding.c) and [header](src/image-binding.h) extend the existing owner.
- [Tests](tests/test-reserved.c) and [API shims](tests/binding-test-compat.h) exercise the same implementation with modeled OF boundaries.
- [Generator](scripts/generate-patch.py), [verifier](scripts/verify.py), and [support](scripts/support.py) pin dependencies and clean managed scratch state on exit.
- [Patch](0005-wifi-mediatek-describe-reserved-memory.patch) is an internal format-patch archive, pending integrator placement in the canonical series.

Run from the repository root:

```sh
python3 experiments/2026-09-05-mt6797-reserved-binding/scripts/verify.py
```

The verifier reproduces and replays the patch, runs the unchanged 52 binding
checks and 32 concurrent claim rounds, then the reserved-memory cases with
AddressSanitizer and UndefinedBehaviorSanitizer. It downloads only bounded pinned
public Checkpatch text. No kernel source extraction or backend is used. The
required Checkpatch result is exactly the missing DCO error; no sign-off is
fabricated. This synthetic-author experiment is not submission-ready.

## Observations and conclusion

[validation.json](validation.json) records 37 reserved-memory check groups,
balanced device/node references, successful existing regressions, and no sanitizer
findings. Tests cover invalid extents, 23 API/property refusal cases, stale
phandles/records/ranges, allocation failure, generation exhaustion, and passive
versus fault-held release behavior. Patch reproduction and replay passed.
The repository gate passed: all 189 manifest profiles were audited, with the
37 grandfathered metadata records unchanged. Linux-only artifact-provenance
fixtures were skipped locally and remain mandatory in CI. No shell files changed.
Checkpatch reports zero warnings or style checks and the expected missing
`Signed-off-by` error.

Confirmed only for the tested host model: the owner can retain and revalidate
this descriptor while continuing to refuse active entry. The host shims do not
prove actual Linux reference behavior, linkage, boot resource correctness, or
hardware support. No kernel build or physical test ran in this work item. The
integrator owns the explicit Buildbox compilation and its source/object identity
checks. Ordered follow-up remains in the [roadmap](../../docs/ROADMAP.md).
