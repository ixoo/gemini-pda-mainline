# Experiment: Gemini kernel configuration gap audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-kernel-config-gap-audit` |
| Status | `completed` for configuration inventory; runtime support remains untested |
| Device | Gemini PDA running Gemian, vendor Linux `3.18.41+` |
| Mainline comparison | Prepared Linux `7.1.3` with the repository fragment |
| Date | 2026-07-12 |

## Question

Which vendor-enabled kernel options are already represented by Linux 7.1.3,
which are merely vendor policy/ABI switches, and which indicate an actual
mainline driver or data gap?

This prevents a misleading “enable every vendor option” migration. A vendor
symbol can describe a private Android ABI, a board policy, or an obsolete
implementation rather than a missing mainline feature.

## Provenance and safety

- Vendor configuration: private read-only capture at
  `artifacts/device-inventory/20260712-live/vendor-kernel.config`.
- Mainline configuration: the merged `.config` produced by
  `./scripts/kernel configure` for Linux 7.1.3.
- Local fragment: `configs/gemini.fragment`.
- The vendor capture is Git-ignored and contains configuration only; no keys,
  serials, firmware, or device data are included.
- The analyzer parses text and hashes inputs. It never changes the device,
  kernel config, source tree, or VM state.

## Reproduction

From the development VM:

```sh
python3 experiments/2026-07-12-kernel-config-gap-audit/scripts/analyze-config-gaps.py \
  --vendor artifacts/device-inventory/20260712-live/vendor-kernel.config \
  --mainline "$HOME/build/gemini-pda/linux-7.1.3/.config" \
  --fragment configs/gemini.fragment \
  > experiments/2026-07-12-kernel-config-gap-audit/results/config-gap-report.txt
```

The generated report records the input hashes and a bounded set of
hardware-facing options. Explicit `n` entries in the fragment are classified
as project policy rather than missing drivers. The current package comparison
uses the authoritative `linux-7.1.3-gemini-a9a7c5002038` package and is summarized in
[`results/current-validation.txt`](results/current-validation.txt). It is an
inventory, not a license to enable anything on hardware.

## Result

The captured vendor config has 351 relevant enabled options:

| Relation | Count | Interpretation |
| --- | ---: | --- |
| matched enabled | 96 | Same option is enabled in Linux 7.1.3; this is configuration evidence only |
| built-in/module delta | 22 | Packaging choice, not a driver identity difference |
| vendor option absent from mainline | 233 | Requires classification; most are vendor ABI, debug, Android policy, or obsolete implementation switches |

The prepared mainline config has the same hash recorded by the current package
metadata (`831289dd...`), while the live vendor capture is
`231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4`.
The fragment hash is `406f9ded...`; its one explicit unset entry is recorded
as project policy, not a request for a missing driver.

### Actionable mappings

| Vendor option | Mainline 7.1.3 interpretation | Driver consequence |
| --- | --- | --- |
| `CONFIG_MTK_WATCHDOG` / `CONFIG_MTK_WD_KICKER` | Replaced by `CONFIG_MEDIATEK_WATCHDOG=y` and the standard watchdog core | Reuse `mtk_wdt`; add board resources, not the vendor WDK ABI |
| `CONFIG_MTK_M4U` | Replaced by `CONFIG_MTK_IOMMU=y` plus MT6797 SMI/IOMMU data | Reuse the generation-two IOMMU framework; validate ports and ownership |
| `CONFIG_MTK_PMIC_WRAP` | `CONFIG_MTK_PMIC_WRAP=y` is already matched | Reuse the generic pwrap/provider layers; PMIC child and EINT data remain board work |
| `CONFIG_MTK_CMDQ` | `CONFIG_MTK_CMDQ=y` and `CONFIG_MTK_CMDQ_MBOX=y` are already matched | Reuse the mailbox core; keep normal/secure IRQ and thread contracts separate |
| `CONFIG_MTK_COMBO_*`, `CONFIG_MTK_BTIF` | No equivalent 7.1.3 symbol or transport binding | New MT6797 consys/BTIF/SDIO transport boundary; reuse STP/HCI layers only where proven |
| `CONFIG_MTK_WIFI_MCC_SUPPORT` and vendor Wi-Fi options | No MT6797 WMT/AP-DMA mainline option | New firmware-aware Wi-Fi MAC/HIF boundary; do not select `mt76` by family name |
| `CONFIG_MTK_USBFSH`, `CONFIG_USB_MTK_DUALMODE`, `CONFIG_USB_C_SWITCH_*` | Vendor USB11/Type-C policy, not a generic MUSB/Type-C match | Reuse MUSB/MTU3/PHY cores only after MT6797 SIF and board-switch contracts are modeled |
| `CONFIG_MTK_AUXADC`, `CONFIG_MTK_THERMAL_PA_VIA_ATCMD` | Generic Linux thermal/AUXADC symbols do not prove MT6797 sensor compatibility | Recover calibration and validity rules before adding a thermal driver/data record |
| `CONFIG_MTK_BMI160_*`, `CONFIG_MTK_AW9523` | Mainline has BMI160 and AW9523 building blocks, but no vendor option-name match | Use standard IIO/pinctrl plus DT consumers after identity and keymap evidence |

The current local fragment additionally selects `CONFIG_MTK_THERMAL=m` and
`CONFIG_MTK_SOC_THERMAL=m` for the disabled MT6797 thermal variant. This is a
mainline packaging decision, not a claim that the vendor `*_PA_VIA_ATCMD`
interface or its disabled thermal zones are equivalent.

The full row-level report retains the non-actionable vendor options so that
future driver work can explain why a symbol was intentionally not recreated.

## Conclusion

The configuration comparison confirms the repository’s reuse-first policy. The
mainline kernel already enables the generic foundations for several recovered
blocks, while the largest vendor-only clusters are exactly the private
connectivity, USB11, display, sensor, modem, and Android-policy surfaces
documented by the subsystem experiments. A missing vendor symbol is therefore
not, by itself, evidence for a new driver; the register/resource/ABI contract
determines that decision.

The next configuration change should add only a symbol required by a specific
reviewable patch and experiment. Do not turn on vendor WMT, WDK, Android
framebuffer, modem, factory-test, or firmware-loader options in the mainline
fragment.
