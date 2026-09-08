# MD1 reservation and protection handoff audit

## Result

Follow-up: the [Gemian observation](GEMIAN_HANDOFF.md) supplies one boot's
loader branch, reported header and concrete reservation map. The findings below
retain their source-only scope; secure acceptance and release remain unproved.

The pinned public host source distinguishes bootloader-loaded and kernel-loaded
modem paths, but neither is a passive reservation consumer. Bootloader readiness
skips selected image, ROM-remap and protection operations while leaving shared
remap and staged protection writes active. A mainline driver cannot interpret
that flag as blanket permission to preserve, replace or release modem ownership.

This source audit does not join an actual selected boot to its loaded image,
reservations or secure-firmware state. The implementation stop in the
[architecture review](README.md#exact-stop-and-discriminator) remains. No driver,
binding, mapping, firmware load or device action is admitted.

Source revision is `c5b0be85017ad0c599725e8273842efdbecdd88a` in the public
Planet kernel repository. [The receipt](results/memory-handoff-sources.json)
pins complete file hashes and the line ranges behind the following findings.
This is a read-only Git-object audit using the existing Buildbox cache, with
no source-tree transfer, private binary analysis, build or Gemini access.

## Boot selection and reservation ownership

`ccci_util_fo_init()` first tries the chosen-node `ccci,modem_info_v2` property,
then `ccci,modem_info`. Their payload identifies an external LK tag buffer;
the property alone is not the memory-layout record. If neither is present,
the code uses the `mediatek,ccci_util_cfg` path or the older per-modem DT path.
The v2 no-modem case also returns without entering the fallback path. These
branches cannot be selected from a vendor compatible or a defconfig name.

On the LK path, optional `opt_using_lk_val` permits individual loader options
to override defaults. `hdr_count` and `hdr_tbl_inf` supply modem base, size,
type and loader error; a zero per-modem loader error sets the environment-ready
bit. `md1_chk` and `md1img` supply the saved check header and raw image size.
Missing required header or shared-layout information can clear readiness.
Readiness is a parsed loader assertion, not a current hardware-state check.

`smem_layout` supplies one base with independent offsets and sizes for AP–MD1,
MD1–MD3 and AP–MD3 regions. `get_md_resv_mem_info()` returns the selected image
and AP shared-memory tuple; `get_md1_md3_resv_smem_info()` is a separate lookup.
The public DTS source instead requests dynamic `no-map` reservations:
MD1 requests `0xa100000` bytes aligned to `0x2000000`, and the shared reservation
requests `0x600000` aligned to `0x4000000`. These requests are not evidence of
the addresses or sizes after LK fixups, nor proof that all tag-derived regions
are excluded from the running kernel's allocator.

The inspected `lineage_gemini_defconfig` sets MD1 support 12, ECCCI CLDMA, C2K,
SCP and MTK PSCI. Its `CONFIG_MD1_SMEM_SIZE=0x200000` does not establish the
active size: the older [published device inventory](../2026-07-13-modem-ccci-recovery/results/live-ccci-postreboot-20260714.txt)
reports a DT property of `0x100000`, while the LK branch consumes its tag layout.
Neither value may substitute for the selected boot's actual allocation.

After parsing, the host zeroes the used LK tag buffer and unmaps it. A later
physical read of the chosen-node pointer is therefore not a reliable way to
recover the original handoff. No such read was attempted here.

## Region identity and feature correction

The [July offset table](../2026-07-13-modem-ccci-recovery/results/mt6797-ccci-mainline-contract.md#shared-memory-and-ownership-boundary)
labels the `0x19000` CCIF tail as MD1/MD3. The actual consumer assigns it only
to `MD_SYS3`, relative to that modem's AP shared-memory base. The separate
MD1–MD3 allocation comes from its own loader tuple; it is not that tail.
The historical record is retained, but its combined interpretation is superseded.

The MT6797 header leaves DHL CCB/raw and direct-tethering logging disabled;
their offset constants remain defined. Smart logging has an MD1-only local
tail at `0x1d000`, but `config_ap_side_feature()` advertises its runtime feature
as unsupported in both preprocessor branches. MD1 also advertises the CCIF
shared-memory feature as unsupported, while MD1–MD3 shared memory is supported.
Thus a defined offset or even an initialized local pointer does not prove that
the firmware negotiated that region. The actual handshake remains unobserved.

## Address views and protection writers

`ccci_md_config()` maps the supplied regions and calls `ccci_set_mem_remap()`
when the modem is enabled. For MD1, the bank-4 base is the AP–MD1 base rounded
down to 32 MiB; the source converts an AP address to a modem shared-memory
address by subtracting that rounded base and adding `0x40000000`. The register
encoding additionally depends on the runtime `enable_4G()` result. No concrete
address is derived here without those inputs.

The ROM/RW remap setter returns early when the environment-ready bit is set.
The shared-memory remap setter does not: with `ENABLE_MEM_REMAP_HW`, MD1 bank-4
registers are still written. This asymmetry matters even before image startup.

`md_cd_start()` bypasses image loading when ready and parses the saved loader
header through `ccci_get_md_check_hdr_inf()`. It still clears shared memory on
first start, configures protection, powers on and releases the modem. The
general protection function skips selected ROM writes when ready, but its
AP–modem shared-region programming remains active. First-stage MD1 protection
still writes the MCU-read-only/hardware-read-write region in the ready branch;
second-stage protection runs from the first-handshake notification before AP
runtime data is sent. This is a multi-stage firmware contract, not one static
reserved-memory permission.

With the inspected PSCI configuration, the EMI helper issues
`MTK_SIP_KERNEL_EMIMPU_SET` through the secure-call wrapper. The outer
`emi_mpu_set_region_protection()` ignores the inner return value and returns
its initialized zero. That return is not proof that secure firmware accepted
the requested protection. Secure-side authority, lock rules and failure handling
are not supplied by these host call sites.

## Lifetime and next evidence

The reviewed stop function powers down and clears transport state but does not
release these reservations. The platform remove callback returns zero without
cleanup, and its shutdown callback is empty. They provide no transferable
unmap, protection-reversal or allocator-release contract. Clearing the LK tag
buffer is separate from releasing the modem's image and shared-memory regions.

The next useful evidence is an attributable boot record joining the actual
kernel configuration and post-fixup reservation map to the selected loader
branch, loader image/header identity and shared-layout tuple. Prefer retained
boot records or bounded ordinary OS metadata; the original tag-buffer pointer
does not justify a physical-memory read after consumption. A separate
source/firmware contract must establish secure MPU acceptance and the safe
release conditions for MD1 and the shared MD1–MD3 owner. Missing links keep
mapping and activation closed; queue/DMA and framing work remain later gates.

Validation: complete public-file hashes and referenced ranges were checked;
the common repository gate passed. No kernel compile, schema test, runtime
handshake, memory access or hardware-support result is claimed.
