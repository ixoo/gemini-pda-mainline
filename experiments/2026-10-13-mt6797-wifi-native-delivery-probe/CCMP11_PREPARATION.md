# C11: group PN observation — consumed once

[Predeclared hypothesis and branches](GROUP_PN_SUCCESSOR.md): retain missing GTK
PN-availability scalars from existing acquisitions, with group delivery still
withheld. C10's finite PTK pass is consumed and is not repeated unchanged.
Guarded installation, full readback, clean shutdown and complete actual host
preparation passed. Owner physical boot2 selection subsequently started the [single C11 trial](CCMP11_RESULT.md).
The instructions below describe its preparation, not a new admission or retry.

## Source, Linux build and validated package

- Kernel input `774e08aa5570f96986acc1fd2a40afa0c226777d`, profile
  `mt6797-a53-wifi-ccmp-group-pn-observe`; 696 ordered patches, 28 fragments.
- [Proposal 0201](../../patches/proposals/0201-wifi-mt6797-observe-initial-GTK-PN-metadata.patch)
  SHA-256 `c14244306eeaab5b6749fb68dc039b312c920f5202d1a619f40d018d6dac4193`;
  bounded driver snapshot `70f1b9a3484139b35dfdb894cbbcb56f21b33218`, not a Linux revision.
- Series SHA-256 `c7a9e57cb42fd8a3d4040fe2cbb9d7e42aa12a949b3d4774e2ef06518f8beca8`.
  All 33 existing profile definitions remain unchanged.
- Standard `./scripts/build-kernel --backend buildbox`, clean pushed inputs,
  32 jobs, x86_64 cross-build, modules disabled. One kernel build completed;
  the earlier input stopped at a Kconfig help style warning before compilation.
- Validated/fetched inventory
  `8ef839effaaac15490201a619a0dc194a16400bd52ac085b2743b6d8462d3c02`,
  854 members and 123 DTBs.
- Image.gz SHA-256 `27faa867bd85c231882fcf3d994917cf1ab56f48c703f71f1f1e5edb9111415c`;
  config `f4edcd7890078912f0093c15f5393b64af4e80b00c1c96421f87bba970d400d6`;
  patchset `c412b9987a25a436f012aa03ad99162a33f15231ff0851989765af13bb40d9af`.
  Generated configuration equals C10 plus only `CCMP_GROUP_PN_OBSERVE=y`.

[Build validation](results/ccmp11-build-validation.json) records actual-source
Linux ASan/UBSan, 2716 allocation/bounds/PN-poison observations, unchanged PTK PN
rejection, reverse-patch recovery and complete option-off MAC parity. Strict
checkpatch has zero warnings/checks and one intentional missing truthful DCO
error for this synthetic, non-certifying internal archive. The build retains an
inherited unused-function warning in `kernel/cpu.c`; no new driver warning.
A build and host simulations do not establish firmware effects or Wi-Fi support.

## Real composition and bindings

The [compositor](build-ccmp-candidate-11.py) used the validated package and the
actual private C32 parent, with exact inventory/config/DT/RAM/container gates.
The [configuration oracle](tests/ccmp11-composition-test.py) passed seven parent
refusals and six child differences. Its local ND6 fixture was reconstructed from
actual C32 bytes and verified against the immutable ND6 receipt digest; Linux
validation uses the retained actual ND6 package configuration.

The [real receipt](results/ccmp-stable-monitor-candidate-11.json), identical to
[runtime binding](runtime-ccmp11/results/candidate.json), has SHA-256
`00eee0c5473a9f26ec8952096d2d992eab731050c2545301fc35443db8152144`.
All six private member hashes, sizes and mode 0600 were independently checked.
Raw boot 12673024 bytes:
`bc0dc195ba7f1987fea4042b85f92800508faceab8c86d8f8f2033c1759573af`.
Exact 16 MiB boot2:
`3fea3a7cf1572f6f3feae4aeb6b773bca912bcc9e548a665679a20ab2ee92aae`.
DT and RAM root are byte-identical to C10. GTK RX/key reuse/physical admission
remain false in the receipt. Historical release/USB/runtime labels still say
stable-monitor; this profile uses C0 mask control, with no SET_MONITOR fallback.

