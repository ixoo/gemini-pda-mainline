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
exercise 14 candidate/container cases and 24 collector cases in both normal and
optimized Python modes.

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

The repair was committed and pushed as
`03a6c69c45cbf0e114244b774ab40c80c10ea8f7`. From that exact clean
`origin/main`, the following construction was run with `<repository>` set to
this checkout and `<foundation-repository>` set to the retained private source
checkout:

```text
python3 <repository>/experiments/2026-09-06-mt6797-consys-passive-boot/scripts/build-candidate.py \
  --package <repository>/artifacts/buildbox/f9981eaf63381a558f77be251da4c2320cb4321b/linux-7.1.3-gemini-7c43a80cce28a15dc70306e3b8c225b537f1589eec4ac7411a46d422d705401c \
  --foundation-initramfs <foundation-repository>/artifacts/mt6797-pwrap-reset-serviceability/candidate-mt6797-pwrap-reset-305230b1/gemini-pwrap-reset-serviceability-initramfs.img \
  --userspace <repository>/artifacts/buildbox/e9c028005b88ef8536ecb58c095e8d172253fa12/userspace-dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60 \
  --credentials <repository>/artifacts/credentials/a53-auth \
  --serviceability-dtb <repository>/artifacts/toprgu/candidates/candidate-22edf533734ac52e56f3291c90264359fec2eaccc79cd68acf28b20d9cb216e8/board.dtb
```

The builder ran its independent validator automatically. The same validator
then passed explicitly in normal and optimized Python modes against:

```text
candidate=a487c5b33d100e75271d56b02535cb2b31f951d745090a54e5ee1287af4c800d
input_id=499e71920d71129b964754e4b9af6b15d5f9e18b383e584725eae241e56c08be
initramfs_sha256=184915b7a678657be41f8f116bc5403c501009e0f740aadaa8c797d81e73119d
raw_sha256=1051ddd45bc70e1fb58e6a70fc256aedb3a755930f59731bf0ae62f781f6e1fb
padded_sha256=a487c5b33d100e75271d56b02535cb2b31f951d745090a54e5ee1287af4c800d
raw_size=8853504 padded_size=16777216
```

Independent runtime review rejected this second candidate because its composed
`/init` retained the parent TOPRGU `uname -r` gate and would hold before
`/bin/usb-auth &`. Its validator reproduced and accepted the same stale bytes.
The replacement archive sources now use the exact passive release/marker and
the validator scans every executable script for stale TOPRGU release/profile
identities, while proving that authenticated USB follows the exact passive
release gate. The collector pins are deliberately empty until the corrected
candidate is rebuilt and reviewed. Physical admission, installation and boot
selection remain false.

## Refusal-wrapper candidate accepted for installer preparation

The specialist-directed repair was committed and pushed as
`f69ca07ff60c706d9592ec8368f21f8b629b7d9b`. A clean replay of the exact
construction command produced:

```text
candidate=08fc061475b4bd6bc274bef6cb61c6e0a1cb8d786c5be197b79dba006bebb1c2
input_id=f77eb7ee3c8f4024124be09a2e81df489093b5298b821ca9dce04ac2c106d12c
initramfs_sha256=73acf4aa0f972a562c5166465cb205a9b0e4b9d273466c21223e374c4e436a1e
raw_sha256=cbeab20db5993ff6ae7b9a94cfc1ecd0348dd2537b109051484ebde2592674c5
padded_sha256=08fc061475b4bd6bc274bef6cb61c6e0a1cb8d786c5be197b79dba006bebb1c2
raw_size=8853504 padded_size=16777216
```

The builder's internal validator and explicit normal/optimized validation pass.
Independent newc inspection found zero stale executable identity hits,
`bin/x-record` absent, and `bin/reboot` equal to the input-bound passive source
with exactly one `exit 126` and no restart effect token. The candidate fixtures
pass 19 cases in both modes and collector fixtures pass 24; the collector pins
the exact candidate/input pair. Final specialist review accepted guarded
installer preparation at `2026-09-06T22:34:23Z`. The acceptance does not grant
device admission or establish hardware support. Physical admission,
installation and boot selection remain false.

## Guarded installer accepted

The deployment adapter source-pins parent installer
`8aef9f6ed975fac3f09d7e3c057a601a444be854efb0ea6de26035adf288388a`
and binds the accepted candidate to expected predecessor
`22edf533734ac52e56f3291c90264359fec2eaccc79cd68acf28b20d9cb216e8`.
The exact ignored derived installer is
`e0c8c9606f0d88093bde3802de03a2ac86f6f49dd8c4ea78bb92fc128f95fcd0`.

Normal and optimized installer fixtures pass seven cases each. Derivation
revalidated the candidate, package, DTB, initramfs, userspace and credential
public inputs, then passed Bash syntax and ShellCheck. Independent Sol review
rejected one nested-symlink output escape; the repaired path walk rejects every
intermediate symlink/traversal and confines new outputs to the real private
passive-artifact root. Re-review accepted the packet at
`2026-09-06T22:45:23Z`.

The derived installer preserves the exact live-GPT, inactive/unmounted/non-swap
target, size, writable-state, power, predecessor, single-write, flush and full
readback gates. It skips an already matching partition and otherwise requests
clean shutdown after verified evidence with `reboot=no`. Standing authorization
admits that guarded `boot2` installation; it does not admit automatic reboot or
physical boot selection. No device action has yet occurred in this record.

## Specialist-rejected corrected candidate

The runtime-identity repair was committed and pushed as
`67423ca0602124e05578d74d954b566b48ad9aab`. The same exact construction
command above was replayed from that clean `origin/main`; the builder's internal
validator and explicit normal/optimized invocations passed.

```text
candidate=159f7801657d36e10d4bb06cce089c46ba13dbcd03e34dcc99a4aa42c6ab1a08
input_id=2177a3d07cdcede79477a9c760cc3915c81305545a393b28dd8f368a8154262f
initramfs_sha256=94d61fb3469f44588983781ca084733005c2b095b6bd53af1607b967b261c567
raw_sha256=ab3cb8fc828c1aa1b955e5cc7315332ac487dc6d5e35b616cc01ac55bbb39434
padded_sha256=159f7801657d36e10d4bb06cce089c46ba13dbcd03e34dcc99a4aa42c6ab1a08
raw_size=8853504 padded_size=16777216
```

The extracted `/init` contains exactly one
`uname -r = 7.1.3-gemini-consys-passive` gate before `/bin/usb-auth &`, and
both `/init` and `/bin/reboot` carry the passive candidate, input and marker
identities. Fixtures reject the prior archive and injected stale TOPRGU text in
any executable script. The collector pins the corrected candidate/input pair.
Specialist review rejected the packet after independently finding TOPRGU text
in `bin/console-status` and `bin/admin-shell`, plus the historical restart
marker in `bin/x-record`. The replacement sources use passive-only text,
`bin/x-record` is removed, and `/bin/reboot` becomes an exact `exit 126`
refusal stub rather than an effectful retained wrapper. The collector pins are
empty pending a newly built candidate. Physical admission, installation and
boot selection remain false.
