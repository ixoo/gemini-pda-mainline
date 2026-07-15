# AW9523 mainline design record

This record compares the vendor keyboard implementation with Linux 7.1.3
without copying vendor code into the repository. It was generated from the
immutable Planet MT6797 source checkout using
[`analyze-aw9523-contract.sh`](../scripts/analyze-aw9523-contract.sh).

## Source identity

| Source | Revision/hash |
| --- | --- |
| Vendor tree | `c5b0be85017ad0c599725e8273842efdbecdd88a` |
| Vendor file | `drivers/misc/mediatek/aw9523/aw9523_key.c` |
| Vendor blob SHA-256 | `01599f2fc072145138bb87d0486841cd1f75e5ff8b0877e8cbfe2615db36da5f` |
| Linux file | `drivers/pinctrl/pinctrl-aw9523.c` from the pinned 7.1.3 tree |
| Linux driver SHA-256 | `82957ed806a73fa81fa37a31d53f8cd5897c610d0b3ad865b14f890e04d4a64b` |

## Silicon contract

The vendor driver reads register `0x10` and requires chip ID `0x23`. It uses
software reset register `0x7f` with value `0x00`. Linux 7.1.3's generic driver
uses the same registers and expected ID, and also implements the same port
mode, input/output state, configuration, and interrupt-disable register
families. This is sufficient evidence to reuse the upstream AW9523/AW9523B
silicon driver; a second Gemini-specific silicon driver would only preserve
the vendor ABI unnecessarily.

## Board consumer contract

The vendor keyboard configures P0 bits 0–7 as matrix rows and P1 bits 0–6 as
matrix columns. It enables P0 interrupts, disables P1 interrupts, and runs a
100 Hz high-resolution timer rescan. The standard Linux binding can represent
the same physical topology as an AW9523 GPIO/IRQ expander plus
`gpio-matrix-keypad`; the timer frequency is a consumer policy, not proof that
the expander needs a custom driver. The Linux 7.1.3 binding explicitly
requires `gpio-ranges` for this expander and documents the same row/column
pinctrl pattern used by the disabled Gemini candidate.

The current 7.1.3 implementation also provides the pinconf operations used by
that pattern: bias pull-up/down, input/output enable, output level, and
open-drain/push-pull drive (open-drain is limited to port 0). Its nested GPIO
IRQ domain defaults to `IRQ_TYPE_EDGE_BOTH` and rejects level-triggered child
types; the board's `IRQ_TYPE_LEVEL_LOW` property describes only the external
AW9523 INTN parent line. This is a compatible generic-driver contract, but
the parent EINT polarity and GPIO58 reset polarity still require a controlled
hardware test.

### Scan polarity correction

The vendor implementation makes the consumer-level electrical polarity more
specific than the topology alone suggests. It initializes P0 as inputs and P1
as outputs, then selects one P1 column by driving that column physically low
while the other seven columns are driven high. A low P0 row bit is treated as
the pressed state and a high bit as release. This is source-derived behavior,
not a direct electrical measurement.

Linux 7.1.3's `gpio-matrix-keypad` binding and driver can express that state
machine with `gpio-activelow` plus `drive-inactive-cols`: the former makes the
logical active value drive a physical low on both rows and columns, while the
latter keeps inactive columns driven high instead of floating as inputs. The
current disabled Gemini candidate in patch 0054 has neither property and marks
all descriptors `GPIO_ACTIVE_HIGH`; it therefore remains a topology/keymap
candidate rather than an electrically equivalent scan description. The
candidate must be corrected before enablement, then validated against one-key,
modifier, rollover, and wake behavior on hardware.

The vendor's 1 ms delayed interrupt work and 100 Hz retry timer are timing
evidence only. They do not justify copying its polling, suppression, or screen
notifier logic into the generic driver. The complete source-vs-candidate
comparison is recorded in
[`keyboard-polarity-contract-20260714.txt`](keyboard-polarity-contract-20260714.txt).

Current source hashes used for this recheck are:

| Linux source | SHA-256 |
| --- | --- |
| `drivers/pinctrl/pinctrl-aw9523.c` | `82957ed806a73fa81fa37a31d53f8cd5897c610d0b3ad865b14f890e04d4a64b` |
| `Documentation/devicetree/bindings/pinctrl/awinic,aw9523-pinctrl.yaml` | `a216e57537cc3c14c2a7f00da51f87a0b089b2c6f4907f07cf687104dd0b653d` |
| `drivers/input/keyboard/matrix_keypad.c` | `a593777db9fb8b3f07054605f5b387461abe7eb52127103aad7b90de3d039b70` |
| `Documentation/devicetree/bindings/input/gpio-matrix-keypad.yaml` | `8aa5453a692c1783b5066f731a1c10dc03ceda9948370f807da6d937e786f9aa` |

The retained source keymap contains 56 matrix positions in an 8-by-7 matrix:
52 positions have assigned Linux key codes and four are retained as
`KEY_UNKNOWN` spare positions. The vendor maps the physical page-down/page-up
keys to `KEY_DOWN`/`KEY_UP` rather than the distinct page-key codes. The
exact active boot ELF independently recovers the same table but compiles the
physical `(row=4,col=3)` record as `KEY_LEFTMETA` rather than the retained
source's `KEY_FN`; the active normalized table is in
[`keyboard-keymap-active-boot.txt`](../results/keyboard-keymap-active-boot.txt),
while the retained source table remains in
[`keyboard-keymap.txt`](keyboard-keymap.txt).
The disabled DT candidate's `MATRIX_KEY()` entries are checked against the
active table by [`validate-keyboard-keymap.py`](../scripts/validate-keyboard-keymap.py);
the current result is
[`keymap-consistency-active-boot-20260714.txt`](keymap-consistency-active-boot-20260714.txt).
The ELF anchors and hashes are in
[`active-aw9523-elf-keymap-20260714.txt`](active-aw9523-elf-keymap-20260714.txt).

## Remaining gates

- The live chip-ID byte was not retained in the sanitized capture; the bound
  address and source-level identity are strong but not a direct readback.
- GPIO58 is the vendor shutdown/reset control and GPIO87 is EINT10. Their
  active polarity and mainline pinctrl states need a controlled board test.
- Row/column electrical polarity, debounce, scan delay, and wake behavior need
  one-key-at-a-time validation before enabling a DT consumer.
- Keep both the AW9523 node and matrix keypad disabled until those gates pass.
