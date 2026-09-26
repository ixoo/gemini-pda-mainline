# Gemian EMI protection and Wi-Fi carrier in one boot

One bounded read-only Gemian inspection captured the controller's reported
region ranges and domain permissions. A later read in that same boot found
`wlan0` with carrier. The result narrows the mainline Wi-Fi EMI policy question:
the configured region-18 and region-19 permissions match the selected vendor
WLAN/WMT requests, but a broad
region 23 overlaps both. It does not establish effective domain routing,
multiple-region arbitration, firmware use of either window or authority for a
mainline protection write.

## Method and identity

The known-good LAN SSH endpoint was pinned to the existing project key and
host key. Gemian reported boot ID
`b79541db-5e95-4a02-a32f-87fa18474b38`, kernel `3.18.41+` and model
`MT6797X`; this is the independently confirmed return boot after the
[mainline handoff snapshot](../2026-09-25-mt6797-consys-handoff/results/runtime-20260926.json).
Two matching 3,294-byte reads came from
`/sys/bus/platform/drivers/emi_mpu_ctrl/mpu_config` at
`2026-09-26T11:25:05Z` and `2026-09-26T11:29:50Z`. Each used a 4,096-byte
output cap and no sysfs write. The first host wrapper used a reserved shell
variable after saving the response, so its outer exit status is not a valid
SSH receipt. The confirming SSH command exited zero and reproduced every
byte in the same verified boot.
The retained Gemian source comparator at commit
`8cfe6596a503612e3332d9c26e292a19525a7f07` shows that
`emi_mpu_show()` reads region registers through `mt_emi_reg_read()`; the latter
uses the EMI read service for MPU registers or MMIO for other offsets. The
source comparator has not been byte-matched to this running kernel.

The private raw responses are ignored under `artifacts/` and both have SHA-256
`b233c1f4328d747e54248384f4977ccc49e535de6b9fc3e6d8e0070a797b9a37`.
It ends with a newline and parses as exactly 24 unique region ranges and all
192 domain permission fields. The [sanitized result](results/runtime.json)
retains only the three decision-relevant regions. A separate read of
`wlan0` sysfs shortly afterward in the same boot reported `operstate=up` and
`carrier=1`. No network address, network name, calibration byte, firmware blob
or raw capture is published.

## Observation and decision

Region 18 reports `0xbfa00000..0xbfa7ffff`, with domain 2 `No` and the other
seven fields `FORBIDDEN`, packed policy `0xb6da2d`. Region 19 reports
`0xbfa80000..0xbfafffff`, with domains 0 and 2 `No`, the others `FORBIDDEN`,
packed policy `0xb6da28`. These ranges are the first and second 512 KiB of the
2 MiB CONSYS reservation observed in the preceding mainline boot. They also
match the selected vendor WLAN and WMT source requests, respectively.

Region 23 reports `0x00000000..0xffffffff` and overlaps both windows. Its
domain-2 field is `FORBIDDEN`, unlike regions 18 and 19. The source-backed
sysfs output shows programmed range and permission registers, not which
region wins a multiple match, whether a master actually uses domain 2, or
whether the broad region's hardware enable/applicability is the same as its
reported range. Carrier does not identify an EMI master transaction. No
protection policy is selected for mainline from these facts alone.

The known-good Gemian boot reports the two policy values from the selected
vendor source. The readout does not identify which component programmed them.
The next implementation still needs a single owner for region 18 and the
reserved range, attributable AP/CONSYS master routing, and an effective
overlap rule or an equivalent owner-verified applicability check. Mainline
firmware loading remains unimplemented; this inspection made no device change.

The [exact MT6797 register table](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Register_Table_Part_1.pdf)
describes per-domain violation-mask fields only through region 19. Reading
those mask registers would therefore not settle whether broad region 23
affects the WLAN window. The table also does not state an overlap arbitration
rule or assign the observed WLAN traffic to an EMI domain. It supplies no
reason to repeat boot2 merely to sample those mask fields.

## Same-boot connectivity rail status

A later bounded read at `2026-09-26T11:40:29Z` found Gemian's named VCN18,
VCN28 and Wi-Fi VCN33 sysfs status values all equal to `1`, while `wlan0`
remained up with carrier `1`. The boot ID matched before and after the read.
The [sanitized receipt](results/rail-status.json) binds the 194-byte private
response and zero SSH exit; the raw response remains ignored under `artifacts/`.
No PMIC register was written, and no radio action was requested.

