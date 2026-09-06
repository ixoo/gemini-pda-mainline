# Session handoff

Corrected review-ready UTC: 2026-09-06T21:01:27Z.

Frozen parent: `5ff87b372419e506a92a052db22da0dcfa13cb8b`. Frozen Linux 7.1.3
source SHA-256:
`be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
Parent profile: `mt6797-toprgu-minimal-restart`.

The implementation is intentionally private and effect-free. Validation is
complete before provider publication; the client sees only a private opaque
generation-bound handle. Release is generation-checked and decrements only
the passive provider reference acquired by a never-active binding.

The integration-owned fragment was verified to select
`CONFIG_MTK_MT6797_CONSYS_PASSIVE_BOOT=y` and retain its unique
`CONFIG_LOCALVERSION="-gemini-consys-passive"`; its current SHA-256 is pinned
in `validation.json`.

Repair 1 corrected OF iterator ownership: duplicate lookup now receives an
independent `of_node_get(node)` reference, which the consuming iterator drops,
while the caller retains and drops its original node reference once. The host
fixture rejects the old direct-`node` iterator pattern.

Focused fixtures passed in both interpreter modes with 49 cases each. The
patch parses as a format-patch (`git apply --stat`) and the worktree diff is
whitespace-clean. `./scripts/check-repository` passed its repository,
publication, profile-series, workflow and privacy gates; it skipped only the
documented Linux-only provenance/package checks. The exact patch SHA-256 is
recorded in `validation.json`; the fixture SHA-256 is recorded there as well.

Buildbox repair 1 moved `linux/types.h` before the byte-order helper header
after the compiler proved that the latter does not supply the kernel scalar
types it consumes. Buildbox repair 2 then exposed both a direct generic-header
layering error and a truncated new-file hunk that omitted the initcall. Astra
escalation selected the architecture byte-order wrapper, required the final
initcall to remain inside the hunk, and identified an uninitialized missing-
property length. The focused fixture now rejects all three defects.
Sol integration review accepted the complete repair at
`2026-09-06T21:26:57Z`, including exact diffstat, applied postimage identity,
normal/optimized mutation refusals and managed-parent application.

Independent Sol review accepted the repaired handoff at
`2026-09-06T21:03:32Z`. It verified the patch against the exact managed parent,
including a clean application, Kconfig symbol correspondence and strict
Checkpatch with zero errors, four non-blocking warnings and three style checks.

Buildbox subsequently passed the exact integrated profile at pushed revision
`f9981eaf63381a558f77be251da4c2320cb4321b`. It resolved release
`7.1.3-gemini-consys-passive`, compiled the observer into the linked kernel and
validated package inventory
`7c43a80cce28a15dc70306e3b8c225b537f1589eec4ac7411a46d422d705401c`.
The package is fetched below ignored artifacts. No device, firmware, private
capture, candidate or boot slot was touched; physical readiness is still false.

## Rejected candidate/collector draft

Candidate preparation was attempted offline with the exact Buildbox package,
the retained authenticated serviceability initramfs, the existing serviceability
DT transform output, and the reviewed credentials. The builder replayed the
DT/initramfs/Android-v0 assembly twice; both byte streams matched. The private
candidate is `candidate-d10528c86fbc1b0da5983a692d95b86562633882be7e1273bfa926627e8d9f0c`.

```text
release=7.1.3-gemini-consys-passive
profile=mt6797-consys-passive-boot
input_id=c395f6f55c7d71b85ad18946637479380209bfe327572d96fc3ed18cf2673358
initramfs_sha256=972d4d813539d98a60b1f7f6f38594d584fe560c619156760919b2001308b47f
raw_sha256=0ae8e6e27693d3241c35932ba664321e984cc1c165afa5e09d5c1af43b07525f
padded_sha256=d10528c86fbc1b0da5983a692d95b86562633882be7e1273bfa926627e8d9f0c
raw_size=8853504 padded_size=16777216
```

Independent review rejected that validator and collector despite confirming the
draft image bytes independently. A controlled raw-payload mutation passed the
draft validator after its self-reported hashes were recomputed, outputs were not
confined, and refusal coverage was incomplete. The draft candidate and its
`c395f6...` input identity are therefore not admissible. Repaired fixtures now
exercise 14 candidate/container cases and 23 collector cases in both normal and
optimized Python modes; a clean published construction and independent replay
remain required. Physical admission, installation and boot selection remain
false.

The future passive session expressly forbids invoking `/bin/reboot`, the
inherited TOPRGU wrapper, BusyBox `reboot`, `poweroff`, or any equivalent
restart/power command, manually or through a helper. The only admitted runtime
operation is one authenticated bounded read of the existing log capture,
followed by host-side classification. Any request to exercise the wrapper ends
the session without action.

The retained foundation input is:

```text
<foundation-repository>/artifacts/mt6797-pwrap-reset-serviceability/candidate-mt6797-pwrap-reset-305230b1/gemini-pwrap-reset-serviceability-initramfs.img
sha256=344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b
```

Exact construction and independent validation command lines will be frozen
here after the repaired tools are committed, pushed and rerun from a clean
`origin/main`. Candidate readiness remains false until that replay completes.
