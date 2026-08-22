# Manual checkpoint ramoops mapping control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-22-mainline-manual-checkpoint-map-control` |
| Status | complete; exact runtime pass, both mainline mapping views matched all ones |
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
- Build commit: `0ada85aab04a3ebaaa4275fad235016292774946`
- Build backend: Buildbox only; no native VM build
- Package: `linux-7.1.3-gemini-da921x-manual-checkpoint-map-control-ccfe6c0b-526176f2`
- Admitted padded candidate: `dd513384...693b5b`, exactly 16 MiB
- Boot path: guarded live-GPT logical boot2 only

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
- `scripts/build-serviceability-dtb.sh`: source-pinned, two-construction DT
  derivation
- `scripts/build-candidate.sh` and `scripts/test-candidate.sh`: deterministic
  assembly and independent package/DT/container/symbol admission
- `scripts/install-boot2.sh`: guarded live-GPT write, readback, and shutdown
- `scripts/collect-runtime.sh`, `scripts/remote-runtime-probe.sh`, and the
  runtime validators: pre-armed exact live oracle and bounded changed-ID
  recovery

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

Buildbox fetched the exact clean pushed definition commit and produced release
`7.1.3-gemini-checkpoint-map`. Its complete package inventory, provenance,
configuration, Image compression, and symbols passed. See the
[Buildbox receipt](results/build-0ada85a.txt).

Two independent serviceability-DT constructions, raw assemblies, and padding
constructions are byte-identical. The raw Android-v0 image is 6,899,712 bytes
with SHA-256 `ecd021b2...299cae`; the exact 16 MiB boot2 form is
`dd513384...693b5b`. All 32 LK gates, 15 negative DT mutations, 17 definition
mutations, five header-consistent runtime outcomes, 26 unsafe runtime
mutations, and six unsafe retained-recovery mutations pass their expected
classification. See the [candidate receipt](results/candidate-ecd021b2.txt).

Guarded deployment resolved live-GPT logical boot2 as `/dev/mmcblk0p30` while
Gemian root remained `/dev/mmcblk0p29`. External power was online, all four
bounded retained headers were exact empty, the predecessor was
`ced1f56f...f3901`, and no fresh backup was created under the standing project
recovery policy. The write, sync, flush, and full-partition readback all
produced exact `dd513384...693b5b`; the Gemini then shut down and remained
unreachable. See the [deployment receipt](results/deployment-20260822.txt).

The one observer-armed selection booted exact release
`7.1.3-gemini-checkpoint-map` and padded candidate `dd513384...693b5b`. USB,
keyboard, DA921x presence, CPU0--7, and all safety closures passed. The fixed
stage was `map-control-observed`; the prefix marker was absent; and the map
marker reported `why=views-match-other`. Both the ramoops-model and parallel
views returned `ffffffff/4294967295/4294967295` after exactly three reads each,
with zero retained writes. Only after exact classification did the observer
request a native reboot. Changed-ID Gemian returned with unchanged boot2,
empty retained slots, and empty pstore. See the
[runtime receipt](results/runtime-attempt-1-views-match-other-20260822.txt).

## Analysis

`ramoops_init()` being skipped explains the absence of pstore files and proves
that the parent tested only its parallel mapper. It does not by itself explain
why that mapper returned all ones. The new control isolates only the remaining
mapping-model variable while keeping the physical address, header width,
runtime phase, DT, and serviceability base fixed.

The observed `views-match-other` result rejects a difference between
`ioremap_wc()` and the exact persistent-RAM vmap model: both mainline views
read the same all-ones header. Replacing only the parallel mapper would preserve
the observed value and is therefore not justified. Gemian read the same
physical header as exact empty before and after the mainline boot, so the
remaining discriminator is shared by both mainline views versus Gemian's
mapping/boot phase, or by a content transition around the OS handoffs. The
result does not establish which of those two explanations is causal.

## Conclusion

The exact read-only mapping-control candidate completed its one selection and
positively rejected mapping-model substitution as the next fix. It makes no
new hardware-support claim. CPU8 and CPU9 remain closed.

## Follow-up

Audit the exact arm64 `/dev/mem` page-protection path used by Gemian and every
mainline owner or initialization path that can change reservation
`0x44410000..0x444c0000` before the manual checkpoint. Select another boot only
if one read-only same-boot observation can distinguish a mapping-contract
difference from a boot-phase content transition. Do not substitute the mapper,
register ramoops, restore the writer, populate clock nodes, or open any CPU
request before that audit.
