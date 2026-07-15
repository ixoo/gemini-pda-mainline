# Experiment: Gemini modem CCCI/CLDMA recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-modem-ccci-recovery` |
| Status | `completed` for read-only topology and source comparison; mainline modem runtime remains untested |
| Subsystem | MT6797 cellular modem, CCCI, CLDMA, CCIF, shared memory |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date(s) | 2026-07-13 to 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Which modem transport and shared-memory contracts are actually live on the
Gemini, and can Linux 7.1.3's existing WWAN/CLDMA code be reused directly?

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Private raw capture: `artifacts/device-inventory/20260714-modem-live/ccci-topology.txt`
  (Git-ignored and access-restricted). The rerun SHA-256 is recorded in the
  current validation result.
- Vendor source: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`; source was read from Git objects
  in the VM and no vendor source was copied here.
- Mainline comparison: Linux `7.1.3` in the development VM.

## Safety assessment

The live collector is read-only. It reads sysfs metadata, flattened-DT
properties, device-node names, interrupt counters, interface state, process
names, and existing `/proc` path names. It does not open a modem character
device, issue a CCCI ioctl, read or write modem shared memory, reset or power
the modem, send radio traffic, read identifiers, or alter network state.

The source analyzer reads immutable vendor Git objects and Linux source. It
does not build or load a modem driver. Firmware images, NVRAM, and modem
shared-memory contents remain private and are not committed.

## Associated code

From the repository root:

```sh
mkdir -p artifacts/device-inventory/20260714-modem-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-13-modem-ccci-recovery/scripts/collect-live-ccci.sh \
  > artifacts/device-inventory/20260714-modem-live/ccci-topology.txt
chmod 700 artifacts/device-inventory/20260714-modem-live
chmod 600 artifacts/device-inventory/20260714-modem-live/ccci-topology.txt
./scripts/dev-vm run bash -lc \
  experiments/2026-07-13-modem-ccci-recovery/scripts/analyze-ccci-contract.sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-b7721ab55e41 \
   experiments/2026-07-13-modem-ccci-recovery/scripts/audit-current-package-ccci.sh'
