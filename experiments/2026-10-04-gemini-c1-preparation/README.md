# Gemini C1 PMIC, RTC and lid preparation

Initial offline integration audit, 2026-10-04, followed by the selected key
compile integration below. No boot candidate or device operation is admitted
by this record. The [roadmap](../../docs/ROADMAP.md)
owns priorities. The [source audit](results/source-audit.json) pins the selected
prepared driver files and the proposed baseline inventory.

## Selected foundation needs the reviewed key fixes

The `mt6797-a53-service-facilities` profile selects the Linux 7.1.3 service
foundation. It includes MT6351 key data and MFD resources, but not the separate
[seven-patch key correction topic](../2026-09-08-mt6351-keys-preparation/README.md).
Inspection of the exact `fcca630d` prepared source confirms three gaps:

- The IRQ handler ignores `regmap_read()` failure before reporting a key.
- Reset setup returns void, ignores `regmap_update_bits()` failure, and runs
  after input registration.
- `power-off-time-sec` is shifted directly into the timeout field. An eleven
  second property would select 3 (documented five seconds), rather than 1.

Integrate the already reviewed error and seconds-conversion changes onto this
selected foundation before enabling a key child. Do not append the independent
MT6351 data/MFD patches blindly: the selected tree already carries those data
and resources. Reuse the actual-function regression and its 94 duration/error
cases, then compile the integrated profile and check the relevant bindings.
The [reset-policy record](../2026-09-08-mt6351-keys-preparation/RESET_POLICY.md)
owns the mapping and the live policy admission gate.

Neither the retained configuration nor a successful `pmic_access` store/show
pair proves current reset fields. The [binary audit](../2026-09-08-mt6351-keys-preparation/RESET_BINARY.md#why-the-existing-debug-read-is-insufficient)
shows ignored transport errors and a shared cached result. Alternating reads
alone cannot turn that interface into attributable transport success. Keep the
key child disabled until the reviewed live observation resolves the policy.
No long press is part of the initial short-key event test.

## Baseline inventory and observation boundary

The PMIC H8 prose calls its subset nine registers, but enumerates ten:
`TOP_RST_MISC`, `STRUP_CON15`, three `TOP_CKPDN_CON` words,
`BUCK_VCORE_CON0`, `LDO_VDRAM_CON0`, and three `CHR_CON` words. The exact ten
addresses are in the audit. They come from the existing
[decoded source table](../2026-10-04-gemini-pmic-basics-re/results/pmic-init-setting-decoded.tsv)
and selected register header. This is an inventory, not read-safety proof.

Before implementing the probe-time observation, review read side effects and
regmap policy for each address. Define its position before child drivers can
change these settings, record each transport return alongside its value, and
stop on the first failure. Label the result loader-inherited state after the
wrapper's setup, rather than raw kernel-entry state. Exclude interrupt-status,
clear/set aliases, RTC mailbox and calibration windows. No vendor init-table
writes follow merely because a value differs.

## RTC and lid integration

The RTC child already exists in SoC DT through patch 0013; do not duplicate it.
The service foundation starts from a handoff fragment that disables RTC_CLASS.
A C1 fragment must explicitly enable RTC_CLASS and RTC_DRV_MT6397, and select
the relevant reviewed RTC alarm/error corrections. Audit the selected MFD IRQ
error handling against the independent MFD topic before claiming alarm delivery.
RTC access includes driver transactions; it is not a raw passive snapshot.

The disabled [hall candidate](../../patches/v7.1.3/0074-arm64-dts-mediatek-gemini-add-disabled-hall-gpio-keys-candidate.patch)
already describes GPIO66, active-low SW_LID and 64 ms debounce without a wake
source. A C1 profile can enable this existing node and build KEYBOARD_GPIO in;
keep event consumption separate from any userspace suspend-on-close policy.
The [lid record](../2026-10-04-gemini-lid-microsd-usb-re/README.md) owns polarity
and IRQ hypotheses. One close/open measures events, not suspend or wake support.

## Future attended packet

After consuming the installed version candidate and the reviewed Gemian
baseline, construct one explicitly validated C1 candidate. Preserve the current
PSCI power-off path and regulator/clock ignore flags. Capture the bounded PMIC
baseline, bindings and interrupt counts; then one short power-key press, lid
close/open, and a ten-second RTC alarm with the system awake. Suspend/wake is a
separate gate. Use the existing PSCI power-off with the charger detached before
considering a PMIC replacement.

C2a may share that boot only after its separate I2C/register-read review: no
charger driver bound, finite REG00–REG14 observation, and no boost or charge
policy writes. No automatic poweroff, recovery or other device command is
provided by this preparation record.

## Validation

The audit checked selected manifest/series membership and actual prepared key
functions/MFD resources, and parsed a ten-entry unique-address inventory.
Historical Buildbox receipts are evidence for their exact original inputs only.
The initial audit performed no build, schema test or hardware measurement.
The subsequent key integration results below are separate from that audit.

## Selected key integration

The four existing key error/duration patches apply unchanged to the selected
Linux 7.1.3 driver and binding. The new
[compile series](../../patches/series-a53-pmic-keys-compile) extends the service
foundation with only those four patches in canonical order. It omits the
independent topic's duplicate chip data and MFD additions. All 94 actual-function
regression cases pass against this integrated source; source hashes and limits
are in the [integration receipt](results/key-integration.json).

`mt6797-a53-pmic-keys-compile` adds only input/key compilation settings and a
release suffix to the service profile. DT is unchanged, with no enabled PMIC
key child; this does not select a hardware long-press policy. Buildbox
compilation, package validation and focused binding checks pass for input
`052f5937`. The existing patches retain their
synthetic non-certifying authorship and do not become submission-ready by
integration. Their upstream destination and deletion condition remain those
of the independent key topic.

```sh
KERNEL_PROFILE=mt6797-a53-pmic-keys-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-pmic-keys-compile ./scripts/buildbox fetch-package
```

The [receipt](results/key-integration.json) pins the compiled key object,
configuration, Image.gz, build log and validated package inventory. The driver
and binding in the exact prepared source match the host-tested hashes. Fetch
verification and local inventory/Image.gz rehashes pass. Input, keyboard and the
PMIC key driver are built in. DT and the installed candidate remain unchanged.
Only the inherited patch-0261 whitespace and unused CPU rollback callback
warnings appear; there is no new key-driver warning.

Focused kernel `dt_binding_check` passes with dtschema 2026.9 and separate
managed temporary output, which was removed afterward. The local binding
meta-schema and eight dtc-compiled fixture cases pass with dtschema 2026.6:
four MT6351 durations accepted, duration 1 rejected, legacy MT6331 duration 1
accepted, mode 3 rejected, and absent duration accepted. These schema fixtures
are offline descriptions, not admitted Gemini key nodes. No board DT changed,
so no new board `dtbs_check` was run. The Linux-only repository provenance
fixture is skipped on macOS; the actual package passed the remote Linux
validator. No boot image, installation, register access or physical reset was
performed. The live policy observation still gates key-node admission.
