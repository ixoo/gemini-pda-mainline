# MT6797 MSDC1 drive-strength fields

Status: unsigned upstream-preparation checkpoint. Strict checkpatch, isolated
Buildbox compilation and focused schema validation pass. No device candidate.

## Change and evidence

The [pad map](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md) identifies
three drive-selector fields for GPIO129–134 at IOCFG_B offset `0x1b0`:
CMD bits 23:21, DAT0–3 shared bits 26:24, and CLK bits 29:27. The
[driver patch](../../patches/upstream-4d7d9486/pinctrl/0004-pinctrl-mediatek-MT6797-MSDC1-drive-fields.patch)
adds those fields, selects `DRV_GRP4` for these six pins, and uses the existing
rev1 drive callbacks. Requests on other pins remain unsupported. The data pins
share one physical field; conflicting per-pin requests cannot be independent.

The pinned vendor GPIO setter independently clears and sets only each pin's
DRV field. Its ordinary branch uses the clear/set aliases; its bring-up branch
uses masked reads/writes. Neither branch adds the MMC helper's bias-tuning
operation. The GPIO field table agrees with the MMC map and assigns each of
these six pins a three-bit field. The MMC source documents selectors 0–7 as
2–16 mA in 2 mA steps, which matches `DRV_GRP4`, not the current `DRV_GRP3`.
These current labels are source evidence, not measured pad currents.

The [binding patch](../../patches/upstream-4d7d9486/pinctrl/0003-dt-bindings-pinctrl-mediatek-MT6797-drive-strengths.patch)
allows the missing 6, 10 and 14 mA settings for MT6797. Its shared schema keeps
MT6779's original allowed values through the existing compatible conditional.
No new binding property or pinctrl callback is introduced.

The drive mask excludes the five-bit bias-tuning field at bits 20:16. This
provider topic preserves that field; it does not implement the complete MMC
pad/power sequence. No board state is selected, and none of this resolves the
bias tune, PMIC trim, Schmitt direction or actual card-test prerequisites.

## Validation and reproduction

[Source inputs](source-inputs.json) pin the upstream and public vendor files.
Only independently described facts are used from the vendor source. Upstream
review files retain their existing authorship and license notices. Strict
checkpatch passes with only `MISSING_SIGN_OFF` excluded. A bounded public
search found no matching six-pin drive-field topic; refresh target-tree overlap
and maintainer discovery before submission.

The isolated profile selects the binding and driver patches in canonical order,
without the separate IES or Schmitt-refusal topics. All 203 existing profiles
and their series remain unchanged.

```sh
KERNEL_PROFILE=mt6797-msdc1-drive-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-msdc1-drive-compile ./scripts/buildbox fetch-package
```

The [compile receipt](compile.json) records the validated build from
`a56e97f65a4f67b4318ebd8cdf7e06e1a8001e9a`. Prepared driver, descriptor header
and binding hashes match the reviewed files. The compiled 60-byte field table
contains exactly the three intended ranges, including the shared-data flag.
Both drive callbacks have object relocations and linked symbols. There were
no compiler warning/error lines; remote package validation and fetched
inventory/checksums passed. Module linkage was not tested.

The [validation receipt](validation.json) records the remaining focused checks:

- A host probe executes the exact upstream rev1 drive callbacks and drive-group
  table with an injected register word. All 182 cases pass: six pins, eight
  valid strengths and three initial words; six invalid strengths for each pin;
  and both adjacent unsupported pins. Valid requests round-trip, preserve bits
  outside their field (including bias tune), and share DAT0–3 readback. Invalid
  requests perform no writes. Separately, the source field descriptors and six
  drive groups match the vendor map. This models selector/control flow, not
  electrical current, actual MMIO or concurrent consumers.
- Focused `dt_binding_check` passes schema, lint and style completion markers
  and compiles the existing example. A direct example validation is silent.
  Synthetic DTBs test every integer from 0 through 18 mA for both compatibles:
  MT6797 accepts all eight even strengths from 2 through 16; MT6779 accepts
  only 2, 4, 8, 12 and 16. All other tested values are rejected for drive
  strength. The preliminary fixture corrections are recorded in the receipt;
  the final 38-case run passed in full.

Schema validation uses the existing
[pinned tool environment](../2026-09-05-mt6797-infracfg-upstream-preparation/schema-tools-requirements.lock).
On Buildbox, put that environment's `bin` directory on `PATH` and run against
the prepared source/output pair:

```sh
make -C "$SOURCE" O="$OUTPUT" ARCH=arm64 \
  DT_SCHEMA_FILES=mediatek,mt6779-pinctrl.yaml dt_binding_check
dt-validate -s "$OUTPUT/Documentation/devicetree/bindings/processed-schema.json" \
  -l mediatek,mt6779-pinctrl \
  "$OUTPUT/Documentation/devicetree/bindings/pinctrl/mediatek,mt6779-pinctrl.example.dtb"
```

Repository publication checks pass; the usual Linux-only provenance fixture
remains deferred to CI. No device access, pad transition or card test occurred.

## Upstream boundary

Destination: pinctrl and Device Tree, with MediaTek review. Actual authorship
and truthful DCO certification remain required; the synthetic archive identity
does not certify these patches. No submission was sent. Remove the local topic
when equivalent support enters the selected upstream baseline; card and pad
transition validation remain required before board enablement.
