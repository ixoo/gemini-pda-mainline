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
