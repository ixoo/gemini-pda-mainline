# MT6797 calibration provider design boundary

This note records the next implementation boundary without enabling a thermal
node or copying device calibration values. It is based on the pinned vendor
tree (`c5b0be85017ad0c599725e8273842efdbecdd88a`), retained LK tree
(`f4988d74bb70a0a15d7f362f412afba7e7fcda46`), and Linux 7.1.3 package
`linux-7.1.3-gemini-a9a7c5002038` (guest-only; provenance is recorded in the
provider build result).

## Wire contract

LK's `target_atag_devinfo_data()` creates the following opaque property and
installs it at `/chosen/atag,devinfo`:

| Property word(s) | Meaning | Evidence |
| --- | --- | --- |
| 0 | ATAG word count: 103 | `lk/platform/mt6797/atags.c`, `tag_size(tag_devinfo_data)` |
| 1 | tag ID `0x41000804` | same source |
| 2–101 | 100 `get_devinfo_with_index()` values | same source |
| 102 | payload count: 100 | same source |

The property is passed to `fdt_setprop()` as a byte buffer. It is not a
`/bits/ 64` or normal Device Tree cell array; on this little-endian platform,
the words are little-endian opaque bytes. The vendor devinfo parser subtracts
the three header/trailer words, then copies words 2–101 into its array. It does
not map the `efusec` resource.

The thermal driver consumes these array indexes:

| Thermal extraction position | Devinfo index | Source bitfields |
| --- | ---: | --- |
| `buf[0]` | 32 | ADC gain/offset, VTS3, ID |
| `buf[1]` | 31 | VTS1/VTS2, DEGC, calibration-enable, slope |
| `buf[2]` | 33 | VTS4/VTSABB |

Consequently, a future NVMEM cell cannot simply expose an ascending 31–33
slice unless the extractor changes. It must either provide the ordered tuple
`[word32, word31, word33]` or parse the full payload by index.

## Candidate Linux boundaries

1. **Direct MT6797 MMIO efuse provider — not accepted yet.** Linux 7.1.3's
   `mtk-efuse` provider reads mapped bytes and has no MT6797 match. The vendor
   AUXADC source contains a direct efuse reader only under `EFUSE_CALI`; the
   MT6797 header leaves that guard disabled. No source evidence establishes
   the thermal words' live MMIO read sequencing, clock/power ownership, or
   reset safety.
2. **Bootloader-backed read-only NVMEM provider — implemented.** Patch 0057a
   validates the final `/chosen/atag,devinfo` property early, retains only the
   three bounded thermal words, and exposes a read-only provider/cell with the
   explicit ordered calibration layout. It refuses registration on missing,
   short, oversized, wrong-tag, wrong-size, or malformed input. The provider
   object, Gemini DTB, and focused binding schema pass in the VM; runtime LK
   handoff evidence is still pending.
3. **Thermal-local parser — fallback.** The MT6797 thermal driver could parse
   the chosen property directly and avoid an artificial NVMEM device. This is
   smaller, but less reusable and would make the bootloader ABI part of a
   thermal driver rather than a named firmware-data provider.

## Required invariants before enablement

- The final LK/FDT handoff preserves `/chosen/atag,devinfo` on every supported
  Gemini boot path.
- Parsing checks property length before subtracting the three-word overhead,
  checks `tag == 0x41000804`, requires the exact 103-word LK layout (or an
  explicitly versioned extension), and validates the trailing payload count.
- Words are decoded explicitly as little-endian; no C cast of an opaque FDT
  byte buffer is used as the ABI.
- The calibration consumer sees `[32, 31, 33]` in the order required by the
  MT6797 V4 extractor, and all GE/OE/VTS/DEGC validity checks remain active.
- Missing or invalid calibration must fail closed for the MT6797 thermal
  consumer. The generic driver's default values are not a thermal-protection
  policy.
- The provider is read-only, never maps or writes the efuse block, and does
  not expose raw calibration values through a new debug or sysfs interface.

The named Gemian device now provides a read-only structural confirmation of
the 103-word property shape and expected tag; the sanitized result is
`live-atag-devinfo-handoff-20260714.txt`. This is evidence for the retained
post-LK handoff, not proof of every boot path or of safe thermal consumption.
The synthetic validator and malformed-input tests are in
`scripts/validate-atag-devinfo-contract.py`; its result records the tested
wire shape without device values. The provider implementation and build
evidence are recorded in patch 0057a and
`mt6797-calibration-provider-build-20260714.txt`. Until the consumer's
invalid-calibration behavior is validated on a non-primary boot and the
handoff is checked across supported boot paths, both MT6797 thermal DT nodes
remain disabled.
