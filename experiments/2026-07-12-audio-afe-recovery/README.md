# Experiment: Gemini audio AFE and MT6351 codec recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-audio-afe-recovery` |
| Status | `inconclusive` for mainline runtime support; live ASoC topology captured |
| Subsystem | MT6797 AFE, MT6351 codec, ASoC machine card, modem/Bluetooth PCM endpoints |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant not independently established |
| Date(s) | 2026-07-12 through 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Does Linux 7.1.3 already contain the correct MT6797 AFE and MT6351 codec
drivers, and what board/device-tree contracts are still needed to expose safe
ordinary ALSA playback and capture on the Gemini?

The working hypothesis is that this is a reuse boundary, not a new audio
silicon driver: Linux already has `mt6797-afe`, `mt6797-mt6351`, and
`mt6351-sound`, while the Gemini-specific work is the AFE clock/power graph,
MT6351 child node, machine-card phandle, external amplifier/jack wiring, and
separation of modem/Bluetooth voice links.

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Vendor DTS: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`, `arch/arm64/boot/dts/mt6797.dtsi`.
- Mainline comparison: Linux `7.1.3` in the development VM.
- Sanitized summary: [`results/runtime-summary.txt`](results/runtime-summary.txt).
- Fresh bounded read-only capture: private
  `artifacts/device-inventory/20260714-live/audio.txt` (whole-capture SHA-256
  `5144b01660c63bef45ac73a7426ff34ec351e2f4a26ddd013f11f545e2497719`). Its
  non-dmesg topology is byte-identical to the 2026-07-12 capture; only the
  volatile focused dmesg section changed.
- A concise status check is recorded in
  [`results/live-audio-idle-status-20260714.txt`](results/live-audio-idle-status-20260714.txt):
  all 40 observed PCM subdevices were closed, and no mixer utility was
  available for a read-only control inventory.
- Earlier focused compile result: [`results/mainline-audio-build.txt`](results/mainline-audio-build.txt).
- Source-contract result: [`results/mainline-audio-source-validation.txt`](results/mainline-audio-source-validation.txt).
- Current 72-patch package validation: [`results/mainline-audio-current-72-package-20260714.txt`](results/mainline-audio-current-72-package-20260714.txt).
- Superseded module-enabled package audit: [`results/mainline-audio-current-package-20260714.txt`](results/mainline-audio-current-package-20260714.txt).
- Private raw capture, if regenerated, belongs only under the Git-ignored
  `artifacts/device-inventory/20260712-live/` directory.

## Safety assessment

The collector is read-only. It reads `/proc/asound`, platform sysfs, the live
flattened device tree, `/proc/interrupts`, and filtered kernel messages. It does
not open PCM streams, change mixer controls, access codec registers, change
PMIC rails, or trigger modem/Bluetooth voice paths. Endpoint names are metadata;
they do not prove that speakers, microphones, or headsets were exercised.

## Associated code

Run from the repository root:

```sh
mkdir -p artifacts/device-inventory/20260712-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-audio-afe-recovery/scripts/collect-live-audio.sh \
  > artifacts/device-inventory/20260712-live/audio.txt
chmod 700 artifacts/device-inventory/20260712-live
```

The output must remain below the ignored `artifacts/` tree. Review it before
sharing: ALSA endpoint names can disclose enabled modem or Bluetooth paths.

## Associated source analyzer

The source-level comparison is read-only. It reads vendor files from Git
objects and compares the MT6797 AFE/MT6351 codec contracts with Linux 7.1.3:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-audio-afe-recovery/scripts/analyze-mt6797-audio-contract.sh
```

Its design record is
[`mt6797-audio-mainline-design.md`](results/mt6797-audio-mainline-design.md).
The source-only clock-consumer validation is preserved in
[`mainline-audio-source-validation.txt`](results/mainline-audio-source-validation.txt).
The source analyzer was rerun against the immutable vendor tree and prepared
Linux 7.1.3 source on 2026-07-14; the normalized hash record is
[`audio-source-validation-20260714.txt`](results/audio-source-validation-20260714.txt),
and the rerun was byte-identical. The current 72-patch package record confirms
that the AFE, codec, and machine drivers are selected as modules and the
artifact includes the matching 1,570-module tree. The AFE node remains disabled and
no machine-card/codec graph is represented. The repeatable current-package/DT
boundary audit is
[`mainline-audio-current-72-package-20260714.txt`](results/mainline-audio-current-72-package-20260714.txt).

## Current package boundary

