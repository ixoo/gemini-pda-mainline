# Exact PWRAP foundation audit

This audit selects the runtime-proven PWRAP package as historical input to the
authenticated A53 baseline. It selects no new device session. The audit parent is
`2891e041fbc5291956bd90882f0f52fea11f2504`; implementation, credential provisioning,
new candidate validation and runtime admission remain separate.

The machine-readable authority is [foundation.json](foundation.json). It pins
the historical manifest, series, all eleven fragment digests, complete Buildbox
provenance, both artifact manifests, kernel/container/DT/initramfs identities,
all 38 inherited archive members and the relevant raw DT resource properties.
Generated artifacts remain private and ignored. No physical device, VM or
Buildbox source tree was accessed by this audit.

## Selected input and reproduction boundary

| Input | Exact identity |
| --- | --- |
| Repository build commit | `ded915b81d56902d8800ff9fefc477480e4bcaa1` |
| Upstream | Linux `7.1.3`, kernel.org source archive; SHA-256 `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc` |
| Historical profile | `mt6797-pwrap-reset-serviceability`, arm64 `defconfig`, historical `patches/series`, eleven ordered fragments |
| Patchset | 505 patches; SHA-256 `bc6d039d88019e95c6e08c9a8caf78f611a8e238ca1cfb234672db3d31d6bcae` |
| Configuration input hash | `2d5840c3eca68e648b422aa00b5f354a73fa577f44bdcbfea78b5d2adc842979` |
| Resolved configuration | `194834d90eb2443f4b14ba8f2078ba16fe0c63f69088fcc8c063fe25af01c410` |
| Release | `7.1.3-gemini-mt6797-pwrap-reset` |
| Image | 13,688,840 bytes; `ee9162e607c263c039aabb22848d35fcefdb47daeaff82fcb3af69b7d3ef2838` |
| Image.gz | 5,636,902 bytes; `6682b2f7d4843c9460576380f28eb14289620e74c7d9b1f0c70ae33eeed3d4e5` |
| Composed DT | `e1e4eca289320533bad5c879e78055eaa86a295080b1154c13debe29ddd8ee4a` |
| Inherited initramfs | 1,820,254 bytes; `344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b` |
| Android boot container | 7,487,488 bytes; `305230b1e2845ce39e1ebee8a6d0ce420bc5766c837a2473dc9409551402bda3` |
| Exact 16 MiB padded image | `5c7429b297c718f5af61367588975e292a8c239854ffd5ba527eb86da1e4a5a6` |

Buildbox generated the package at `2026-09-04T01:21:01Z` using an x86_64
cross build, GCC `aarch64-linux-gnu-gcc (Debian 12.2.0-14) 12.2.0`, compiler
SHA-256 `c7b8890354c8ddc0364addfeb8968597e197627bd1e338fb6ed705b578803846`,
and GNU ld `2.40`, SHA-256
`e09a889c78a75e73ed096c9fa28905599e6813298b9ac839d10b02ffa96e7b08`.
The exact record includes ccache `4.7.5`; modules were not built. The package
contains 123 DTBs and 646 checksum-listed files. Its manifest SHA-256 is
`46a6602a2af1fa159eb1c89e451049f6818f738a53b1c01226e2ff100302c745`.
The 12-file candidate manifest SHA-256 is
`528f38ae3459149bc6f12242118b69d104590bd8902eef7d3969a1cd1b8d0f17`.

The DT is not the package's ordinary board DTB. The
[historical builder](../../2026-09-04-mt6797-pwrap-reset-serviceability/scripts/build_dtb.py)
retained Candidate AW's exact final DT
`e51891c839ab5e40e591346cb78ac66f1c5e0179a1cc30c4a33acf0b9c0667f7`
and changed only PWRAP's second reset cell from 64 to 1, yielding `<3 1>`.
AW's manifest was
`22b2cc789c0ac39792617f693b8852ff1a8ad25d71e733cb6f8727716f34171b`.
Only those independently identified DT/initramfs inputs were reused; AW's
quarantined noncanonical eMMC profile is not a permissible kernel foundation.

The retained LK contract is Android v0, `gemini-obs-L`, header command line
`bootopt=64S3,32N2,64N2`, kernel `0x40200000`, ramdisk `0x45000000`, second
`0x40f00000`, tags `0x44000000`. Linux forces its configuration command line;
editing the Android header does not change the CPU or console policy. A new
initramfs must be composed and independently checked as a new container.

### Current profile drift

