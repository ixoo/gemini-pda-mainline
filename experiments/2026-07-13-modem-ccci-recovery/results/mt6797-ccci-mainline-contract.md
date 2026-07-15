# MT6797 CCCI/CLDMA mainline contract

## Status

The live Gemini topology and the pinned Planet source establish a distinct
MT6797 APB CCCI transport. This is not the PCIe/DPMAIF transport implemented
by Linux 7.1.3 `t7xx`; a new platform CCCI/CLDMA/CCIF backend is justified.
This record is a design input, not a working modem driver.

No modem character device was opened, no shared-memory byte was read, no
handshake or radio operation was attempted, and no reset, power, EMI-MPU, or
CLDMA register was written.

## Provenance

The source-only analyzer is
[`analyze-ccci-contract.sh`](../scripts/analyze-ccci-contract.sh). It reads
Git objects from Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a` and compares Linux `7.1.3` in the
development VM. Vendor source and firmware are not copied into this
repository.

The key source inputs are hash-anchored below:

| Source | SHA-256 |
| --- | --- |
| `eccci/mt6797/ccci_config.h` | `b357a3315115cc62c2e240d357eb1635ae4f308e32e4fccb1d310cf91d94c56e` |
| `eccci/mt6797/cldma_reg.h` | `a6f0119e5db899aa0657f95794f703fd8f00b3fbc0889325d87cdd17938bb32b` |
| `eccci/mt6797/modem_reg_base.h` | `5d923dc4eca7c724b6bbd8d238f61cae69afe8810afb5039b5895d5f843541f8` |
| `eccci/modem_cldma.h` | `e056e5d15e7f1725c66bc7a98e763ef8e78a81ababcbb5608b8030ed89d9402b` |
| `eccci/modem_ccif.h` | `a8dc81f4754846280c6e273dd58e0ef4dabc128323657037c890aea012059bfc` |
| `eccci/ccci_ringbuf.h` | `cb33fa0073ad1fb53d00b0a9465cd1a7d10c815b91673bcd7d0a031bcf82975a` |
| `eccci/ccci_core.h` | `fca1f5e06f5353967dd8782a2e42fcbaa712f167180e436a1ff6d0d013cee697` |
| `eccci/port_proxy.h` | `8b04f0bfee405c74741822b17e74caa9e005bfb7544095a47854b84ca5213dfc` |
| `include/mt-plat/mt_ccci_common.h` | `f2e705f6a43ecdaeabf0188c148268ce99c525b2ce71f756579d861b830da74f` |
| `eccci/mt6797/cldma_platform.c` | `ada25c673de99cf648955cc782fabf7ab98af1c6bf3227ca7883d5ff44792125` |
| `eccci/mt6797/ccci_platform.c` | `d7092013b0fa14b12c37e96a973c3179c565c1a1e1ebef3a6c27ec38b566a156` |
| `eccci/port_cfg.c` | `feabc1a20dd4a149daeac5d275b4894e9b13ef6cdd1a1afc1dd46458db213a8f` |
| `arch/arm64/boot/dts/mt6797.dtsi` | `eaac86c8752ebd8ddf18b831eb3bc52a08f87475a213bb521650bf95dabb3e5e` |

The current prepared Linux/package recheck is recorded in
[`mainline-ccci-current-71-validation-20260713.txt`](mainline-ccci-current-71-validation-20260713.txt).
It confirms that the authoritative 71-patch Image is built with
`modules_built=true` and an optional module tree, while `CONFIG_WWAN=m` and
`CONFIG_MTK_T7XX` remains unset. The generic WWAN and comparison `t7xx`
objects compile in the VM build tree, but none is loaded from the Gemini Image.

## Live topology

The read-only capture records two vendor domains:

- MD1 uses major `237`, `ccci_*`, `ttyC0`–`ttyC3`, and `ccmni0`–`ccmni17`.
- MD3/C2K uses major `236`, `ccci3_*`, and `cc3mni0`–`cc3mni7`.
- The aggregate `mdcldma` node is at `0x10014000`; the AP/MD CLDMA data
  windows are `0x10219000` and `0x1021a000`; AP/MD CCIF windows are
  `0x10209000`–`0x1020c000`.
- MD1 uses CLDMA capability `6` and a declared shared-memory size of
  `0x100000`; the separate C2K node declares `0x400000`.
- The captured CLDMA, CCIF, and modem-watchdog interrupt lines are active,
  but activity alone does not prove a usable handshake or payload path.

These addresses and sizes are platform evidence. They are not permission to
map or touch the modem from a development kernel.

## Wire and queue contract

The vendor wire header is a packed 16-byte `ccci_header`: two 32-bit data
words, a 16-bit channel, a 15-bit sequence number, a one-bit assert flag, and
a 32-bit reserved word. The source selects header version `3`, memory-layout
version `1`, CCCI MTU `3456`, and network MTU `1500`.

The MT6797 CLDMA implementation has eight transmit and eight receive queues.
Six of each are normal queues and three of each are designated for network
traffic (the remaining queue is reserved by the vendor implementation). Its
descriptor families are TGPD/RGPD and optional TBD/RBD scatter-gather
descriptors. Each is a packed 16-byte shape; 36-bit physical-address high
nibbles are carried in debug/reserved fields rather than in a normal Linux
DMA address. This is a hardware descriptor contract, not a reusable copy of
the vendor queue code.

The CCIF path has eight transmit and eight receive queues. Its optional flow
control structure uses `FLOW`/`CTRL` magic values and AP/MD busy-queue bitmaps.
The CCIF SRAM layout carries a downlink header plus MD runtime data and an
uplink header plus AP runtime data. The separate CCCI ring buffer stores
shared RX-read/TX-write and RX-write/TX-read controls around a variable data
area.

The vendor port table maps MD1 network channels to `ccmni0`–`ccmni17` and MD3
channels to `cc3mni0`–`cc3mni7`; queue indices and ACK channels are encoded in
the private `port_proxy` table. Mainline should expose standard WWAN/netdev
and tty ports only after this channel mapping is independently validated.

## Shared-memory and ownership boundary

The source lays out the following offsets relative to the bootloader-provided
MD1 shared-memory base:

| Region | Offset | Size |
| --- | ---: | ---: |
| Exception/debug | `0x00000` | `0x10000` |
| AP/MD runtime | `0x10000` | `0x1000` (`0x800` per side) |
| CCISM | `0x11000` | `0x8000` |
| CCB DHL (feature-gated) | `0x19000` | `0x1000` |
| Raw DHL (feature-gated) | `0x1a000` | `0x1000` |
| Direct-tethering NETD (feature-gated) | `0x1b000` | `0x1000` |
| Direct-tethering USB (feature-gated) | `0x1c000` | `0x1000` |
| Smart logging / MD1 tail | `0x1d000` | variable, last |
| MD1/MD3 CCIF tail | `0x19000` | variable, last |

The source computes all addresses from bootloader-provided reserved-memory
bases; offsets alone do not establish a stable physical address or total size.
The feature-gated CCB/CCIF definitions intentionally share the `0x19000`
boundary, so a backend must resolve the active feature set rather than map
both regions unconditionally.

The modem platform source defines EMI-MPU regions for MD1 ROM/RW (`11`/`14`),
MD3 ROM/RW (`16`/`17`), shared memory, and modem hardware views. It may skip
clearing protection when the boot environment reports that it already owns
the modem setup, and it aligns the remap range to 32 MiB boundaries. This is
an ownership protocol with secure/boot firmware, not a normal Linux IOMMU
setup. A mainline backend must obtain an explicit reservation and ownership
contract before touching shared memory, descriptor rings, or reset state.

The source also requests `scp-sys-md1-main`, AP/MD CCIF clocks, two AP-to-C2K
CCIF clocks, and six MD-to-MD CCIF clocks. Clock enablement cannot be separated
from the modem power and handshake state machine.

## Linux 7.1.3 boundary

Linux `t7xx` is selected by `CONFIG_MTK_T7XX` and depends on PCI; its CLDMA is
the T700 PCIe/DPMAIF implementation. It is not a compatible MT6797 transport,
and a compatible-string substitution would be incorrect. The generic WWAN
core is a better reuse boundary: `include/linux/wwan.h` supplies
`wwan_create_port`, `wwan_remove_port`, `wwan_port_rx`, TX flow-control helpers,
and `wwan_register_ops`. A transport implements `wwan_port_ops` (`start`,
`stop`, and `tx`, with optional blocking/poll methods) and advertises framing
through `wwan_port_caps`; the core then exposes standard AT/MBIM/QMI/QCDM,
FIREHOSE, XMMRPC, FASTBOOT, ADB, MIPC, or NMEA ports. `rpmsg_wwan_ctrl.c`
demonstrates this adapter shape for another lower layer, while the MHI and USB
QMI/MBIM drivers demonstrate transport-specific alternatives. None of those
lower-layer dependencies match APB CCCI, so only the WWAN port/netdev/tty
interfaces are reusable above a new MT6797 backend.

Required new work is:

1. a disabled MT6797 platform CCCI/CLDMA/CCIF resource driver;
2. a bootloader/firmware handshake and modem state machine;
3. descriptor-ring and CCIF interrupt handling with explicit DMA/cache rules;
4. reserved-memory and EMI-MPU ownership integration; and
5. standard WWAN/TTY/netdev consumers without the vendor character/ioctl ABI.

The future backend should create WWAN control ports with `wwan_create_port`
and deliver completed CCCI packets through `wwan_port_rx`; its network data
path should register a normal netdev for the `ccmni` service rather than
reproducing the vendor `/dev/ccci*` ABI. This keeps channel mapping, queue
ownership, reset, and shared-memory lifetime inside the MT6797 transport while
retaining upstream userspace-facing interfaces.

## Safe gates

- Keep all modem, C2K, CLDMA, CCIF, and shared-memory consumers disabled in
  the Gemini mainline DT.
- Do not open `/dev/ccci*`, map modem memory, send a CCCI ioctl, reset the
  modem, or use a generic network test as a first probe.
- First recover bootloader reservation placement and a non-transmitting
  state transition/handshake trace from an explicitly authorized source or
  trace. Only then design one MD1 queue and one standard netdev path.
- Treat modem firmware and calibration/NVRAM as a separate, non-redistributable
  boundary until licensing and load ownership are proven.
