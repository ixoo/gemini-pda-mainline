# Experiment: earliest post-ramoops checkpoint

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-mainline-post-ramoops-checkpoint` |
| Status | one empty-pstore runtime result; exact candidate stopped |
| Subsystem | pstore/ramoops, early boot serviceability, DA921x boundary |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-15 to 2026-08-16 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline pre-transport localization |

## Question or hypothesis

Does the exact current mainline kernel reach successful ramoops console
registration before the repeated pre-transport return to Gemian?

The diagnostic adds one persistent-console line inside the successful ramoops
probe, immediately after `pstore_register()` returns and before the built-in
DA921x device initcall. It does not attempt to make USB serviceable and does
not repeat the stopped module-policy candidate unchanged.

## Provenance and environment

- Parent profile: `da921x-resource-only-provider-modules-control`.
- Parent runtime result: one exact pre-armed no-USB, empty-pstore failure at
  full boot2 SHA-256
  `044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff`.
- Linux source: 7.1.3, source SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

Patch `0279` is default-off. The isolated profile enables it only on the exact
module-policy/provider-only base and assigns a unique release. The marker is
guarded by the successful pstore registration path and the runtime console
flag. It appends one line to reserved persistent RAM. It does not access a
device partition, issue an I2C transaction, read or write a regulator, install
a setter, change a transition owner, schedule recovery, reboot the device, or
admit CPU8 or CPU9.

The patch is experiment-only and explicitly not submission-ready. Its
synthetic author identity is non-certifying and it has no DCO sign-off.

## Associated code

- [`../../patches/v7.1.3/0279-pstore-add-Gemini-post-ramoops-checkpoint.patch`](../../patches/v7.1.3/0279-pstore-add-Gemini-post-ramoops-checkpoint.patch):
  one default-off marker on successful ramoops registration.
- [`../../configs/gemini-post-ramoops-checkpoint.fragment`](../../configs/gemini-post-ramoops-checkpoint.fragment):
  isolated enable plus unique local version.
- [`scripts/validate.py`](scripts/validate.py): exact profile, patch, ordering,
  attribution, and safety validator.
- [`scripts/test-validate.py`](scripts/test-validate.py): eight unsafe or
  non-attributable mutations.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh) and
  [`scripts/test-candidate.py`](scripts/test-candidate.py): deterministic
  Android-v0/LK construction and independent structural validation.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): live-GPT boot2
  resolution, full readback, and clean-shutdown installer.
- [`scripts/remote-runtime-probe.sh`](scripts/remote-runtime-probe.sh),
  [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh), and
  [`scripts/validate-runtime.py`](scripts/validate-runtime.py): one-hour,
  read-only USB observation and frozen exact-identity classifier.
- [`results/initcall-placement-audit-20260815.txt`](results/initcall-placement-audit-20260815.txt):
  exact-source ordering audit.

## Procedure

1. Freeze the failed module-policy runtime result and stop that exact
   candidate.
2. Inspect the exact prepared Linux source read-only on Buildbox.
3. Place one marker immediately after successful `pstore_register()` in the
   ramoops probe and guard it by the console-storage flag.
4. Add the patch to the canonical series default-off and create one profile
   that exactly extends the failed parent with one final fragment.
5. Reject wrong-order, duplicate-marker, default-on, hardware-access,
   attribution, profile-drift, and unsafe-CPU mutations.
6. Commit and push a clean worktree, then build only on Buildbox.
7. Independently validate the fetched package and exact Android-v0/LK
   container before deciding whether one boot is justified.
8. Freeze the exact candidate, runtime decision map, no-write collector, and
   guarded installer; commit and push before device action.

## Observations

The exact source orders `ramoops_init` as postcore initcall level 2. Successful
`ramoops_probe` calls `pstore_register`, which registers the pstore console
before returning. The built-in DA921x driver expands through `module_init` and
the generic `__initcall` to device initcall level 6. The new marker is inside
the successful ramoops probe directly after `pstore_register`, so it is both
later than console registration and earlier than any DA921x probe. See the
[placement audit](results/initcall-placement-audit-20260815.txt).

The marker token is
`GEMINI_MAINLINE_POST_RAMOOPS_20260815_A`. Its record states
`checkpoint=ramoops-registered`, `pstore_console=active`, no storage or
regulator access, and closed CPU8/CPU9 admission. The patch does not introduce
any timer or reset path.

Buildbox completed exact pushed commit
`cac458c1cbd228390b94f2ae7154db34160adac2`. The fetched package passes its
complete manifest. It selects release `7.1.3-gemini-postram-a`, retains the
built-in read-only provider, leaves the observer and KUnit disabled, and
contains the unique checkpoint token exactly once. Its Gemini DTB is
byte-identical to the stopped module-policy control. The decompressed Image has
the same 11,943,944-byte size and 12,517,376-byte effective arm64 extent as
that control, but a different hash attributable to the checkpoint. See the
[Buildbox receipt](results/buildbox-20260815.txt).

Two independent assemblies produced the exact 6,881,280-byte raw container
`e16405f0a9061e98898f7fac5312033d56b1ab2aec162673fbebac564672e788`
and exact 16 MiB boot2 image
`ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348`.
The known serviceability ramdisk, Gemini DTB, LK addresses, page size, and
command line are unchanged. All 32 LK gates pass, independent padding agrees,
and the independent parser rejects six structural mutations. The runtime tool
suite accepts the exact positive record and rejects or distinguishes five
attribution, checkpoint, control, and CPU-safety mutations. See the
[offline review](results/offline-validation-20260815.txt).

The guarded installer resolved the sole live-GPT logical `boot2` as inactive,
unmounted, writable `/dev/mmcblk0p30`. It recorded the stopped module-policy
control as predecessor, made no fresh backup, wrote the exact checkpoint
candidate, synced and flushed it, and required both a matching full-partition
checksum and independent byte-for-byte readback. Gemian then powered off and
was confirmed unreachable. See the sanitized
[deployment receipt](results/deployment-20260815.txt).

The original pre-armed one-hour collector expired before the owner selected
boot2. An identical replacement started immediately after the boot report and
observed no exact Gemini USB interface before the reported automatic return.
The disconnect was confirmed across two probes. Ordinary Gemian returned on
`3.18.41+` with boot ID `2f308b03-2e2e-42a4-840a-03f43fd48014`, different
from the pre-deployment ordinary-Gemian boot ID. Immediate read-only recovery
found an empty pstore directory: no `console-ramoops`, exact marker, candidate
kernel identity, or initramfs entry record survived. Last-kmsg remained the
same generic 74-byte reset header seen in the preceding failures, and full
boot2 SHA-256 still matched the deployed candidate. See the
[runtime result](results/runtime-attempt-1-pre-ramoops-20260816.txt).

A bounded read-only audit then checked the reserved ramoops layout through
returned Gemian `/dev/mem` without saving payload contents. The final four
4 KiB dmesg zones, indices 171--174 at `[0x444bb000, 0x444bf000)`, each have
the expected `DBGC` signature and zero start/size. The exact live Gemian binary
and prior Candidate-L runtime evidence already establish that all 175 dmesg
zones share addresses and persistent-RAM headers across the two kernels. See
the [capture-method review](results/capture-method-review-20260816.txt).

## Analysis

This was the earliest durable observation point available through the normal
pstore console path. A retained marker would have proved kernel entry,
DT-backed ramoops probe, and pstore console registration before the later
failure. The confirmed empty-pstore cycle instead supplies no evidence of
successful registration and moves the localization boundary before that
checkpoint. It does not prove the kernel never entered, nor does it establish
whether LK handoff, decompression, early arm64 setup, DT unflattening,
postcore initcall dispatch, or ramoops probe failed.

## Conclusion

Exact full boot2 SHA-256
`ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348`
is stopped after its one selected boot and must not be repeated unchanged. The
only accepted runtime claim is the pre-successful-ramoops-registration
localization boundary. No provider or hardware-support claim exists. Provider
setters, transition ownership, and CPU8/CPU9 admission remain closed.

## Follow-up

Follow [`docs/ROADMAP.md`](../../docs/ROADMAP.md): design one isolated
pre-ramoops stage-ledger profile. Keep the pstore reservation but prevent the
normal ramoops driver from probing, then write four unique records only to the
four validated-empty final dmesg slots: after reserved-memory scan, at early
initcall, at core initcall, and at postcore initcall. Returned Gemian must
recover all completed slots read-only; USB remains secondary. The writer must
fail closed on any nonempty or structurally unexpected slot and remain CPU-,
regulator-, partition-, timer-, and reboot-inert. A device boot will require
explicit owner approval for these bounded reserved-RAM writes after offline
review.
