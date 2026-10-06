# Experiment: audio H3, a first headphone card

| Field | Value |
| --- | --- |
| ID | `2026-10-06-gemini-audio-h3` |
| Status | Built and package-verified; DT derivation and protocol draft for review; not booted |
| Profile | `mt6797-a53-audio-h3-compile` |
| Date | 2026-10-06 |
| Device action | None |

## Purpose

[Audio H3](../2026-10-04-gemini-audio-re/README.md): a first mainline card
from parts that already exist upstream (the MT6797 AFE, the MT6351 codec and
the `mt6797-mt6351` machine card) plays a −40 dB tone to the headphones, with
the amplifier GPIOs left as the loader left them.

## Design

- **Power domain.** The AFE node uses SCPSYS power domain 4 (AUDIO). The
  profile therefore builds on the
  [display H2](../2026-10-06-gemini-display-h2/README.md) series and its
  SCPSYS adopt mode; without SCPSYS the AFE would defer forever.
- **Profile.** `mt6797-a53-audio-h3-compile`: the H2 series and fragment,
  plus `SOUND`, `SND`, `SND_SOC`, `SND_SOC_MT6797`, `SND_SOC_MT6797_MT6351`
  and `SND_SOC_MT6351`, all built in. The handoff fragment's
  `# CONFIG_SOUND is not set` is overridden explicitly.
- **Candidate DT.** [audio-h3-dt.sh](audio-h3-dt.sh) runs the H2 derivation,
  then enables the AFE with a new phandle, adds the PMIC's `audio-codec`
  child (`mediatek,mt6351-sound`, the MFD cell's compatible) and a `/sound`
  card linking the two. It checks the exact difference. The output is
  reproducible: SHA-256
  `87af3dd71c1ef9f98feed46861ca59f30d795daaf00dfc24b2a54ae76bc9f862`. There
  is no new schema diagnostic relative to H2; the card binding is still a
  text binding and is not validated.
- **Pads.** The five codec pads, GPIO146–150, default to mode 1 in the board
  DWS: `AUD_CLK_MOSI`, `AUD_DAT_MISO`, `AUD_DAT_MOSI`, `VOW_CLK_MISO` and
  `ANC_DAT_MOSI`. The preloader applies that default, so no pinctrl state is
  added. The AFE binding also forbids extra properties.

## Protocol draft (for the custodian's review)

Admitted effects, beyond H2:

- **AUDIO domain.** If SCPSYS adoption finds AUDIO off, the AFE's runtime PM
  powers it on through the normal SCPSYS sequence: power control, SRAM and
  infracfg bus protection. That is the first SCPSYS power transition in this
  series. The adopt log line says which case applies.
- **AFE and codec.** Probe and register writes; codec register writes when
  the card's DAPM paths change.
- **Audio.** One −40 dB tone to the headphones; no speaker path. The
  amplifier GPIO234/GPIO235 are untouched.

Observations:

- the `adopt:` line for `audio`;
- AFE, codec and card probe lines;
- `/proc/asound/cards` and the control list;
- with headphones attached, a 2 s −40 dB 1 kHz tone at 48 kHz, judged by ear;
- `/proc/asound/card0/pcm0p/sub0/status` during playback.

The `AUDDEC_ANA_CON0` readback in H3 needs a register read path this kernel
lacks; it stays open.

Branches:

- **Card registers and the tone is heard.** H3 holds; next is capture (H4).
- **Card registers but silent.** Check the DAPM path and controls; no
  amplifier GPIO changes in this boot.
- **AFE probe defers or fails.** Record the genpd and clock errors.
- **Any SCPSYS timeout.** Stop.

## Build

| Item | Value |
| --- | --- |
| Input commit | `eba7896b338c8ba4094086ec43e00ab40c799fb7` |
| Job | `eba7896b…-mt6797-a53-audio-h3-compile-m0`, buildbox-1, 32 jobs |
| Package inventory | `5f7954482d1ef2af2fa82966d64b42696b71641ac98c070882230719aa207508` |
| Release | `7.1.3-gemini-a53-audio-h3-compile` |

Compilation, remote validation, fetch and local checksums pass, with no
compiler warning. The resolved config has `SOUND`, `SND_SOC_MT6797`,
`SND_SOC_MT6797_MT6351`, `SND_SOC_MT6351` and SCPSYS adopt mode built in.
