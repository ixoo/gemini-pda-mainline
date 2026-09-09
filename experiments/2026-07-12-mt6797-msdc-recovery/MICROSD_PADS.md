# MT6797 microSD pad ownership

Offline source and retained-kernel follow-up, 2026-09-09. No live device
access, register reads/writes, pin configuration, build or boot occurred.
This resolves candidate field locations, not electrical settings or runtime
support. It follows the [card-detect/power contract](MICROSD_CONTRACT.md).

## Field map

The pinned Gemian GPIO table and MMC register header agree on GPIO129–134:
CMD, DAT0, DAT1, DAT2, DAT3, CLK, respectively. Function 1 selects MSDC1.
The retained board DTB describes IOCFG_B at `0x10002400` and IOCFG_R at
`0x10002800`, each with length `0x400`. The pinned upstream driver already
names these bases `iocfgb` and `iocfgr`, at indices 2 and 3. No additional
register resource is indicated for the fields below.

| Control | Base + offset | CMD | DAT0–3 | CLK |
| --- | --- | --- | --- | --- |
| Input enable | B + `0x020` | bit 25 | separate bits 26–29 | bit 30 |
| Schmitt enable | R + `0x030` | bit 0 | shared bit 1 | bit 2 |
| Pull direction | B + `0x100` | bit 18 | separate bits 19–22 | bit 23 |
| Pull R0 | B + `0x110` | bit 18 | separate bits 19–22 | bit 23 |
| Pull R1 | B + `0x120` | bit 18 | separate bits 19–22 | bit 23 |
| TDSEL | B + `0x0c0` | bits 19:16 | shared bits 23:20 | bits 27:24 |
| RDSEL | B + `0x0a0` | bits 13:8 | shared bits 19:14 | bits 25:20 |
| Drive selector | B + `0x1b0` | bits 23:21 | shared bits 26:24 | bits 29:27 |

DAT0–3 cannot have independent Schmitt, delay or drive settings. A future
field table must describe those shared fields rather than incrementing the
bit position for each data pin. The card-detect GPIO67 is a separate pin and
is outside this six-pin map.

## Boundaries a direct table port would miss

The vendor drive helper documents selectors 0–7 as 2–16 mA in 2 mA steps.
Upstream currently assigns these pins `DRV_GRP3`, whose generic table accepts
2–8 mA and uses a different selector scale. `DRV_GRP4` describes the vendor's
stated scale. Adding drive fields and a callback while retaining `DRV_GRP3`
would therefore encode different selectors for the same requested current.
The vendor current labels remain source evidence, not measured drive current.

More importantly, both compiled host-1 drive branches finish with another
read/modify/write to B + `0x1b0`: clear mask `0x001f0000`, then insert
`0x00050000`. This matches the separate five-bit `MSDC1_BIAS_MASK` and literal
5 in the public source. It is disjoint from the three drive-selector fields.
It must not be represented as ordinary pull-up/pull-down or folded silently
into a generic drive callback. Its electrical meaning and retention across
boot/power transitions remain unresolved.

The public pull helper requests CMD/DAT pull-up as PUPD/R0/R1 = 0/1/0 and
CLK pull-down as 1/0/1; its comments name 10 kOhm and 50 kOhm, respectively.
Those comments do not supply a complete resistance table. The helper's
disable path clears all three fields. An eventual bias implementation must
use the existing MediaTek R0/R1 contract and preserve unsupported cases,
rather than guessing an ohmic mapping.

Input-enable fields can be prepared independently of this drive/bias policy.
The [isolated input-enable topic](../2026-09-09-mt6797-msdc1-input-enable/README.md)
now adds that six-pin map and passes Buildbox compilation without a board change.
Schmitt handling needs an additional API review: the pinned Paris setter
changes GPIO direction before writing SMT, whereas the compiled vendor MMC
helper changes SMT alone. A mapped SMT bit is therefore not by itself proof
of an equivalent transition. Keep board activation separate from provider
field support; none of these findings justifies restoring the previously
removed generic eMMC pad properties or enabling MSDC1 now.

## Provenance and reproduction

Source: [Gemian commit 8cfe6596](https://github.com/gemian/gemini-linux-kernel-3.18/tree/8cfe6596a503612e3332d9c26e292a19525a7f07).
Read the following Git objects in the RE VM and inspect array entries 129–134
alongside the `MSDC1_*` definitions and helper implementations:

| Path | SHA-256 |
| --- | --- |
| `drivers/misc/mediatek/gpio/mt6797/gpio_cfg.h` | `29ea8cc6a821288defab068c0f8c6f452b3adcd068d48c3ca0702a616454ac9c` |
| `drivers/mmc/host/mediatek/mt6797/msdc_io.h` | `e3c97a2930ac29dd46838c170c733fb05d5d87b5aa139ee7837da9b9f242ce65` |
| `drivers/mmc/host/mediatek/mt6797/msdc_io.c` | `b87966fb3bb7be7e9c7c273cc58e92e7c19ed6a3b09a503afbaedb529c890e07` |

Upstream comparison uses commit `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`,
files `pinctrl-mt6797.c`, `pinctrl-mtk-mt6797.h`, `pinctrl-paris.c`, and
`pinctrl-mtk-common-v2.c` under `drivers/pinctrl/mediatek/`.
The driver has only MODE, DIR, DI and DO register calculations and no drive
or bias callbacks; the field/encoding issue is latent until those are added.

Binary identities and Image slicing method are in the
[preceding receipt](MICROSD_CONTRACT.md#reproduction-and-identities).
GNU AArch64 objdump inspection confirms the host-1 IES mask `0x7e000000`
at offset `0x20`, the SMT mask `0x7` at offset `0x30`, and the drive helper's
separate tune-field write described above. This checks compiled offsets/masks,
not that these functions executed on the current boot.

| Symbol | Start | Exclusive next-symbol end | Image-slice SHA-256 |
| --- | --- | --- | --- |
| `msdc_set_smt_by_id` | `0xffffffc000977878` | `0xffffffc000977950` | `f54a8ca02d245219f4a53016b0c08eacd65f3d2f3a85e25843497e6bcdc460a6` |
| `msdc_set_ies_by_id` | `0xffffffc000977950` | `0xffffffc000977a28` | `9dd95068eaf41b5e2a8aa0c5bdf7f340a65b52c39cf3c4a75ae01d8123f88c73` |
| `msdc_set_driving_by_id` | `0xffffffc000978638` | `0xffffffc000978910` | `fa2c78180d3ef193d900e60a8de524d58a4ef49f1e4e8ecdadfe410507bab4e1` |

Only facts and hashes are published; retained binary bytes remain private.