The current reproducible package is
`linux-7.1.3-gemini-a9a7c5002038`. It selects `CONFIG_SND_SOC_MT6797=m`,
`CONFIG_SND_SOC_MT6351=m`, and `CONFIG_SND_SOC_MT6797_MT6351=m`; the AFE,
codec, and machine objects are packaged in the module tree (1,570 `.ko`
objects). The Gemini DTB
contains one disabled `audio-controller@11220000` node with the expected
`mediatek,mt6797-audio` compatible, SPI151, and eight clock names. It has no
machine-card node, codec graph, analog route, amplifier, or jack consumer.

Run the package audit from the VM:

```sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-a9a7c5002038 \
   experiments/2026-07-12-audio-afe-recovery/scripts/audit-current-package-audio.sh'
```

The audit is read-only and byte-repeatable. It confirms a strong existing
Linux silicon-driver reuse boundary, but does not claim a usable ALSA card;
no PCM stream, mixer/codec write, clock/rail transition, or hardware write was
attempted.

## Procedure

1. Confirm the key-only, noninteractive SSH path with `BatchMode=yes`.
2. Run the collector once while the device is idle; all PCM endpoints should
   report `closed` if their subdevice state is inspected separately.
3. Compare the live DT and endpoint inventory with the pinned vendor DTS and
   Linux 7.1.3's AFE, codec, and machine-driver source.
4. Do not run `aplay`, `arecord`, mixer writes, jack tests, or modem/Bluetooth
   call paths as part of this inventory. Those require a separate owner-approved
   functional experiment with volume and feedback stop conditions.

## Observations

- The live system has one ALSA card named `mt-snd-card` (`mtsndcard`). It
  exposes 31 PCM device numbers, including ordinary multimedia playback/capture,
  FM I2S, TDM debug capture, headphone impedance, Bluetooth voice, modem voice,
  and hostless/routing endpoints. The capture is enumeration evidence only.
- The 2026-07-14 capture reproduces the same card, PCM inventory, AFE platform
  node, vendor clock topology, and IRQ 183 observation. The only changed
  section is noisy battery-timer logging, so no new audio hardware identity is
  inferred.
- A separate idle-status probe found all 40 PCM subdevices closed. This
  confirms only that no audio stream was active during the probe; it is not a
  functional playback/capture result.
- The active audio platform node is `audio@11220000`, compatible
  `mediatek,audio`, with register aperture `0x11220000 + 0x10000` and SPI 151
  level-low. The vendor AFE child `mt_soc_dl1_pcm@11220000` uses a 4 KiB view of
  the same base and the same interrupt.
- The vendor DT exposes an audio clock provider (`#clock-cells = <1>`) and a
  28-clock `mt_soc_dl1_pcm` child. Its names cover AFE/DAC/ADC gates, APLL
  tuners, SCP audio power, infrastructure 26 MHz clocks, audio muxes, PLL
  dividers, and APMIXED APLL1/APLL2. This is a vendor component graph, not the
  modern mainline AFE node contract.
- Vendor pseudo-nodes include `mt_soc_codec_63xx`, dummy PCM, FM, HDMI,
  Bluetooth, modem, TDM, and routing components. The live tree does not expose
  a standard `mt6797-mt6351-sound` machine-card node or an explicit
  `mediatek,mt6351-sound` child phandle.
