# Manual checkpoint live prefix-reason control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-manual-checkpoint-prefix-control` |
| Status | complete; exact runtime result attributed, candidate retired from repetition |
| Subsystem | pstore retained writer, live prefix-header attribution |
| Device variant | Gemini PDA x27, named project unit |
| Date(s) | 2026-08-21 to 2026-08-22 |
| Investigator(s) | Julien Etienne, Codex |
| Tracking issue | Gate 7 / CPU8 prerequisite localization |

## Question or hypothesis

Which first live header makes the unchanged four-slot prefix predicate refuse
the isolated manual checkpoint: a bad signature, nonzero start, nonzero size,
or a value that changes between the predicate and its bounded post-refusal
snapshot?

This is not a repeat of candidate `43e7f44e...eac3`. Canonical patch `0329`
adds one independent live observation that reports the first failing relative
slot index and its three header words. It does not change the predicate or
attempt to repair the header.

## Provenance and environment

- Runtime-proven foundation: manual checkpoint stage candidate
  `43e7f44eeef694ef876f7686ae03e2a779a118141e7f9efa060ccc1182c8eac3`
- Foundation result: exact serviceability pass with
  `stage=prefix-refused`, `first=0`, `second=0`, and zero writes
- Foundation mainline release: `7.1.3-gemini-checkpoint-stage`
- Foundation evidence commit: `55690096fe502064cfa25110bca6801ff5ee3d85`
- New profile: `da921x-manual-checkpoint-prefix-control`
- Expected release: `7.1.3-gemini-checkpoint-prefix`
- Build backend: Buildbox only from an exact clean pushed commit
- Boot path: guarded live-GPT logical boot2 only

Buildbox fetched exact clean commit `49f8e7f`, compiled release
`7.1.3-gemini-checkpoint-prefix`, and produced package
`linux-7.1.3-gemini-da921x-manual-checkpoint-prefix-control-b0fce1cc-f81f3888`.
The admitted raw Android-v0 candidate is `1d69e033...5e6ee`; its exact 16 MiB
boot2 image is `ced1f56f...f3901`.

## Safety assessment

Patch `0329` and its profile are default off. The profile inherits the exact
manual call count, at-most-two retained writes, fixed stage oracle, and every
clock, protected-transport, DA921x-action, owner, and CPU veto. The new code is
called only after the existing prefix predicate returns false. It reads the
rejected slot's 12-byte header with exactly three `readl()` operations and
records only those values, the relative slot index, checkpoint, and a fixed
reason string.

The patch does not modify `gemini_prb_slot_empty()`,
`gemini_prb_slot_exact()`, the loop order, write target, write protocol, or
return value. It adds no write, retry, clear, loop, timer, mapping, storage,
firmware or device-register MMIO action, I2C transaction, regulator-data
operation, clock or protected read, owner registration, CPU request, reset,
or power action. If the build and candidate gates pass, installation must use
the standing guarded boot2 write/readback/shutdown workflow and the exact
observer must be armed before one physical selection.

## Associated code

- `patches/v7.1.3/0329-pstore-report-Gemini-manual-checkpoint-prefix-reason.patch`:
  default-off post-refusal header snapshot and one new live marker
- `configs/gemini-manual-checkpoint-prefix-control.fragment`: exact profile
  delta and unique release
- `kernel/manifest.json`: named canonical-series Buildbox profile
- `scripts/validate.py`: patch, fragment, profile, contract, safety, and
  canonical-tip validator
- `scripts/test-validate.py`: negative source/configuration mutations
- `contract.json`: frozen hypothesis, result map, and safety scope
- `scripts/build-candidate.sh` and `scripts/test-candidate.sh`: exact two-way
  construction and independent package, DT, Image, symbol, and container gates
- `scripts/install-boot2.sh`: source-pinned live-GPT write/readback/shutdown
- `scripts/collect-runtime.sh`, `scripts/remote-runtime-probe.sh`,
  `scripts/validate-runtime.py`, and `scripts/validate-retained.py`: exact
  pre-armed reason capture, native Gemian return, and bounded recovery

## Procedure

1. Validate the patch, unchanged predicate, exactly three post-refusal reads,
   fixed reason inventory, default-off Kconfig gate, exact parent-profile
   derivation, canonical order, and every manifest-selected series.
2. Sign and push the clean definition commit to the exact project origin.
3. Build only with
   `KERNEL_PROFILE=da921x-manual-checkpoint-prefix-control ./scripts/build-kernel --backend buildbox`.
4. Fetch only the validated package, then pin and independently validate the
   exact Image, configuration, symbols, serviceability DT, Android-v0
   container, and negative mutations before admitting one candidate.
5. Guardedly install to inactive logical boot2, match the full readback, shut
   down, and arm the exact USB observer.
6. Select boot2 once. Require the exact candidate, release, serviceability,
   historical boolean marker, `prefix-refused` stage marker, and one unique
   prefix-reason marker before a native return to Gemian.

## Observations

The exact parent completed one physical selection with serviceability intact.
Sequence, exact DT/resource conversion, and `ioremap_wc()` passed. The first
call then reported `prefix-refused` before any retained write; the second call
was short-circuited. Changed-ID Gemian recovered the owned slots empty, but
that later cross-version view cannot reveal what the mainline late initcall
read.

