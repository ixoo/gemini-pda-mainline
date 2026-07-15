# Experiment: Linux 7.1.3 MT6797 upstream coverage census

## Question

Which MT6797-related source blocks already exist in the pinned Linux 7.1.3
tree, and which Gemini vendor blocks have no upstream implementation at all?

## Method and safety

The audit reads the Linux 7.1.3 source checkout, the local working series,
and the current packaged configuration. It classifies source paths containing
`MT6797` as either touched by the local series or not touched by it, then
checks explicit vendor-only block patterns. It is read-only: no source is
copied, built, loaded, or executed on hardware.

Run it in the VM with:

```sh
./scripts/dev-vm run env \
  CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-c2feb465d6c6 \
  experiments/2026-07-14-upstream-mt6797-coverage-audit/scripts/audit-source-coverage.sh
```

The focused controller comparison is reproducible with:

```sh
./scripts/dev-vm run experiments/2026-07-14-upstream-mt6797-coverage-audit/scripts/audit-i2c-controller-reuse.sh
```

The corresponding SPI comparison is reproducible with:

```sh
./scripts/dev-vm run experiments/2026-07-14-upstream-mt6797-coverage-audit/scripts/audit-spi-controller-reuse.sh
```

The live controller topology can be recaptured read-only with the fixed local
key and SSH options:

```sh
experiments/2026-07-14-upstream-mt6797-coverage-audit/scripts/probe-live-spi-dt.sh \
  --target gemini@192.168.1.50
```

The historical result used the pre-correction package and remains retained for
comparison. The corrected 72-patch package remains the source-census comparison
baseline:
[`results/mt6797-source-coverage-current-c2d-20260714.txt`](results/mt6797-source-coverage-current-c2d-20260714.txt)
(SHA-256 `be12372544b02a43d6c491c7efd72d34b661b30d74d8427e590aa515c05fb77e`).
The package correction changes only the panel module; the census itself is a
source/configuration classification and its vendor-only conclusions are
unchanged.

The same census was rerun against the current 74-patch SPI package
`linux-7.1.3-gemini-c2feb465d6c6`. It reports 74 MT6797-related source files
and 108 patch-touched paths; the only new MT6797 path relative to the prior
package is `drivers/spi/spi-mt65xx.c`, while the shared `mt6797.dtsi` hash also
changes for the six disabled SPI nodes. Two direct VM runs were byte-identical:
[`results/mt6797-source-coverage-current-c2feb-20260714.txt`](results/mt6797-source-coverage-current-c2feb-20260714.txt)
(SHA-256 recorded in the result).
The module-bearing package's display/input boundary is recorded in
[`mainline-display-input-current-74-package-20260714.txt`](../2026-07-12-input-backlight-recovery/results/mainline-display-input-current-74-package-20260714.txt);
it confirms packaged reusable modules but keeps all Gemini consumers disabled
and the vendor NT36xxx touch protocol unresolved.

## Interpretation

The census is a source-coverage map, not a runtime-support claim. Files that
already contain MT6797 data but are not touched by the local series are useful
reuse evidence; files touched by the series are local extensions or board
descriptions. An absent vendor-only pattern means that no direct MT6797
implementation was found in the scanned Linux subsystems, not that the block
is impossible to support.

The key boundary is consistent with the hardware evidence: Linux already has
generic or family support for clocks, audio, MMC, IOMMU/SMI, USB, DRM,
Panfrost, and standard input/sensor frameworks. It has no MT6797-specific
CONSYS/WMT/BTIF, CCCI/CLDMA/CCIF, SP5509, SENINF/CAM/ISP, NT36xxx, or
MT6797 CPU-DVFS implementation; those require new backends while preserving
standard subsystem interfaces.

The focused [I2C controller reuse result](results/i2c-mt6797-controller-reuse-20260714.txt)
compares the immutable Planet driver and device tree with Linux 7.1.3. Both
historical and current paths use the legacy `mt6577` register/quirk profile;
the current binding requires the `mt6797-i2c` plus `mt6577-i2c` compatible pair,
which the ten disabled Gemini nodes provide. The result therefore recommends
reusing `i2c-mt65xx.c`, not adding an MT6797-specific controller driver. This is
source and topology evidence only; a mainline runtime transfer remains an
open gate. Result SHA-256: `45693fc6e638cd283cdc1c92adbfcc3d20a83704103c00dd5190a4f79768eb5d`.

The [SPI controller result](results/spi-mt6797-controller-reuse-20260714.txt)
finds the same family-level reuse boundary: the vendor register contract
matches the existing Linux `mt6765_compat` profile, but Linux lacks the MT6797
compatible, clock/pad DT description, and pinctrl groups. The six live SPI
masters and the unbound `fpc1020` child are documented as topology evidence,
not as permission to enable a fingerprint driver. A subsequent read-only
device-tree probe confirmed the six live windows, IRQs, pad macros, and
`spi-main` clock names against the running vendor DT. Result SHA-256:
`855a1fa29f035ea1245e15518b2dd29e100193d5141fc54a2df0dfcd1faf4a8d`.

The implementation validation is recorded in
[`results/spi-mainline-patch-validation-c2feb-20260714.txt`](results/spi-mainline-patch-validation-c2feb-20260714.txt).
Patches 0072–0073 add the reuse alias and six disabled SoC nodes; the
corrected package built successfully, passed the SPI binding schema check, and
serializes all six nodes as `status = "disabled"`. Result SHA-256:
`271223f687a56ab529be3df0718052146c01b42f9feaacb3abe2a9bee4feb66e`.

The current 74-patch source recheck is preserved in
[`results/spi-source-reuse-current-74-20260714.txt`](results/spi-source-reuse-current-74-20260714.txt).
It confirms the same four `mt6765_compat` flags and clock/pad boundary against
the prepared 7.1.3 tree; the vendor-only `mt_chip_conf`, test, wake-lock,
address-remap, and DMA ABI remain deliberately out of scope.

The [SPI1 pinctrl contract](results/spi1-pinctrl-contract-20260714.txt)
recovers the vendor's GPIO234–237 `SPI1_*_B` mapping and its nine pinctrl
states. Four signal states switch explicitly between GPIO function 0 and SPI
function 1; the vendor default state is empty. This is a real compatibility
boundary: a mainline static function-1 group is plausible, but not yet proven
safe, so no pinctrl state machine or fingerprint child is enabled.

A fresh bounded post-reboot probe is recorded in
[`results/spi-live-postreboot-20260714.txt`](results/spi-live-postreboot-20260714.txt).
It reproduces the six controller windows/IRQs/pad macros and the `test_spi` /
unbound-`fpc1020` child topology byte-for-byte with the earlier probe. This
raises confidence that the recovered resource map is stable across the battery
depletion reboot, but it remains sysfs/Device-Tree observation only: no SPI
register was read, transfer was issued, GPIO was changed, or driver was loaded.

No runtime probe, firmware load, radio transmit, camera stream, or hardware
write was attempted.
