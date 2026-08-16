# Experiment: pre-ramoops four-stage retained ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-16-mainline-pre-ramoops-ledger` |
| Status | single device attempt complete; no stage retained |
| Subsystem | arm64 early boot, initcalls, pstore/ramoops |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-16 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline pre-transport localization |

## Question or hypothesis

How far does the exact current mainline kernel progress before its
pre-serviceability return to Gemian?

The prior exact post-ramoops candidate produced no retained record after a
confirmed cycle. That localizes the observation boundary before successful
ramoops registration, but it does not show whether Linux completed the arm64
reserved-memory scan or reached the early, core, or postcore initcall levels.

This experiment gives each boundary one independent record in existing crash
memory. It is not a DA921x provider, CPU, or serviceability experiment.

## Provenance and environment

- Kernel: pinned Linux 7.1.3 from `kernel/manifest.json`.
- Parent profile: `da921x-resource-only-provider-modules-control`.
- Experiment profile: `da921x-modules-pre-ramoops-ledger`.
- Patch: canonical `0280-pstore-add-Gemini-pre-ramoops-stage-ledger.patch`.
- Build backend: explicit Buildbox only; no native VM build is authorized.
- Boot path: retained LK Android-v0 container on inactive logical `boot2`.
- Recovery path: ordinary known-good Gemian boot and read-only pstore capture.
- Buildbox package: repository commit
  `ca56f0161f6d67900d0fc58719e9190e7d1bb4a3`, profile
  `da921x-modules-pre-ramoops-ledger`, release
  `7.1.3-gemini-preledger-a`.
- Raw Android-v0 candidate SHA-256:
  `00455398cf1ffa3f57ad5083322e5541b0a58dbdec9ff63883b1427990cff8c3`.
- Exact 16 MiB `boot2` image SHA-256:
  `ac849d9aca9454d5d6a29d25a67b5d27fcef94e16bb881f4d14db09d0d29d75f`.
- Live GPT resolved inactive `boot2` as `/dev/mmcblk0p30`. Its predecessor
  full-partition SHA-256 was
  `ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348`.

## Safety assessment

The candidate writes only four short records, one per 4 KiB dmesg zone, inside
the already reserved range `[0x44410000,0x444f0000)`. The selected zones are
the final four Gemian-compatible dmesg slots:

| Stage | Slot | Physical range |
| --- | ---: | --- |
| arm64 reserved-memory scan complete | 171 | `[0x444bb000,0x444bc000)` |
| early initcall | 172 | `[0x444bc000,0x444bd000)` |
| core initcall | 173 | `[0x444bd000,0x444be000)` |
| postcore initcall | 174 | `[0x444be000,0x444bf000)` |

The live known-good kernel exposed each selected header as exact signature
`DBGC`, start zero, size zero before design selection. Before its first write,
the runtime code requires the exact Gemini root compatible, exact ramoops DT
node address and size, `no-map`, memblock reservation, and all four empty
headers. It writes record data before committing the start and size fields,
reads the record back, and disarms every later stage on any failure. Normal
ramoops registration is skipped only in this isolated profile so it cannot
consume or clear the records.

The candidate performs no partition or filesystem access at runtime, no
regulator read or write, no I2C transfer, no CPU admission, no timer action,
and no reboot action. CPU8 and CPU9 remain closed. The guarded installer may
write only live-GPT-resolved inactive `boot2`, with full-partition readback,
and must shut Gemian down after success. It records the predecessor checksum
but makes no new backup; recovery relies on the verified project-wide backup
captured at project start.

On 2026-08-16 the owner explicitly approved proceeding with this bounded
reserved-RAM diagnostic after the four-slot design and write boundary were
stated. The exact response and scope are recorded in
`results/owner-authorization-20260816.txt`.

Stop on any target, power, header, reservation, package, container, or readback
mismatch. Visual screen state is not attributable evidence.

## Associated code

- `scripts/validate.py`: exact patch/profile/static safety validator.
- `scripts/test-validate.py`: negative mutation suite.
- `scripts/classify-pstore.py`: returned-Gemian four-slot classifier.
- `scripts/test-classify-pstore.py`: classifier fixtures and rejection tests.
- `scripts/build-candidate.sh`: source-pinned exact candidate builder.
- `scripts/test-candidate.py`: source-pinned independent package/container
  validator with structural negative mutations.
- `scripts/install-boot2.sh`: source-pinned live-GPT guarded `boot2` installer.
- Changed-cycle recovery uses the repository collector; capture review is
  recorded before the single physical boot.

## Procedure