The new patch parses as 14/0 Kconfig lines and 59/1 C lines. A read-only
Buildbox `git apply --check` passes against the exact prepared canonical source
through patch `0328`. Strict checkpatch has no warning; its sole error is the
intentionally absent synthetic-author sign-off.

The exact fragment/profile contract, four unified-diff hunk counts, five fixed
reasons, three-read ceiling, canonical-series invariant across all 110
profiles, eight series-invariant self-test mutations, and 16 unsafe source or
configuration mutations pass. See the
[prebuild receipt](results/prebuild-definition-20260821.txt).

The Buildbox package passes its full checksum inventory and binds the clean
pushed commit, profile, 24 configuration fragments, cross toolchain, Image,
configuration, symbols, DTBs, and release. No native VM build occurred. See
the [build receipt](results/build-49f8e7f.txt).

Two independent serviceability-DT derivations, two raw assemblies, and two
padding constructions are byte-identical. The exact candidate passes all 32
LK Android-v0 gates, 15 independent DT mutations, exact Image markers and
reason strings, configuration and symbols, 16 definition mutations, and the
offline runtime tools. Those tools accept four header-consistent live reasons
while rejecting 32 unsafe live mutations and eight retained mutations. See the
[candidate receipt](results/candidate-1d69e033.txt).

Guarded deployment from known-good Gemian resolved logical boot2 as
`/dev/mmcblk0p30` while root remained `/dev/mmcblk0p29`. Slots 171 through 174
were exact empty records before the write. The installer recorded predecessor
`43e7f44e...eac3`, used no fresh backup, wrote exact padded candidate
`ced1f56f...f3901`, matched that value across the full 16 MiB readback, and
confirmed clean shutdown without an automatic reboot. See the
[deployment receipt](results/deployment-20260822.txt).

The pre-armed observer's first interface wait saw an early USB topology change
but timed out before the exact gadget became ready. That non-attributable wait
is retained privately as timing evidence. When the exact interface later
appeared, the unchanged collector captured the same qualifying mainline boot;
this was not another candidate build or a repeated physical selection.

Exact release `7.1.3-gemini-checkpoint-prefix`, boot image identity, USB/netcat,
keyboard, one DA921x client, and CPUs 0--7 all passed; CPUs 8--9 remained
offline. The same-value attribute, clock backend, BigiDVFS backend, and
protected-readback device remained absent. All three expected markers appeared
once. The live result was `first=0 second=0 retained_writes=0`,
`stage=prefix-refused`, and
`cp=0 slot=0 why=bad-signature hdr=ffffffff/4294967295/4294967295 reads=3`.
Only after that exact classification did the collector send one native reboot.
Changed-ID Gemian returned with unchanged boot2, exact empty owned slots 173
and 174, and no pstore file. See the
[runtime receipt](results/runtime-attempt-1-bad-signature-20260822.txt).

## Analysis

The parent stage result eliminates sequence, DT/resource, and a null mapping;
it did not prove that the returned virtual mapping reads the retained DRAM
contents correctly. Because `gemini_prb_prefix_valid()` walks relative slots 0
through 3 and returns on the first mismatch, the new snapshot attributes the
earliest rejected header without altering the decision. Its three all-ones
words are internally consistent with `bad-signature` but contradict both the
pre-deployment and changed-ID Gemian views of physical slot `0x444bb000`, which
read exact empty header `444247430000000000000000`.

The exact prepared 7.1.3 source explains a more specific boundary. Canonical
patch `0323` deliberately makes `ramoops_init()` return before driver
registration whenever the protected-readback ledger is enabled on Gemini.
There is therefore no already-owned ramoops mapping in this profile; the
isolated ledger creates only its parallel `ioremap_wc()` mapping. Upstream
`persistent_ram_buffer_map()` would instead select `persistent_ram_vmap()`
whenever `pfn_valid()` is true; the exact configuration uses
`CONFIG_SPARSEMEM_VMEMMAP=y`, and that path vmaps the PFNs with
`pgprot_writecombine(PAGE_KERNEL)`. Slot `0x444bb000` is ramoops dmesg record
171 inside the `0x44410000`/`0xe0000` reservation. The next discriminator must
compare those two mapping models without registering ramoops or writing the
reservation. This is a source-backed inference, not yet a claim that either
mapping is universally wrong on the hardware.

The snapshot is deliberately after the existing predicate. If all three words
appear valid despite the refusal, `unstable-or-other` identifies a changed or
otherwise non-reproduced read rather than silently claiming an empty header.

## Conclusion

Exact candidate `ced1f56f...f3901` completed one guarded boot2 deployment and
one physical selection. It passed identity and serviceability and attributed
the unchanged prefix refusal to an all-ones read from relative slot zero. That
result rejects a stale/nonempty-record explanation and localizes the next work
to the ledger's ramoops-registration skip and parallel-map boundary. It does
not validate a retained write or change hardware support. CPU8 and CPU9 remain
closed, and this exact candidate must not be repeated.

## Follow-up

Use the ordered work in [the roadmap](../../docs/ROADMAP.md). The immediate
successor must be a default-off, read-only mapping-model discriminator with no
ramoops registration, retained write, clock action, protected transport,
transition-owner registration, or CPU request. Do not change the prefix policy
or proceed to clock-node population until mainline can attribute the empty
header through the mapping model that ramoops would use.
