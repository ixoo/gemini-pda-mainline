# Experiment: earliest post-ramoops checkpoint

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-mainline-post-ramoops-checkpoint` |
| Status | exact candidate validated; deployment pending |
| Subsystem | pstore/ramoops, early boot serviceability, DA921x boundary |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-15 America/New_York |
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

## Analysis

This is the earliest durable observation point available without adding a
second storage backend or writing outside the already configured ramoops
console region. A retained marker proves kernel entry, DT-backed ramoops probe,
and pstore console registration before the later failure. An empty pstore after
another confirmed cycle moves the boundary before successful registration; it
does not prove the kernel never entered.

## Conclusion

Exact full boot2 SHA-256
`ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348`
is accepted for one installation and one selected boot. No runtime claim
exists yet. Provider setters, transition ownership, and CPU8/CPU9 admission
remain closed.

## Follow-up

Follow [`docs/ROADMAP.md`](../../docs/ROADMAP.md): commit and push the frozen
candidate/tooling record, install only to live-GPT logical boot2 with full
readback, shut Gemian down, and arm the one-hour collector before the one
owner-selected boot. Recover pstore immediately after any return to Gemian.