1. Validate the exact patch, profile extension, record framing, slot map,
   fail-closed flow, normal-ramoops bypass, and prohibited-operation boundary.
2. Run the manifest invariant, shell/Python checks, patch review checks, and
   negative mutations.
3. Commit and push a clean exact input, then build only with
   `./scripts/build-kernel --backend buildbox` and fetch only its validated
   package.
4. Independently validate the package, resolved config, Image, DTB, and exact
   four records. Construct and validate one Android-v0 container using the
   pinned working initramfs and unchanged load contract.
5. Freeze the exact candidate hypothesis and decision map. Re-read the four
   live headers before deployment and require them still to be empty.
6. Pre-arm a changed-boot-cycle observer while known-good Gemian is reachable.
   Install only to live-GPT-resolved inactive `boot2`, verify the complete
   readback, and shut the device down.
7. Select `boot2` once. After automatic or manual return to Gemian, archive
   pstore immediately and classify the highest contiguous valid stage.

One device boot is planned. The exact artifact must not be repeated unchanged.

## Observations

The exact pushed commit built successfully on Buildbox. The fetched package
manifest, resolved config, Image, DTB, System.map, and embedded marker set all
validated. The official candidate and an independent exploratory construction
were byte-identical before the exploratory copy was discarded. All 32 LK
container gates passed and six structural corruptions were rejected.

Buildbox checkpatch review reported the deliberately absent synthetic-author
sign-off, seven style warnings, and one alignment check. The missing sign-off
is required for this explicitly non-submission experiment archive; the style
findings do not change the compiled operation and are recorded rather than
silently treated as an upstream-ready result. No native VM build ran.

Immediately before deployment preparation, known-good Gemian was reachable as
kernel `3.18.41+`, boot ID `2f308b03-2e2e-42a4-840a-03f43fd48014`. A read-only
12-byte `/dev/mem` read at each exact slot returned little-endian `DBGC`, start
zero, size zero. The first-write all-four-empty runtime precondition therefore
still matches the live state.

The guarded installer resolved inactive, unmounted logical `boot2`, recorded
the predecessor without a fresh backup, wrote the exact candidate, synced and
flushed it, and matched both the full-partition checksum and an independent
byte comparison. It then powered Gemian off and confirmed the target was
unreachable.

The pre-armed collector observed that disconnect, then a returned known-good
Gemian boot with a changed boot ID. Immediate pstore recovery exposed no
files. The exact classifier therefore returned `no-stage`, with no valid slot
and no highest valid slot. A bounded post-return `/dev/mem` follow-up found all
four headers reset or retained as `DBGC`, start zero, size zero, and found zero
exact ledger payloads in all four complete 4 KiB zones. A read-only
post-cycle checksum still matched the installed candidate.

## Analysis

The four independent slots avoid the circular-buffer problem in which a later
partial write can destroy an earlier completed boundary. Returned Gemian
accepts the ordinary ramoops dmesg framing and can expose every completed slot.
USB remains useful only as secondary live evidence because it depends on much
later initramfs and gadget setup.

The post-return raw-zone check rules out a classifier-only or pstore-file-name
miss: no exact candidate payload remained in the selected zones. It does not
distinguish failure before the slot-171 hook from refusal by one of that hook's
exact DT, reservation, mapping, or header gates. Source re-audit confirms
arm64 calls `early_fixmap_init()` and `early_ioremap_init()` before
`arm64_memblock_init()`, so simple early-ioremap API initialization is not the
explanation. The exact artifact is stopped and must not be repeated.

Decision map:

- no valid stage: failure before completion of the reserved-memory checkpoint,
  or the exact runtime preconditions refused all writes;
- slot 171 only: after reserved-memory scan, before early initcall completion;
- slots 171--172: after early initcalls, before core initcall completion;
- slots 171--173: after core initcalls, before postcore initcall completion;
- slots 171--174: after the postcore checkpoint; move the next observation
  boundary later without repeating this artifact;
- any gap, duplicate, bad integrity field, or partial record: reject that
  record while retaining earlier contiguous valid stages.

## Conclusion

Offline validation, Buildbox construction, deployment, shutdown, changed-cycle
recovery, classification, raw-zone follow-up, and post-cycle image identity all
completed. No stage was retained. The attributable boundary is before
successful completion of the reserved-scan checkpoint or inside its
fail-closed preconditions; this result does not establish whether LK entered
the arm64 Image. No hardware-support or DA921x provider claim exists.

## Follow-up

Do not repeat this candidate. The ordered project path and the next lower
observation-boundary audit remain in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
