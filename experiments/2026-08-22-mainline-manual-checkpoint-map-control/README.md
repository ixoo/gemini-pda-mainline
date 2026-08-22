# Manual checkpoint ramoops mapping control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-22-mainline-manual-checkpoint-map-control` |
| Status | running; prebuild definition only, not compiled or admitted |
| Subsystem | pstore retained RAM, arm64 mapping-model attribution |
| Device variant | Gemini PDA x27, named project unit |
| Date(s) | 2026-08-22 |
| Investigator(s) | Julien Etienne, Codex |
| Tracking issue | Gate 7 / CPU8 prerequisite localization |

## Question or hypothesis

Does the mapping model used by upstream `persistent_ram_vmap()` read dmesg
record 171 at physical `0x444bb000` as the exact empty header while the
unchanged parallel `ioremap_wc()` view reads all ones?

The result distinguishes a mapping-model discrepancy from absent retained data
without registering ramoops, changing the existing prefix predicate, or
writing the reservation.

## Provenance and environment

- Runtime-proven foundation: manual checkpoint prefix-control evidence commit
  `c5d0be76bf1ac135c57d814e259971fa72dbd366`
- Foundation candidate: `ced1f56f...f3901`
- Foundation result: exact serviceability pass with relative slot zero reported
  as `ffffffff/4294967295/4294967295` through the parallel mapping
- Known-good preflight and changed-ID recovery: physical slot `0x444bb000`
  read exact empty header `444247430000000000000000`
- Parent profile: `da921x-manual-checkpoint-prefix-control`
- New profile: `da921x-manual-checkpoint-map-control`
- Expected release: `7.1.3-gemini-checkpoint-map`
- Build backend: Buildbox only from an exact clean pushed commit
- Boot path if admitted later: guarded live-GPT logical boot2 only

Exact prepared source audit found that canonical patch `0323` deliberately
makes `ramoops_init()` return before platform-driver registration whenever the
protected-readback ledger is enabled on Gemini. No ramoops zone is therefore
owned in the parent live boot. `persistent_ram_buffer_map()` nevertheless
defines the mapping model normal ramoops would use: on a valid PFN it calls
`persistent_ram_vmap()` with the selected memory type. The exact configuration
uses `CONFIG_SPARSEMEM_VMEMMAP=y`, and `mem-type = <0>` selects
`pgprot_writecombine(PAGE_KERNEL)` in that vmap path.

## Safety assessment

Canonical patch `0330` and its profile are default off. In this mode the first
manual checkpoint validates sequence and exact DT, creates the unchanged
parallel mapping, takes its three-word header snapshot, and then calls a
read-only helper that maps the same physical header through
`persistent_ram_vmap()`, takes three scalar reads, and unmaps it. The control
sets `stage=map-control-observed` and exits before
`gemini_prb_prefix_valid()` or `gemini_prb_write()`.

Normal ramoops registration remains skipped. The patch adds no retained write,
payload read, pstore record scan, storage access, firmware or device-register
MMIO, I2C transaction, regulator-data operation, clock or protected read,
transition-owner registration, CPU request, retry, timer, watchdog, reset, or
power action. Definition validation has no device access. A later candidate
must pass independent package, configuration, DT, container, and mutation gates
before the standing guarded boot2 workflow may install it.

## Associated code

- `patches/v7.1.3/0330-pstore-compare-Gemini-ramoops-mapping-models.patch`:
  default-off read-only two-view comparison
- `configs/gemini-manual-checkpoint-map-control.fragment`: exact profile delta
  and unique release
- `kernel/manifest.json`: named canonical-series Buildbox profile
- `contract.json`: frozen hypothesis, result map, and safety scope
- `scripts/validate.py`: exact patch, fragment, profile, contract, and safety
  validator
- `scripts/test-validate.py`: negative source and configuration mutations

## Procedure

1. Validate the exact four-file patch, default-off dependency, mapping helper,
   three reads per view, writer bypass, fixed result inventory, profile
   derivation, canonical tip, and all manifest-selected patch series.
2. Confirm read-only application and strict style against the prepared
   canonical 7.1.3 source through patch `0329`.
3. Sign and push the clean definition commit to the exact project origin.
4. Build only with
   `KERNEL_PROFILE=da921x-manual-checkpoint-map-control ./scripts/build-kernel --backend buildbox`.
5. Fetch only the validated package and independently prove the Image,
   configuration, symbols, serviceability DT, Android-v0 container, no-write
   branch, and runtime oracle before admitting one candidate.
6. If admitted, guardedly install to inactive logical boot2, match the full
   readback, shut down, and arm the exact observer before one physical
   selection.

## Observations

The parent completed one physical selection with exact identity and
serviceability. Its parallel mapping returned all ones for record 171, while
known-good Gemian read the physical header as exact empty before and after that
boot. No retained write occurred.

The follow-up source audit found the ledger-specific early return in
`ramoops_init()`, disproving the assumption that an already-owned ramoops
mapping existed. The new patch instead calls the exact internal vmap model
directly without constructing a persistent RAM zone or registering ramoops.

The patch applies read-only to the exact prepared source through `0329`.
Strict checkpatch reports zero warnings and zero checks; its sole error is the
intentionally absent synthetic-author sign-off. All 111 manifest profiles pass
the canonical-series invariant. See the
[prebuild definition receipt](results/prebuild-definition-20260822.txt).

## Analysis

`ramoops_init()` being skipped explains the absence of pstore files and proves
that the parent tested only its parallel mapper. It does not by itself explain
why that mapper returned all ones. The new control isolates only the remaining
mapping-model variable while keeping the physical address, header width,
runtime phase, DT, and serviceability base fixed.

An exact-empty vmap-model header paired with an all-ones parallel header would
justify replacing the ledger's mapper before any retained write. If both views
are empty, the earlier all-ones result was not stable across builds and the
writer still remains closed. Any other match, mismatch, or map failure stops at
read-only attribution.

## Conclusion

The read-only mapping-control definition is statically admissible for a
Buildbox build. It is not compiled, is not a boot candidate, and makes no new
hardware-support claim. CPU8 and CPU9 remain closed.

## Follow-up

Use the ordered work in [the roadmap](../../docs/ROADMAP.md). Build and
independently validate this exact definition before considering one physical
selection; do not register ramoops, restore the writer, populate clock nodes,
or open any CPU request in this discriminator.