This is a same-boot reference for the three active supplies, including VCN28.
It does not establish the VCN28 hardware-control selector, the effective
source-clock mode, the rail sequence, or which other connectivity clients hold
votes. Those remain provider-design questions rather than permission to copy
the vendor wrapper's unchecked return behavior.

## Region-23 producer and CONNSYS master label

A follow-up inspection of the [pinned public MT6797 EMI driver](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/emi_mpu/mt6797/emi_mpu.c), checksum
`39921d80191b674940246425123b52fa140262a7e17022f90f02dd88389932b2`,
found that its `protect_ap_region()` deliberately requests region 23 across
DRAM with packed permission `0xba8b68`; the live sysfs readout matches that
policy. This explains why the broad region is present in the reference, but
does not establish which overlapping region wins an access. The same driver
labels a CONNSYS master at peripheral port 6 with AXI ID match value `0x3`
and mask `0x1ffb`. Its violation path decodes the domain ID from status bits
23:21; the master-name table itself does not assign a domain.

A bounded read-only filter of the current Gemian `dmesg` returned no matching
EMI violation/master/domain lines and confirmed the same boot ID before and
after. The private 74-byte response is ignored under `artifacts/`; the
[sanitized receipt](results/master-routing.json) records its checksum. A quiet
ring buffer neither proves that no violation occurred nor identifies a domain.
No protection write, test violation or radio action was attempted. Mainline
must account for region 23 without overwriting it and still determine effective
CONNSYS/AP domain routing and overlap arbitration before writing region 18.

## Retained boot-chain routing pass

A renewed read-only RE-VM pass examined the privately retained preloader, LK
and TEE images after the host boot2 observation window ended. The preloader
SHA-256 was `25319ce877bd17b204fa264645aebf4583ec10ae2f05f6d8a7fff5efe4c06246`;
LK and TEE matched the previously recorded digests
`75ec9f0ba97af9e68d964b304e0de809f9b4546982570bd16b2e7fe88823282c`
and `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
The preloader was decoded as Thumb code with Capstone 4.0.2 and independently
checked with GNU ARM objdump 2.42. Raw images and disassembly remain private.

The preloader's device-APC domain-initialization path at file offset `0x276c`
zeros `0x1000ef00` and makes masked four-bit-field writes to `0x1000ea04`,
`0x1000ea08`, `0x1000ea0c` and `0x1000ea10`, using selected values 1, 2, 3,
5 and 6. The path's own diagnostic strings
identify this as device-APC domain setup. Those register-field writes are
decoded firmware behavior, **not** a map from a named CONSYS AXI master to an
EMI protection domain. The exact master-index meanings, later overrides and
the executing preloader's identity remain unverified. The earlier
[TEE EMI-set trace](../2026-09-05-mt6797-wifi-contract/RETAINED_EMI_SECURE_ABI.md)
establishes writes to region-18/19 range and policy registers, not a routing
or overlapping-region arbitration rule.

The [MT6797 register table, page 401](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Register_Table_Part_1.pdf#page=401)
places the AP-DMA HIF0 security/domain field at physical `0x11000020`, with
domain in bits 3:1. Global security control is at `0x11000014`. The
[functional specification, pages 143–144](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Functional_Specification_V1_0.pdf#page=143)
describes per-transfer security/domain setup and reset to defaults after a DMA
transfer. This governs **AP-DMA's own memory transactions**; it does not
identify WLAN firmware fetches by the CONSYS master. The pinned selected
[gen3 HIF DMA source](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb_pdma.c)
maps only the HIF channel window beginning at `0x11000080`; its
[header](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/include/hif_pdma.h)
defines local offset `0x20` as the destination address. Neither inspected file
sets the global HIF0 security/domain register. Their SHA-256 values are
`83c23a5582be2dcaa385359b7cd0f82af0ec9d6a4e102ea6faea57f59d75b480`
and `898874f9f3180000a393fab0a13666fd4960364f3c4b7517a1f965f027213028`.

The two MT6797 register-table parts were searched for the preloader's exact
`0x1000ea00`/`0x1000ef00` addresses and master-domain labels without finding
their master-index map; the EMI register pages were searched for a region-18/23
overlap rule without finding one. This is a bounded negative search, not proof
that the hardware has no rule. No current-boot register read, SMC, firmware
execution, DMA, protection write or radio action occurred. The next
decision-changing evidence is an exact MT6797 DEVAPC master-index/domain map
and EMI overlap applicability for the CONSYS master, or a separately admitted
attributable live transaction; AP-DMA's programmable field cannot substitute
for either.