```

The analyzer also emits a normalized, hash-anchored backend contract. See
[`results/mt6797-ccci-mainline-contract.md`](results/mt6797-ccci-mainline-contract.md)
for the wire header, queue/descriptor shapes, CCIF flow-control layout,
shared-memory offsets, EMI-MPU ownership, and the Linux reuse boundary.
The historical package/config/source recheck is
[`results/mainline-ccci-current-71-validation-20260713.txt`](results/mainline-ccci-current-71-validation-20260713.txt);
the current package audit is
[`results/mainline-ccci-current-package-20260714.txt`](results/mainline-ccci-current-package-20260714.txt).
The authoritative current Image/DTB-only package audit is
[`results/mainline-ccci-current-77-package-20260714.txt`](results/mainline-ccci-current-77-package-20260714.txt).
It remains a byte-repeatable static boundary check; the SPI additions do not
introduce a CCCI/CLDMA/CCIF transport node or alter the protected reservations.

## Procedure

1. Run the key-only SSH collector once with no modem control operation.
2. Record only topology, resource properties, counters, interface names, and
   process names; do not open any CCCI node.
3. Compare the live node/resource contract with the pinned vendor CCCI/CLDMA
   sources and Linux 7.1.3.
4. Hash the relevant source files and retain raw output only in the private
   artifact directory.

## Observations

- Two vendor CCCI domains are present. Major `237` exposes MD1 nodes including
  `ccci_aud`, `ccci_fs`, IMS/control/RPC/IPC nodes, raw shared-memory nodes, and
  `ttyC0`–`ttyC3`. Major `236` exposes a second `ccci3_*` family for the
  C2K/MD3 path, including `ccci3_at`–`ccci3_at8`, data, filesystem, ioctl, and
  TTY nodes.
- The live network topology has `ccmni0`–`ccmni17` (18 MD1 interfaces) and
  `cc3mni0`–`cc3mni7` (8 MD3/C2K interfaces). MD1 interfaces report
  `operstate=dormant`, `carrier=1`, and MTU 1500; the MD3 interfaces are down
  in this capture.
- Platform devices include `10014000.mdcldma` (`cldma_modem`), AP/MD CLDMA
  windows at `0x10219000`/`0x1021a000`, AP/MD CCIF windows at
  `0x10209000`–`0x1020c000`, `ap2c2k_ccif`, MD-to-MD CCIF windows, and
  `mdhw_smi`. CLDMA, CCIF, and watchdog platform objects are enumerated.
- The live `mdcldma` DT contract has six AP/MD/CCIF register windows, CLDMA
  capability `6`, MD1 shared-memory size `0x100000`, and vendor clock names
  including `scp-sys-md1-main`, `infra-ccif-ap`, `infra-ccif-md`, C2K, and
  MD-to-MD CCIF clocks. `ap2c2k_ccif` carries a separate `0x400000` shared
  memory size.
- Interrupt counters show active CCIF and CLDMA paths (DT SPI values decode to
  CCIF0/1, CLDMA AP, and modem-watchdog lines). This is enumeration/activity
  evidence only; no handshake or payload was attempted.
- The vendor CCCI configuration defines a 16-byte `ccci_header`, header
  version 3, memory-layout version 1, CCCI MTU 3456, network MTU 1500, and
  private channel/sequence/ioctl ABIs. Its shared-memory layout includes
  exception, runtime, CCISM, DHL, NETD, USB, smart-logging, and MD1/MD3 CCIF
  regions.
- The source-level queue contract is eight CLDMA TX/RX queues, with six normal
  and three network queues per direction, packed 16-byte TGPD/RGPD/TBD/RBD
  descriptors, and 36-bit address high nibbles carried in descriptor metadata.
  The CCIF side has eight queues per direction and an optional `FLOW`/`CTRL`
  busy-queue protocol. These are hardware/backend inputs, not a reason to
  reuse Linux `t7xx`.
- Vendor bring-up obtains modem and shared-memory reservations through
  bootloader/platform helpers, programs CLDMA/CCIF resources and clocks, and
  owns EMI MPU permissions plus optional 32 MiB-aligned memory remap banks.
  Those ownership contracts are prerequisites, not safe details to infer from
  the character-node names.
- The current Linux `7.1.3-gemini-b7721ab55e41` package selects generic WWAN
  and MHI helper options but ships no module tree, `t7xx`, RPMSG, QMI/MBIM, or
  CCCI/CLDMA transport. Its Gemini DTB retains exactly two `no-map` CCCI
  reservations (`md1` and shared memory) and has no active modem transport
  node. This is a deliberate carve-out boundary, not evidence that a modem
  probe is safe; see the [current 77-patch package audit](results/mainline-ccci-current-77-package-20260714.txt).

The 2026-07-14 live capture is byte-identical to the 2026-07-13 capture:
all 18 MD1 `ccmni` and eight MD3/C2K `cc3mni` interfaces, platform windows,
process names, and sampled interrupt counters are unchanged. The sanitized
comparison and private-capture hash are recorded in
[`live-ccci-repeat-20260714.txt`](results/live-ccci-repeat-20260714.txt).
After the battery-depletion reboot, a fresh bounded capture again enumerated
the same MD1/MD3 domains, CLDMA/CCIF windows, and network surface. The new
post-reboot result records the changed cumulative interrupt counters without
promoting them to a hardware invariant:
[`live-ccci-postreboot-20260714.txt`](results/live-ccci-postreboot-20260714.txt).

## Analysis

The device is not using a generic PCIe modem. It has two MediaTek modem paths
behind MT6797 APB-mapped CLDMA/CCIF blocks, vendor clocks, firmware-owned
shared memory, and an EMI MPU/remap setup. The live CCCI character and network
interfaces are a private vendor ABI; their existence does not make the Linux
`t7xx` driver applicable.

Linux 7.1.3's `t7xx` WWAN code is selected by `CONFIG_MTK_T7XX` and depends on
PCI. Its CLDMA implementation is tied to the T700 PCIe/DPMAIF transport and
cannot be adapted by changing a compatible string. Linux WWAN netdev, tty, and
port-proxy frameworks are reusable only after a new MT6797 CCCI transport
driver defines the ring, channel, handshake, reset, shared-memory, and modem
state contracts. A different chipset or transport is a reason to add a new
driver/backend, while retaining standard Linux interfaces above it.

The Linux 7.1.3 comparison also identifies the exact reusable WWAN boundary:
`include/linux/wwan.h` provides `wwan_create_port`, `wwan_remove_port`,
`wwan_port_rx`, TX flow-control helpers, and `wwan_register_ops`; a transport
implements `wwan_port_ops` and advertises framing with `wwan_port_caps`.
`rpmsg_wwan_ctrl` demonstrates the same lower-endpoint-to-WWAN-port adapter
shape. The prepared arm64 VM compiles `wwan_core.o`, `rpmsg_wwan_ctrl.o`, and
the compared `t7xx` objects. MHI and USB QMI/MBIM are useful pattern references
but their lower-layer dependencies do not match APB CCCI. The future MT6797
backend should use this WWAN port boundary and a normal `ccmni` netdev while
keeping the vendor `/dev/ccci*` character/ioctl ABI private.

The modem image (`modem_3_3g_n.img` in the private firmware inventory) and
calibration/NVRAM remain proprietary firmware boundaries. Dynamic CCCI,
CONSYS, SCP, and SPM reservations must remain protected until the bootloader
placement and lifetime contract is reproduced.

## Conclusion

`confirmed` for the live MD1/MD3 CCCI topology and the source-level transport
boundary. `inconclusive` for mainline modem runtime: no Linux CCCI/CLDMA probe,
firmware handshake, call/data test, or shared-memory access was attempted.

## Follow-up

- Recover a redistributable CCCI/CLDMA protocol description or an owner-
  authorized, non-transmitting handshake trace before implementing rings or
  channel mappings.
- Resolve the bootloader helper that supplies each modem image/shared-memory
  reservation and the EMI MPU ownership sequence; compare more than one boot
  before fixing any dynamic address.
- Design a new MT6797 CCCI/CLDMA transport under standard WWAN/TTY/netdev
  interfaces. Keep the vendor character ABI out of the mainline DT and UAPI.
- Keep modem, C2K, CLDMA, CCIF, and shared-memory consumers disabled in the
  Gemini mainline DT until those gates are met. See the
  [source validation](results/mainline-ccci-source-validation.txt) and the
  [current 77-patch package audit](results/mainline-ccci-current-77-package-20260714.txt).
