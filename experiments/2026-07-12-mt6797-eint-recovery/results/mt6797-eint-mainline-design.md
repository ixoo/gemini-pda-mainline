# MT6797 EINT/pinctrl boundary for Linux 7.1.3

## Result

The MT6797 EINT block should reuse Linux's generic MediaTek `mtk-eint` and
Paris pinctrl machinery, but its SoC data and GPIO-to-EINT map are genuinely
MT6797-specific. The vendor pinctrl header cannot be treated as a complete
map: ordinary pins are marked `NO_EINT_SUPPORT`, and its EINT offsets are
commented out. The vendor DT and live device-tree capture provide the
authoritative controller resource and board wiring evidence.

The local series therefore adds a dedicated EINT data record and recovered
map, adds the EINT resource to the existing pinctrl node, and represents the
PMIC and built-in inputs as virtual GPIOs. This is a compile/schema result;
the controller remains untested at runtime on the Gemini.

## Provenance

The source-only analyzer is:

```sh
./experiments/2026-07-12-mt6797-eint-recovery/scripts/analyze-mt6797-eint-contract.sh
```

It uses the pinned Gemian reference commit `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
The relevant vendor blob IDs are:

| Evidence | Git blob ID |
| --- | --- |
| `drivers/pinctrl/mediatek/pinctrl-mt6797.c` | `8095e08ee2dd40cb9fa43a7f1e8e1d81526605ad` |
| `drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h` | `bbd077eff42954dddfbc81e6628702bd4038d473` |
| `arch/arm64/boot/dts/mt6797.dts` | `35e6938650c50d24604ce1258c580cd021e4b344` |
| `arch/arm64/boot/dts/cust_eint.dtsi` | `76fed6f93cef6226c69f5f4549ad5f45c178e79e` |

The local implementation is carried by patches 0004–0006 in `patches/series`.
The existing PMIC recovery record contains the sanitized decoded summary in
[`results/eint-summary.txt`](../../2026-07-11-mt6351-pmic-recovery/results/eint-summary.txt).

## Recovered hardware contract

| Property | Evidence and interpretation |
| --- | --- |
| EINT resource | `0x1000b000`, size `0x1000`; parent GIC SPI170, level-high |
| Capacity | 192 EINT channels in six banks (`port_mask=7`, `ports=6`) |
| GPIO map | 172 downstream table entries: 171 physical GPIOs plus pseudo-GPIO262→EINT176 |
| Hardware debounce | 16 channels; timing values 128, 256, 512, 1024, 16384, 32768, 65536, 131072, 262144, and 524288 microseconds |
| Direct routing | Four optional parent SPIs 206–209; no captured consumer uses them |
| Built-in input | EINT186 selected by alternate mux on GPIO61, GPIO93, GPIO107, or GPIO181 |
| Board candidates | GPIO67→EINT6 (microSD), GPIO85→EINT8 (touch), GPIO88→EINT11 (ALS/proximity), EINT10 (AW9523 keyboard) |

The PMIC signal is not a physical GPIO. It is downstream pseudo-GPIO262,
which maps to EINT176 and requests level-high with a 1000-microsecond
debounce. The physical GPIO register range remains GPIO0–261. The local
header's `GPIO262` and `VEINT186` entries have null mux functions so generic
resource setup does not write nonexistent GPIO mode/direction registers.

## Vendor versus Linux boundary

The vendor DTS declares the EINT controller as a separate `mediatek,mt-eic`
node and contains the debounce/direct-routing properties. In contrast, the
vendor `pinctrl-mt6797.c` leaves its EINT offsets commented (including a stale
`ap_num = 224`) and the vendor pin header marks ordinary pins
`NO_EINT_SUPPORT`. The old board files therefore express consumers using raw
EINT numbers, not a complete modern pinctrl map.

Linux 7.1.3 supplies the reusable pieces:

- generic status/ack/mask/sensitivity/polarity/soft-trigger/debounce register
  operations;
- chained IRQ and IRQ-domain handling, including wake configuration;
- MediaTek virtual-GPIO handling for internal PMIF/USB-style EINT inputs;
- the Paris pinctrl register model and the MT6797 pinmux/drive tables.

The new MT6797 data must provide the channel count, bank layout, timing table,
and every captured GPIO mapping. No adjacent SoC's map is a safe substitute.

## Contradictory board assignments

The downstream `cust_eint.dtsi` is not a Gemini board binding. It contains
alternative labels and raw lines such as MSDC1 `<5>`, touch `<10>`, ALS `<65>`,
and gyro `<67>`. The live Gemini capture and pinmux evidence instead correlate
microSD with GPIO67/EINT6, touch with GPIO85/EINT8, and ALS/proximity with
GPIO88/EINT11. Both sets are preserved as evidence; only the live correlation
should drive the first controlled Gemini test, and even that remains a
candidate until an interrupt is observed.

## Bring-up gates

1. Enable only the EINT controller and pinctrl resource; verify probe, parent
   IRQ registration, and no unexpected interrupt storm.
2. Test one physical consumer at a time: keyboard (EINT10), touch (EINT8),
   microSD card-detect (EINT6), then ALS/proximity (EINT11). Confirm mux,
   polarity, mask/ack, and one event per stimulus.
3. Test the MT6351 pseudo-GPIO262/EINT176 path separately, including the
   1000-microsecond debounce request and wake behavior. Never treat GPIO262 as
   a normal output-capable pin.
4. Leave direct GIC routing and built-in EINT186 disabled until a consumer
   identifies the required alternate mux mode and wake semantics.
5. Only after those tests add board consumers and promote support status; a
   successful compile or schema check is not hardware support.

## Validation boundary

The map decoder mechanically checks the private capture against the authored
Linux header. The focused pinctrl object, DT binding, and full Linux 7.1.3
series build have passed in the VM. No mainline kernel image has been booted,
and no EINT line has yet been stimulated under Linux 7.1.3.