At the audit parent, the identically named profile selects
`patches/series-before-v4-conversion-correction`, containing 529 patches.
It adds 24 patches, `0517` through `0540`, after the 505-patch historical set.
The original patch bytes, relative order and all eleven configuration fragment
bytes still match the historical Git inputs. The kernel archive is unchanged.
That establishes a usable canonical subsequence, not binary equivalence of
the later profile. Thermal/A72 changes being disabled does not prove the two
packages are identical.

The closed experiment's
[package validator](../../2026-09-04-mt6797-pwrap-reset-serviceability/scripts/validate_package.py)
requires today's manifest entry to say `patches/series`. It therefore refuses
the changed manifest before it can validate this retained package. It also
expects the package under the calling checkout's exact Buildbox export root.
Do not edit that historical validator or claim it passed in the current tree.
The new [audit_foundation.py](audit_foundation.py) instead compares the package
against immutable Git objects at the historical commit, every packaged patch
and fragment, full manifests and binary pins. It also verifies that the
historical selection is still a canonical subsequence with unchanged bytes.

For future kernel compilation, the integrator must pin an explicit historical
505-patch subsequence/profile before using the normal clean, committed,
published Buildbox workflow. Reusing the already validated exact kernel package
for an initramfs-only delta needs no Linux source copy or kernel rebuild.
The intended new candidate remains distinct from the closed historical boot.

## Userspace and console contract

The archive has 38 members, including 16 regular files. It contains no account
database, SSH daemon, host key, authorization key or password configuration.
The exact inventory and metadata are in `initramfs_members` in
[foundation.json](foundation.json).

| Component | Audited behavior and implication |
| --- | --- |
| `/bin/busybox` | Static ARM64 binary, SHA-256 `52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`; all normal applets use these same bytes. |
| `/init` | Mounts devtmpfs, read-only procfs/sysfs, launches the USB worker and independent keyboard probe, then BusyBox init. No persistent root mount or automatic reboot. Historical labels still say `maxcpus-1`; the actual forced kernel configuration says `maxcpus=8`. |
| `/bin/usb-net`, `/bin/usb-shell` | Wait at most 30 seconds for `usb0`, set `10.15.19.82/24`, then unauthenticated, unencrypted root `nc` on TCP 2323. The shell prints a banner and uses an interactive prompt. These are the intended authentication replacement boundary. |
| `/etc/inittab`, `/bin/local-shell` | Respawn supervised tty1, select foreground VT1, initialize Unicode mode, verify or load the exact keymap, verify all map entries, then start interactive ash. Ctrl-Alt-Del is a no-op. |
| Kernel logs | Forced command line has `console=ttyS0,921600n8`, `earlycon`, `ignore_loglevel`, `loglevel=8`, `log_buf_len=1M`, `initcall_debug`; there is no VT console token. Kernel logs remain in serial/kmsg/ramoops rather than tty1. |
| `/bin/x-record`, `/bin/ac-record` | Append RAM status and emit records to kmsg and ttyS0; do not write tty1. Their old markers are historical text, not sufficient new attribution. |
| Keyboard map/utilities | Map SHA-256 `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`; Unicode helper `5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650`; verifier `29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`. |
| `/bin/x-probe` | Automatically discovers the matrix event node within 5 seconds and starts one 15-second, non-grabbing event capture. This historical automatic action must be explicitly accounted for or removed from the new packet; it does not confer a reusable keyboard-test budget. |
| `/bin/reboot` | SHA-256 `3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7`; invokes exact BusyBox `reboot -n -f`, with no sync or storage inspection. Both shells validate the `reboot` alias before exposing their prompt. |
| `/bin/emmc-flash-boot2` | Dormant, explicit-opt-in historical write helper, SHA-256 `a4aa07eedefac73804483039f1db48206628fe8894b085627183802a4be7c88d`; does not implement the current shared guard. Remove it from the new administration image rather than expose an obsolete deployment path. |

The keymap utilities have tracked GPL-2.0-or-later source under
[the console-map experiment](../../2026-07-20-keyboard-console-map-diagnostic/README.md).
The static input-event helper has tracked source and exact binary validation in
the earlier keyboard experiments. BusyBox's historical constructors inherited
the binary from a `busybox-static` package, but this audit has not established
an exact source-package/version/download provenance for that binary. Its byte
identity and runtime history are established; a redistributable new userspace
package still needs its own source/license inventory and compliance record.
The audit neither publishes inherited binaries nor claims all-source rebuild
reproducibility of the old initramfs.

## Kernel and DT resource contract for parallel work

These are static observations of the exact candidate DT/configuration, scoped
separately from the runtime pass. Raw property bytes are recorded in
[foundation.json](foundation.json). Dynamic reservations below are pre-LK
constraints; their selected runtime physical addresses are not established here.

