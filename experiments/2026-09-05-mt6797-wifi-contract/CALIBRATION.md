# Selected gen3 calibration and regulatory input contract

This offline slice follows `054b4ec830b7f6f849faca7b842a3a210dc01867`.
It asks which record the selected MT6797 host driver consumes, what it checks,
and whether its fallbacks establish safe radio operation. **They do not.**
The result is a pinned source contract and a pure record inspector, not an
active radio candidate or a claim about firmware enforcement on Gemini.

All vendor references use Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`, below
`drivers/misc/mediatek/connectivity/wlan/gen3/`. The inspected files carry
GPLv2 notices. This document describes their interfaces independently; it
does not import vendor implementation, calibration, identifiers or defaults.
The installed Gemian driver has not been proved identical to this source.

## Retained-input reconciliation

The [July 14 backup](../2026-07-14-mmc-partition-backup/README.md) includes
`nvram`, `nvcfg`, `nvdata`, `protect1` and `protect2`; the earlier firmware-file
inventory excluded those inputs. This slice verified the private manifest's
checksum and each of those five complete images against its recorded full
SHA-256, exact size and successful capture status. The capture directory is
mode 0700 and the files are owner-only, owned by the current account and not
symlinks. [Sanitized receipt](results/calibration-backup-inventory.json).

No image was copied, mounted or extracted; hashing did not inspect record
contents. Private checksums and manifests remain private. The capture was
not an atomic filesystem snapshot. A verified image is retained evidence,
not proof that a particular record is current, coherent or applicable.
No new acquisition is needed for this source-contract slice.

## Consumer and fixed record layout

The selected build includes `os/linux/platform.c`. Its reader opens
`/data/nvram/APCFG/APRDEB/WIFI` and requires each requested two-byte read to
return exactly two bytes. `WIFI_CUSTOM` is defined nearby but is not selected
by this reader. The code does not directly consume a GPT partition, parse an
NVRAM database or establish which service restores that file. Mapping a
verified retained filesystem record to this path remains unresolved.
[Build selection](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/Makefile#L126),
[file reader](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/platform.c#L389).

The active `WIFI_CFG_PARAM_STRUCT` has exactly 512 bytes in two 256-byte
halves. The historical `MT6620` type alias does not establish MT6620 silicon.
Offsets below describe the selected 5GHz-enabled layout; scalar version
words are decoded little-endian by the host model.

| Byte offset | Extent | Selected field or group |
| --- | --- | --- |
| 0, 2 | Two 16-bit words | Part-one own and peer versions |
| 4 | 6 bytes | Per-device MAC address; never emitted |
| 10 | 2 bytes | Country input; never emitted or treated as approval |
| 12 | 40 bytes | Base transmit-power parameters; opaque here |
| 52 | 144 bytes | EFUSE override mapping, including a 16-bit signature field at 60 and conditional calibration groups |
| 196–201 | 6 bytes | TX-power validity, 5GHz support, 2.4GHz band-edge flag and limits |
| 202, 203 | Two bytes | Regulatory map selector and table index |
| 204 | 36 bytes | Six custom subbands, six bytes each |
| 240 | 16 bytes | Reserved part-one tail |
| 256, 258 | Two 16-bit words | Part-two own and peer versions |
| 260–267 | 8 bytes | Bandwidth flags, 5GHz enable, RX diversity, RSSI offsets/validity and GPS desense |
| 268–511 | 244 bytes | Feature word, reserved byte and tail |

Compile-time assertions establish total size, second-half offset and selected
alignment. Neither these assertions nor the field named `u2Signature`
establish an integrity check: no checksum/signature verification was found
in the audited host load path. Firmware interpretation of the complete
record remains unknown. The image CRC in [FIRMWARE_FORMAT.md](FIRMWARE_FORMAT.md)
is a different format and supplies no NVRAM checksum algorithm.
[Layout and assertions](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/CFG_Wifi_File.h#L224).

## Checks and fallbacks actually enforced by the host

| Source behavior | Consequence for a new implementation |
| --- | --- |
| `glLoadNvram` marks data available after reading only the last word. Later field/full-record reads ignore their return values. Version reads also ignore failures. | Obtain one complete, coherent, independently attributed record; final-word readability is insufficient. |
| Driver own version is `0x0200`, peer version `0`. Either record peer version above `0x0200` returns failure from `wlanLoadManufactureData`; unsigned record-own lower-bound checks against zero cannot reject anything. | Compatibility is a narrow software predicate, not format provenance or calibration validation. |
| Adapter startup ignores the manufacture function's result and only warns if data is absent. | The vendor path does not provide a reliable stop before radio operation. Actual firmware behavior is unverified. |
| Part-one own version 1 forces the TX-power-valid flag and skips the usual base-power command. Otherwise a zero validity flag skips that command. | Preserve this as historical behavior; never generate an RF default or infer valid power values from the flag. |
| Edge, channel-offset, RSSI and AC-power flags use zero/nonzero truthiness. Commands generally request no reply; their submission results are ignored, including the final complete-record submission. | Record flags do not establish successful firmware application. Canonical 0/1 encoding would be added policy, not a vendor requirement. |
| 5GHz eligibility tests record enable/support flags and the stored hardware-disable flag; capability-query failure is not propagated. Loading 5GHz parameters precedes the latter eligibility checks. | Record flags alone cannot identify radio capabilities or a no-transmit state; even a successful capability observation is not enforced by this source path. |
| Invalid MAC input may fall back to an embedded or generated address. Configuration errors become synthetic scan-list warnings and the checker returns success; its caller runs after scan completion. | An address or warning-free scan list does not prove factory calibration, and the warning path is not an admission gate. |

Primary control-flow references:
[availability](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/gl_init.c#L562),
[versions](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/version.h#L73),
[ignored manufacture result](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L655),
[manufacture commands](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L4056),
[address fallback](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L3121),
[warning result](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L4682),
[post-scan caller](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/gl_kal.c#L3336).

## Regulatory input is not regulatory approval

Map selectors are country 0, table index 1 and customized 2. The selected
source has 22 domain entries; invalid indices or unrecognized selectors fall
through to country lookup. Unknown country uses default entry 21, which has
populated 2.4GHz and 5GHz channel ranges. Custom subbands are used directly.
Enumeration filters disabled 5GHz and optionally DFS, without a calibration
validity gate. These are historical host choices, not verified legal limits
or a safe policy for Gemini.
[Selectors](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/wlan_lib.h#L195),
[domain selection](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/rlm_domain.c#L666).

The enabled country-power checker examines compiled tables, not this record.
Its duplicate check only logs; its validity result feeds the warning path.
Unknown country selects a zero-country default with power fields set to 63
and produces zero power-limit entries. Neither that sentinel nor successful
unacknowledged command submission proves a safe emission limit. The custom
Linux regulatory/channel handling and host configuration country override
also prevent treating record country bytes as the sole authority.
[Power-table checking and selection](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/rlm_domain.c#L1284),
[compiled default](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/mgmt/rlm_txpwr_init.h#L989),
[Linux channel update](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/gl_init.c#L1245),
[country override](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L5708).

## Pure validator and limits

[`wifi_nvram.py`](scripts/wifi_nvram.py) accepts exactly one independently
isolated immutable 512-byte record plus required driver-version context.
Optional firmware versions must be supplied together. It reports source
version predicates, the base-power branch, a MAC usability predicate and
record 5GHz flags, without emitting identifiers, country, calibration values,
reserved bytes, hashes or input data. It does not parse custom channels,
validate calibration ranges or invent a signature/checksum test.

Malformed framing/context raises a fixed `Refusal` code. A semantic mismatch
is reported as such; even all-zero bytes can satisfy the vendor's permissive
version test and still have **unproven calibration**. Every result denies
loading/transmit authorization. The CLI prints a static contract and refuses
all arguments without echoing them; it has no input-file or device API.

The [23 synthetic tests](scripts/test_wifi_nvram.py) cover all 512 truncated
lengths, extra/batched records, required contexts, both version halves and
boundaries, ignored private payload, all nonzero validity flags, legacy
override ordering and absent firmware/hardware evidence. Fixture bytes are
test constructions, never RF defaults. Run with:

```sh
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_nvram.py
```

Independent source/code review found no validator defects; its documentation
review corrected the distinction between a stored capability flag and a
successful query. The common repository gate and new-file publication review
passed. [Validation receipt](results/calibration-validation.txt). No kernel
input changed, so no kernel build, checkpatch or DT-schema run was needed.
The Linux-only artifact-provenance fixture was not run on macOS and remains
mandatory in CI. No device test was performed.

No retained calibration record was parsed. The specific remaining input
dependency is the producer/restoration and filesystem identity of the `WIFI`
record, followed by its exact board/firmware applicability and actual
application contract. This can be investigated from verified retained
evidence without new acquisition. The [shared ownership](OWNERSHIP.md) and
authenticated A53 recovery prerequisites remain independent blockers to
active radio work. Ordering remains with [the roadmap](../../docs/ROADMAP.md).

## Exact source identities

SHA-256 values refer to raw files at the pinned commit. Re-fetch and compare
before relying on a different revision; no Linux tree is needed.

| Path below gen3 | SHA-256 |
| --- | --- |
| `Makefile` | `5e099f94e6c79593a9210b97096646d2d8e2b0ddd7110a8870519b3dd5c49204` |
| `os/version.h` | `42b36412b3a9298063fad63f8de51fd71345e045326fc849cc714c8c19f41d21` |
| `include/config.h` | `c773b8e5e07978d60565c2eeee976dae3e285ecb9152062fe3bb50b1358a1c32` |
| `include/CFG_Wifi_File.h` | `f65877529e37df1f63792f59b538f16980af47bdbe4d51cbce47ce8738cd9dbd` |
| `include/wlan_lib.h` | `82680ed2fba541a751b63d01aa9d18b8414929e4e4eba74d44fe36d1c531172c` |
| `include/mgmt/rlm_domain.h` | `b0d57b3bcc6a071592b138a868ed6892c1272914327fd2dd45dc624a3f3eb4ec` |
| `include/mgmt/rlm_txpwr_init.h` | `d6c575ea68714645b57487a9899d09c898dff6ee22ce663dd1e684d72906d957` |
| `os/linux/platform.c` | `f6c8b02d1af757c91143ebee83f240469a274a4c9949f96543a649281f0d2090` |
| `os/linux/gl_init.c` | `8a644f0c9f3e37c6f66654cf3aeecb8e5f4cd71405e67f79105da7c8f87a7665` |
| `os/linux/gl_kal.c` | `749c5fc0e6cf3614d15e237e2d65cf92858d483ef1d678f6d9aee0f87bf348f1` |
| `common/wlan_lib.c` | `56bf99536fcb96de5a5198943aec96c9efccb8af89261b29c62046e6560c422f` |
| `mgmt/rlm_domain.c` | `8f3ff17db935ca1e47943a5437ca788a9fa8fa585bbb7c6f8c2a7f4f87612650` |