- The live interrupt table shows an active `Afe_ISR_Handle` line (GIC IRQ 183
  in the vendor kernel's global numbering). The vendor DT audio node's SPI is
  151; the different printed number is retained as an unresolved vendor IRQ
  naming/virtualization discrepancy, not silently reconciled.
- A separate vendor `mt6351` PMIC child is present under the pwrap and has the
  PMIC EINT contract documented by the MT6351 experiment. The source does not
  prove that the analog outputs are physically wired to the Gemini speaker,
  earpiece, microphone, headset detect, or an external amplifier.

## Linux 7.1.3 comparison

Linux already contains the relevant chipset drivers:

- `sound/soc/mediatek/mt6797/mt6797-afe-pcm.c` matches
  `mediatek,mt6797-audio`, maps the AFE aperture, requests the AFE IRQ, and
  uses runtime PM and the MT6797 clock helper;
- `mt6797-afe-clk.c` requests seven named clocks and selects the 26 MHz parent
  for the audio mux;
- `sound/soc/codecs/mt6351.c` matches `mediatek,mt6351-sound` as an MFD child;
- `mt6797-mt6351.c` matches `mediatek,mt6797-mt6351-sound` and requires
  `mediatek,platform` plus `mediatek,audio-codec` phandles.

The existing text binding lists eight AFE clock names, including
`mtkaif_26m_clk`. The MT6797 platform clock helper requests seven clocks for
its runtime-resume sequence; the ADDA DAPM graph separately declares
`mtkaif_26m_clk` as a `SND_SOC_DAPM_CLOCK_SUPPLY`, which ASoC obtains by name
from the same device. This is a split-consumer contract, not evidence of a
missing clock or a reason to invent a new AFE driver. It should be preserved
explicitly when the binding is converted to YAML.

The reproducible build configuration now prepares `CONFIG_SND_SOC_MT6797=m`
and `CONFIG_SND_SOC_MT6797_MT6351=m`; Kconfig resolves the shared
`SND_SOC_MEDIATEK` and `SND_SOC_MT6351` symbols. The AFE, machine, and codec
objects compile without warnings, but the board machine card and analog route
remain absent. The earlier focused result is recorded in
[`mainline-audio-candidate-validation.txt`](results/mainline-audio-candidate-validation.txt);
the superseded 71-patch package result remains in
[`mainline-audio-current-71-validation-20260714.txt`](results/mainline-audio-current-71-validation-20260714.txt),
while the current package boundary is recorded in
[`mainline-audio-current-72-package-20260714.txt`](results/mainline-audio-current-72-package-20260714.txt).

The deeper source audit confirms a strong silicon match, but also preserves two
integration hazards: the vendor parent AFE aperture is 64 KiB while Linux only
uses registers through `0x84c`, and the platform/DAPM clock consumers must keep
the eight-name binding split intact. The MT6351 MFD also
creates its sound cell from the core cell table. In the current MFD core, an
exact matching child with `status = "disabled"` suppresses that cell, while an
absent child still leaves a name-matched `mt6351-sound` platform device. The
Gemini DTS has no sound child, so keep the codec module and machine card
disabled until this boundary and the analog wiring are reviewed. The detailed
MFD matching audit is in
[`mfd-child-of-match-audit-20260714.txt`](../2026-07-11-mt6351-pmic-recovery/results/mfd-child-of-match-audit-20260714.txt).

## Analysis

The chipset match is strong enough to prefer the existing Linux ASoC drivers;
the source hashes and exact reuse boundary are recorded in
[`mt6797-audio-mainline-design.md`](results/mt6797-audio-mainline-design.md).
The missing work is board integration:

1. expose a disabled MT6797 AFE node with the exact eight-cell DT clock list
   expected by the binding, and preserve the seven platform-clock plus one
   DAPM-supply consumer split;
2. add the MT6351 sound MFD child and a disabled machine-card node with the
   platform/codec phandles;
3. recover the physical analog output/input graph, jack-detect GPIO/IRQ,
   speaker amplifier (if populated), and safe supply dependencies;
4. keep modem, Bluetooth, FM, ANC, and hostless vendor paths out of the first
   board card; they are separate transports and not proof of local analog audio;
5. enable the standard card only after a bounded playback/capture test with
   volume limits and an external recovery path.

No vendor audio implementation is copied into this repository. If a future
probe demonstrates an MT6797 codec or AFE register difference from the
existing mainline driver, add a new driver/data record and preserve this
reuse-first comparison.

## Conclusion

`inconclusive`: the live audio graph is enumerated and the exact MT6797/MT6351
mainline drivers exist and now build as modules, but no mainline audio DT
machine card or runtime test has been performed. The current evidence supports
the disabled-only AFE resource node in
[patch 45](../../patches/v7.1.3/0045-arm64-dts-mediatek-mt6797-add-disabled-audio-afe.patch),
not an enabled speaker/microphone claim.

## Follow-up

1. Preserve and review the eight-clock DT contract: seven clocks are consumed
   by the platform resume helper and `mtkaif_26m_clk` by the ADDA DAPM supply;
   keep the AFE resource disabled-only until the full card is reviewed.
2. Correlate analog codec widgets and external amp/jack GPIOs with board-level
   source or controlled read-only pinmux evidence.
3. Keep the MT6351 MFD sound cell inert while the board graph is incomplete;
   in this source revision, an exact disabled `mediatek,mt6351-sound` child
   suppresses the cell, while an absent child does not.
4. Package the ASoC modules and inspect probe logs in a disposable image; the
   current default package contains Image/DTBs while the focused objects are
   validated separately.
5. Test playback and capture separately at conservative volume/rate; test
   modem/Bluetooth PCM only in a separate connectivity experiment.