- CPUs are the ten described cores: eight A53 entries with PSCI, two A72
  entries using `mediatek,mt6797-psci`; the proven observation was
  possible/present `0-9`, online `0-7`, offline `8-9`. The forced command line
  keeps `maxcpus=8`. There is no enabled A72 power, platform-state, transition,
  hotplug or DVFSP handoff/backend configuration.
- PWRAP at `0x1000d000 + 0x1000` uses GIC SPI 178, clocks `<6 22>, <3 2>`
  named `spi,wrap`, and reset `<3 1>` named `pwrap`. MT6351 and its regulator
  child are enabled, including VEMC and VIO18. Thermal at `0x1100b000` remains
  disabled; `CONFIG_THERMAL`, CPU frequency, CPU idle and suspend are disabled.
- eMMC MSDC0 at `0x11230000 + 0x10000` is enabled, 8-bit, non-removable,
  `no-sd`, `no-sdio`, capped at 25 MHz. It uses GIC SPI 79 and clocks
  `<3 33>, <6 16>, <6 17>` named `source,hclk,source_cg`; VEMC/VIO18 phandles
  are 26/27. MSDC1 at `0x11240000` is disabled. This describes no Wi-Fi SDIO
  transport; `CONFIG_WIRELESS`, `CONFIG_WLAN` and modules are disabled.
- The usable USB path is MTU3 `0x11271000 + 0x3000` with IPPC
  `0x11280700 + 0x100`, GIC SPI 127, `dr_mode=peripheral`, clocks
  `<3 75>, <3 76>, <3 69>` named `sys_ck,ref_ck,mcu_ck`. USB2 PHY
  `0x11290800 + 0x100` is enabled with its fixed reference clock. USB3,
  xHCI and the USB1.1 host node are disabled. Kernel g_ether provides the
  direct IPv4 gadget link; authentication is an initramfs delta.
- Keyboard I2C5 at `0x1101c000 + 0x1000` and DMA window
  `0x11000380 + 0x80` is enabled, using GIC SPI 83 and clocks
  `<3 60>, <3 46>` named `main,dma`. AW9523 at address `0x5b` supplies an
  8-by-7 matrix, polled every 20 ms. The IRQ/wake/rollover contract is not
  established by the matrix/map or PWRAP serviceability pass.
- The retained DT also leaves I2C6 `0x1100e000 + 0x1000`, DMA window
  `0x11000500 + 0x80`, GIC SPI 88, clocks `<3 54>, <3 46>` enabled, with
  `regulator@68` compatible `dlg,da9214`. The resolved DA9211 and legacy
  DA9213-family drivers are disabled. Do not describe this DT as removing
  I2C6/DA9214, or assume a runtime-proven active regulator provider here.
- Infracfg phandle 3's clock 46 is shared by these I2C `dma` resources.
  The [prior clock observation](../../2026-07-24-mt6797-ap-dma-owner-observer/README.md)
  identifies I2C5's DMA clock as `infra_ap_dma`. The series contains the historical DVFSP/AP-DMA
  preservation work, but its owning DVFSP configuration is disabled in this
  package. `clk_ignore_unused` is retained. That is not a new shared-resource
  ownership or permission-to-toggle claim for Wi-Fi.
- No CONSYS, WMT, BTIF or Wi-Fi device/transport node is present in this
  candidate DT. Its retained `consys-reserve-memory` is `no-map`, size
  `0x200000`, alignment `0x200000`, alloc-ranges `<0 0x40000000 0 0x80000000>`.
  This constrains allocation to `[0x40000000, 0xc0000000)`; it is not a fixed
  `reg` address, mapped userspace transport, firmware load, or active driver.
  Vendor Wi-Fi/CONSYS windows, IRQs and AP-DMA sharing remain evidence in
  [the connectivity investigation](../../2026-07-12-connectivity-wmt-recovery/README.md),
  not an active contract silently inherited by the authenticated baseline.
- SCPSYS is described at `0x10006000 + 0x1000`, but `CONFIG_MTK_SCPSYS` and
  `CONFIG_MTK_SCPSYS_PM_DOMAINS` are disabled. A future CONSYS power owner
  must review overlapping SPM, infracfg, reset and PMIC ownership explicitly.

Static no-map reservations also retain `0x40000000+0x1000`,
`0x44400000+0x10000`, ramoops `0x44410000+0xe0000`,
`0x444f0000+0x10000`, ATF `0x44600000+0x10000`, ATF ramdump
`0x44610000+0x30000`, cache dump `0x44640000+0x30000`,
`0x44800000+0x100000`, and `0x46000000+0x400000`. The dynamic CCCI,
CCCI-share, SPM and SCP-share reservations retain their exact size/alignment/
allocation constraints in the JSON. Ramoops preserves record `0x1000`, console
`0x10000`, ftrace `0x1000`, pmsg `0x20000`, mem-type 0; the pmsg frontend is
disabled and its allocation is not cross-version evidence. No new reserved
memory writer is authorized by preserving these descriptions.

