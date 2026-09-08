# MT6351 VCN33 ownership evidence

Source-only follow-up, 2026-09-08. No device access, PMIC reads or writes.
The shared voltage selector is established; output-pin topology and the enable
combination logic remain unresolved. Do not copy the newer PMIC drivers'
enable-consolidation writes on the strength of register names alone.

## Pinned source

The inspected public Gemian tree is commit
[`8cfe6596a503612e3332d9c26e292a19525a7f07`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/8cfe6596a503612e3332d9c26e292a19525a7f07).
Files were read from retained Git objects in the RE VM. This is a source
identity, not proof that its connectivity implementation is running on the PDA.
It differs from the Planet source revision used by the July regulator audit.
Its register header does match that audit's complete header SHA-256.

| Path below `drivers/misc/mediatek/` | SHA-256 |
| --- | --- |
| `power/mt6797/pmic.c` | `c08786d5ad44006d1fdc0f885e43f6ca1e9398f9c6e5e14c4ec6fe167e3d143c` |
| `include/mt-plat/mt6797/include/mach/upmu_hw.h` | `e376d2835dd32812b52caf6a51139cc7fd541de18eaad0f30ecf8194f70cebbe` |
| `connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c` | `0ec8e9c1594626d0b31f2d2623927d614f63af4437c16df838e10e11258663ce` |
| `connectivity/common/common_main/mt6797/include/mtk_wcn_consys_hw.h` | `3ee7631a95a12f5cddd860c213e51e75e1cb3146ca858a892aaae55b4d22fad1` |

## Established register and source facts

| Control | Header definition |
| --- | --- |
| Shared voltage selector | `0x0ada`, bits 10:9 |
| BT software enable | `0x0a98`, bit 1 |
| Wi-Fi software enable | `0x0a9a`, bit 1 |
| BT/Wi-Fi on-control fields | Bit 3 of their respective enable registers |
| BT/Wi-Fi source-clock selection | Bits 13:11 of their respective enable registers |
| Common reported VCN33 enable | `0x0a92`, bit 15 |

The selector table at `pmic.c:1404` maps raw values 0–3 to 3.3, 3.4, 3.5 and
3.6 V. Both descriptor entries at lines 1634–1637 use that one selector field.
Separate regulator handles therefore do not provide independent voltage
ownership. A successful write through either handle changes the field used by
both; the current draft has no cross-consumer voltage arbitration.

The connectivity header defines `CONSYS_BT_WIFI_SHARE_V33` as **0** and
`CONSYS_PMIC_CTRL_ENABLE` as **1**. The counter-based common BT/Wi-Fi helper at
`mtk_wcn_consys_hw.c:846–894` belongs to the disabled branch. Its presence is
not evidence that the common helper governs this platform.

The selected source branch has separate BT and Wi-Fi paths. Both request
3.3 V. Under `CONFIG_MTK_PMIC_LEGACY`, each path changes its own on-control
field and uses the vendor power API; the alternative uses separate regulator
handles. Which branch executes on a given boot needs matching configuration
and binary evidence. Nearby comments cite older offsets that disagree with the
MT6351 header; they are not a register-address authority.

## Decision

The common selector and common status naming support a shared analog-resource
interpretation, but they do not prove one output pin, two switched outputs, or
the Boolean relationship between the software and source-clock controls.
The [retained runtime summary](../2026-07-11-mt6351-pmic-recovery/results/runtime-pmic-repeat-20260714.txt)
reported both handles enabled at 3.3 V. That observation does not distinguish
those hardware models.

Keep the compile-only draft's shared-rail limitation open. A production model
needs an MT6351-specific output/control contract before choosing a common
regulator, aliases or separate output switches. The MT6358/MT6359 precedents
in the [topic record](README.md) do not supply that contract. This source audit
does not authorize enable-bit experiments, source-clock changes or radio use.