Fresh C11 preparation, capture, installer, host and session adapters bind this
real receipt and fresh namespaces. The installer pins the last installed C10
full checksum `73e1ac21860e69f6e8f03fd3625022bd8d4c8e6f189c17ecc44d40f91066ed8d`.
The five inherited binding/source/no-scan fixtures pass locally. All five fixtures also passed on Linux from clean pushed tooling
`003519224de8ddc9d525971b3d3c9028b55aae05`. The actual derived installer
review and deployment below complete the physical handoff gates.

## Fresh live image identity before any C11 trial

The observer was inlined; no new standalone symbol is claimed. Existing symbol
counts alone cannot distinguish C11 from C10's identical release string.
Use the guarded installation/readback chain and fresh boot identity, then also
read the standard read-only `/sys/kernel/notes`: exactly 84 bytes, SHA-256
`9519a6db2f5922e736534fc922d54784437ba0f8c62ce05d546f5e1220dc6b69`.
This differs from C10. ELF section/boundary checks and the packaged System.map
locate identical note bytes inside the validated Image. The pinned 7.1.3
`kernel/ksysfs.c`, `include/linux/sysfs.h` and `fs/sysfs/file.c` export exactly
that immutable note range; their hashes are in build validation. This is an
existing standard identity interface, not a new control API or register read.
Require the exact digest and length before capture; missing/mismatched identity
refuses device work. It identifies the kernel image, not firmware internal state.

## Retained limits and result interpretation

One arm/close, all-RX 512, 1 MiB, checked 64, wall 10 seconds or lower grant,
unchanged frame/100 ms command/cleanup limits and fatal poison. The observer
runs only in the existing ready/authorized initial-key ACTIVE window before
the PTK allocator/checker. It does not read PN bytes or mutate input/key/PN/queue
state. The single terminal `group PN observation` line distinguishes reported
group exposure, legacy group shape, observation-policy eligibility, G1 present/
absent and a mask bitmap. None is GTK authentication or delivery.

Record transport, DHCP/individual pings/fresh-boot SSH and cleanup independently.
Positive GTK metadata supports only the next strict checker review; absent PN
remains rejection, wrong shape/key is a separate branch, and no group exposure
is inconclusive. No unchanged retry, packet generator, length exception,
credit refund or global-monitor fallback. Original preservation/quiescence/A53/
one native return/finite changed-boot Gemian verification gates remain required.
Ordinary integrity, rekey/retirement, two healthy lifetimes and sustained minimal-
profile ten-minute SSH acceptance are still incomplete.

## Guarded deployment and complete host preparation

The [actual installer review](results/ccmp11-installer-review.json) pins the
603-line derived script SHA-256
`0df673ffb05240884deab7689bdfabb9986469699e416dba95ff20617d7b9a8c`.
It is byte-identical to C10 under the intended identity substitutions only.
Bash syntax and ShellCheck passed. The complete source guard remained
`0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf`.

The installer executed once, exit 0, from fresh verified Gemian boot
`2e2d8be5-54d4-4d99-a40b-91e005d19c1c`. Both live block-device gates passed,
with inactive/unmounted/non-root boot2, expected size/writability, exact C10
predecessor and stable power `1|100|Good|1`. It wrote C11, synced/flushed and
required exact full 16 MiB checksum and byte comparison. No new predecessor
backup; primary boot, boot3, calibration and GPT were not written.

[Deployment scalars](results/ccmp11-deployment-scalars.json) record full matching
readback and clean poweroff. SSH closed with status 255 during the reviewed
`systemctl poweroff`; the required finite watcher confirmed unreachable, with
no reboot. The summary's checksum seal was independently verified and the
summary copied mode 0600 byte-for-byte into the fresh C11 session root.

Complete actual offline session preparation then passed with Wi-Fi helper
key/boot environment unset, using the retained pinned source cohort separately
from credentials/calibration. At that preparation checkpoint the session root
contained only the deployment summary; capture, execution claim and helper were
absent. Owner physical selection then started the single trial described in the
[C11 result](CCMP11_RESULT.md), including verified return. These preparation
instructions are consumed; no unchanged retry or physical selection is pending.