## Runtime and recovery evidence

The [original runtime record](../../2026-09-04-mt6797-pwrap-reset-serviceability/results/runtime-attempt-1-pwrap-serviceable-20260904.txt)
attributes one complete session to boot ID
`30ed4846-5a9f-4bd4-8450-c0c0ba4f4b07`, exact release and runtime PWRAP reset
tuple. PWRAP, MT6351 core/regulator child, VEMC, VIO18 and MSDC bound; one MMC
card had 122,142,720 sectors and 33 GPT partitions. Targeted PWRAP/MMC error
counts were zero. One netcat session and CPUs 0–7 passed. The owner reported
working framebuffer console; keyboard coverage and authentication were not
measured by this observation. No storage read/write or thermal/load action
was performed by that observer.

The [deployment record](../../2026-09-04-mt6797-pwrap-reset-serviceability/results/deployment-20260904.txt)
resolved inactive `boot2` on that cycle, recorded predecessor checksum, wrote
the exact padded candidate, verified full readback, then shut down.
Those historical p30/p29 names are evidence, not new target-selection rules.
The [recovery record](../../2026-09-04-mt6797-pwrap-reset-serviceability/results/native-recovery-20260904.txt)
records one exact-wrapper reboot request and changed-ID Gemian `3.18.41+`,
boot ID `00101221-1d89-4896-b634-75ed02cf46a6`. The host initially rejected
interactive prompt prefixes after the device had acted; no retry occurred.
The repaired parser evaluated the marker-bounded suffix. A later read-only
full checksum confirmed the candidate remained in boot2. This is one prior
recovery success, not current custody or fresh admission.

## Deployment reuse boundary

The current [shared boot2 guard](../../../scripts/boot2-device-guard.sh)
must run after live GPT selection and immediately before a write. The
[V4 guard derivation](../../2026-09-04-mt6797-thermal-snapshot/scripts/v4_installer_guard.py)
and [strict receipt parser](../../2026-09-04-mt6797-thermal-snapshot/scripts/v4_deployment_receipt.py)
are reusable mechanisms to study: they add observed root/target major:minor
identities, pin the guard digest, reject ambiguous fields, distinguish a
verified write from an already-matching skip, and require readback plus
shutdown/disappearance evidence. Their experiment, candidate, manifest and
one-use receipt-directory identities are V4-specific; they are not directly
usable for this packet and their observation budget is consumed.

The new installer must retarget those identities and validate its own receipt
path and consumer together. It must clean temporary upload/readback state on
interruption, preserve a durable incomplete outcome, refuse automatic replay
after uncertainty, and never infer physical boot selection from a partition
checksum. The historical installer alone does not meet the current guard
requirement. No generic runner or replacement deployment framework is needed.

## Audit checks and limits

The 2026-09-05 offline audit passed against the retained primary-checkout
exports: 646 package files, 12 candidate files, 505 historical patch comparisons,
eleven fragment comparisons, 38 archive members, recorded DT resources and LK
container validation. All 10 inventory test methods passed, including their
path and symlink subcases. Scoped Python syntax, JSON parsing, Markdown links,
license markers and sensitive-path scans passed; `git diff --check` passed.
No shell file changed, no kernel build ran and no device was accessed. The
integrator's all-worktree prepublication gate remains required before commit.

Run the audit against the retained exports with explicit paths:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/audit_foundation.py \
  --package "$PACKAGE" --candidate "$CANDIDATE"
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/test_audit_foundation.py
```

Here `PACKAGE` is the exact directory named in `foundation.json` beneath the
historical `artifacts/buildbox/<commit>/` export and `CANDIDATE` is its named
PWRAP candidate beneath `artifacts/mt6797-pwrap-reset-serviceability/`.
The audit reads those exports in place and creates no binary copy. It validates
all recorded checksums, exact inventories, historical Git/packaged/current
patch and fragment equality, build provenance, gzip/Image equality, inherited
userspace metadata, exact padding and the independent LK analyzer. Fixtures
exercise changed, missing, duplicate, unlisted, malformed, traversal and
symlink inputs, including symlink ancestors and wrong counts.

These host checks prove retained-input integrity and historical attribution.
They do not run ARM64 userspace, authenticate SSH, rebuild the old initramfs
from sources, prove the later manifest profile equivalent, retest hardware,
establish current recovery, or admit the proposed baseline and its dependents.
