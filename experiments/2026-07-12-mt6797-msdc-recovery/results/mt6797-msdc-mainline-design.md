# MT6797 MSDC mainline design

Status: `inconclusive` for a current-mainline boot, but the controller
compatibility record and conservative Gemini DT boundary are source- and
hardware-audited. The live device was not booted with the local kernel during
this experiment.

## Reproducible source comparison

Run the source-only analyzer in the development VM:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-mt6797-msdc-recovery/scripts/analyze-mt6797-msdc-contract.sh
```

The analyzer reads vendor files from Git objects and emits hashes, register
anchors, Linux compatibility data, and the reuse decision. It never changes
MMC IOS, tuning, clocks, regulators, or card state.

Vendor evidence is Planet's MT6797 tree at commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`. Linux evidence is the prepared
`7.1.3` source in the VM.

| Source | SHA-256 |
| --- | --- |
| Vendor `msdc_reg.h` | `895415e03d287fd7c9f37b318927ad4f25694e5fac764108bb7ce238f5fe1f9c` |
| Vendor `msdc_io.c` | `b87966fb3bb7be7e9c7c273cc58e92e7c19ed6a3b09a503afbaedb529c890e07` |
| Vendor `msdc_io.h` | `e3c97a2930ac29dd46838c170c733fb05d5d87b5aa139ee7837da9b9f242ce65` |
| Vendor `msdc_tune.c` | `2e3cde55d6f6765ee1a523b9f6c99286be9c56cd2373bc6d488446d26e82de2d` |
| Vendor `sd.c` | `e8cc38b57f18b0a8c8e6476d3c11c333f999326297538d35e7f93585daf63cba` |
| Vendor `mt_sd.h` | `07270f8c4dd3fab89e51bead04b21d167c7bcf1013ba22394d706fae9c45505e` |
| Vendor `dbg.c` | `6d41d490914738425d4b5e2ce82dc2d493c7f5e8405719d197981edf84df06d6` |
| Vendor `mt6797.dtsi` | `eaac86c8752ebd8ddf18b831eb3bc52a08f87475a213bb521650bf95dabb3e5e` |
| Linux `mtk-sd.c` | `2044a80b01c0fc94091deeb5bf127ccc5d0b613fcb64ade2014d861f2813e876` |
| Linux `mtk-sd.yaml` | `a4eb5b4bc878141a0b6cc62c98cfa817ca31ea242624831ffcab7dc88668acf9` |

## Recovered hardware state

The live Gemian capture records:

| Property | MSDC0 / eMMC | MSDC1 / microSD |
| --- | --- | --- |
| Register window | `0x11230000 + 0x10000` | `0x11240000 + 0x10000` |
| IRQ | SPI 79, level-low | SPI 80, level-low |
| Clock | `CLK_INFRA_MSDC0` / 200 MHz active | `CLK_INFRA_MSDC1` / 0 Hz idle |
| Media | 64 GB-class SanDisk DF4064 eMMC | no card present |
| Bus/timing | 8-bit MMC HS400, 1.8 V | reset/legacy, 3.3 V |
| Controller ID | `0x20141118` | `0x20140512` |

Unique CID/CSD and serial fields are intentionally excluded. The runtime
capture also reports `MSDC_CFG=0x03700099`, confirming clock mode 3, divider 0,
and the HS400 bit; this is performance-ceiling evidence, not a reason to
enable HS400 on the first mainline boot.

## Compatibility decision

The MT6797 register map is close to newer MediaTek MSDC blocks but not a safe
`mt6779_compat` alias. Source and read-only register evidence support this
dedicated record:

| Linux compatibility field | MT6797 evidence | Decision |
| --- | --- | --- |
| `clk_div_bits` | `MSDC_CFG_CKDIV` is 12 bits | `12` |
| `pad_tune_reg` | `MSDC_PAD_TUNE0` at `0xf0`; live PAD_TUNE0 is active | `MSDC_PAD_TUNE0` |
| `async_fifo` / `data_tune` | vendor map and tuning code expose both | `true` / `true` |
| `stop_clk_fix` | offset `0x228` is `EMMC50_BLOCK_LENGTH`, not newer FIFO config | `false` |
| `enhance_rx` | no vendor `SDC_ADV_CFG0` at `0x64` | `false` |
| `busy_check` | downstream initialization selects the no-busy-check path; PATCH_BIT1 bit 7 is set | `false` |
| `support_64g` | vendor descriptors truncate addresses to 32 bits; live high-address register is zero and SUPPORT64G is clear | `false` |

The local patches implement this as `mt6797_compat` and add the
`mediatek,mt6797-mmc` binding match. This is reuse of the Linux MMC core and
`mtk-sd` protocol with a new SoC data record, not a new storage-controller
driver.

## Gemini DT boundary

The board DT enables only MSDC0/eMMC, with:

- 8-bit, non-removable bus;
- `max-frequency = 25000000` and no HS200/HS400 capability flags;
- VEMC as `vmmc` and the fixed 1.8 V VIO18 rail as `vqmmc`;
- the recovered GPIO114–125 MSDC0 pin group; and
- no MSDC1/card-detect or UHS voltage switching.

This is deliberately more conservative than the live vendor HS400 state. The
VEMC/VMC/VMCH selector relationship and shared VIO18 consumers are not yet a
mainline-validated regulator contract. A fixed-regulator shortcut could make
microSD voltage switching unsafe.

## Bring-up gates

1. Boot the conservative eMMC node read-only and verify rootfs discovery,
   repeated cold boots, and bounded sequential reads.
2. Confirm the VEMC selector and VIO18 ownership before increasing the clock or
   adding eMMC HS200/HS400 capability flags.
3. For MSDC1, identify card-detect polarity and debounce, validate GPIO67/EINT6
   wiring, and prove VMCH/VMC voltage transitions with an external recovery
   path.
4. Add UHS modes only after tuning results are recorded on the named hardware;
   do not infer them from the vendor DT advertisement.

The current source evidence supports the existing MT6797 `mtk-sd` compatibility
record and conservative board description. No new storage driver is warranted.
