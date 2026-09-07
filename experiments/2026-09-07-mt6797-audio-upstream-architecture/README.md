# MT6797 audio current-upstream architecture

## Decision

The smallest coherent upstream audio topic is an **adapted patch 0064 by
itself**: convert the existing MT6797 AFE text binding to DT schema for the
already-upstream `mediatek,mt6797-audio` driver. The conversion has a real
consumer and a complete offline validation story. It changes no driver or DTS,
does not instantiate a card, and cannot power a speaker, microphone, headset,
modem, Bluetooth or voice path.

The local patch is not submission-ready unchanged. Current mainline still
contains
`Documentation/devicetree/bindings/sound/mt6797-afe-pcm.txt`; patch 0064
creates a YAML file without deleting that source binding. The accepted MT8173
precedent converted and deleted its legacy text file in the same change.
Therefore the first topic must:

1. create `mediatek,mt6797-afe-pcm.yaml` with the exact existing compatible,
   register, interrupt, power-domain and ordered eight-clock contract;
2. delete only `mt6797-afe-pcm.txt`, leaving the separate
   `mt6797-mt6351.txt` machine-card binding untouched;
3. retain the seven clocks acquired by `mt6797-afe-clk.c` plus
   `mtkaif_26m_clk`, which the ADDA DAPM graph acquires by name; and
4. add a complete schema example derived from the public text binding and pass
   focused DT-schema checks before submission.

Patch 0045 is a coherent **follow-up**, not part of the smallest first topic.
Its disabled AFE node is legitimate SoC description rather than a board audio
enablement: the matching AFE driver, every named clock provider, and the
MT6797 AUDIO power domain are all in current mainline. A disabled node supplies
an immediate `dtbs_check` consumer for the schema without registering an ALSA
card. The patch still needs a current-tree adaptation: current `mt6797.dtsi`
does not include `dt-bindings/power/mt6797-power.h`, and the node must be moved
to current unit-address order near `0x11220000`. It should follow binding
acceptance through the ARM/MediaTek DTS route.

No codec child or machine-card node belongs in either topic. Current mainline
has the MT6351 codec and MT6797–MT6351 machine drivers, but the inspected
current MFD core/binding has no MT6351 parent/cell instantiation, and the board
codec routes, amplifier, jack and analog endpoints are not represented. That
is a separate dependency chain, not a reason to expand these two patches.

This does not contradict the July audio record. Its `mt6351_devs` statement
describes the **locally patched v7.1.3 package** used by that experiment. Local
patch 0008 adds the MT6351 parent and child compatibles to the MFD binding;
local patch 0010 adds the MT6351 parent match, core data and `mt6351_devs`
table, including the `mt6351-sound` cell. Official stable v7.1.3 and the pinned
current mainline omit those local additions. Their absence from current
mainline is provenance, not an upstream regression or removal, and the July
observations about the patched package remain historical evidence.

## Source pin

Torvalds' kernel.org repository resolved to
`28924df2a08f440c73991b83028032c901de2ae4`. Only individual official files
from commit-addressed current and stable mirrors and two exact historical
commit patches were inspected; no tree was cloned. Exact URLs, hashes,
negative lookups and findings are recorded in
[`results/source-review.json`](results/source-review.json).

The frozen inputs and repair-requested provenance patches match their recorded
identities:

| Input | SHA-256 |
| --- | --- |
| patch 0008 | `6ebf2fd36968b23b1b8499f3881228114f13c50885b6aebfb3ff481a03286757` |
| patch 0010 | `e6e6d7988745af64544b8fc695ebb2eb49620d575799ea65cb7c430d87069ae1` |
| patch 0045 | `a07bcf53e3c1fcddfed58ef6ec74e59b664acf8916e6c2c5bcbef027bc29128e` |
| patch 0064 | `b5fc79ee89672106bcec8014f3fc973a4553671e95eae4537e99d0ce274d004d` |
| July audio README | `05ac5115903ea73105bcefe2064b0df4d32f6d0c325b89c082cf85197a07ad45` |

The July README was used only as the frozen sanitized project record. None of
its linked private captures, vendor sources or retained binaries was opened.
Bounded exact-string public searches located no current mailing-list overlap;
that result is not proof that no discussion exists.

The official stable v7.1.3 source ref resolves to
`199c9959d3a9b53f346c221757fc7ac507fbac50`. At that ref,
`Documentation/devicetree/bindings/mfd/mediatek,mt6397.yaml` has SHA-256
`a61b17c83146db12db3b5ff22cdb10779b65fa764042fc68321ad9bdba1bf2cc`
and `drivers/mfd/mt6397-core.c` has SHA-256
`3642c30bc125001b3e2ee3563900567e927dc04d963ef0b7f8e1d79a352c0ff6`;
neither contains MT6351 support. The corresponding pinned-current files are
listed in the receipt and likewise omit an MT6351 parent match and MFD cell.

## Current dependency map

```text
MT6797 clock providers (current)
  +-- infra_sys_audio_clk
  +-- infra_sys_audio_26m
  +-- mtkaif_26m_clk
  +-- top_mux_audio
  +-- top_mux_aud_intbus
  +-- top_sys_pll3_d4
  +-- top_sys_pll1_d4
  `-- top_clk26m_clk

MT6797 scpsys AUDIO power domain (current)
  `-- AFE node / mediatek,mt6797-audio (0045 follow-up)
        +-- current AFE platform + memif/DAI driver
        |     +-- seven platform clock consumers
        |     `-- ADDA DAPM -> mtkaif_26m_clk
        `-- future machine card / mediatek,mt6797-mt6351-sound
              +-- mediatek,platform -> AFE
              `-- mediatek,audio-codec -> MT6351 codec child
                    `-- MT6351 MFD parent/cell (not current mainline)

Board analog graph (not established)
  +-- speaker / possible external amplifier
  +-- earpiece
  +-- microphones
  `-- headset detect and routing
```

The AFE owns digital PCM/DAI resources, its IRQ, runtime-PM transition, clocks
and AUDIO domain. The MT6351 codec owns analog codec registers and DAPM
widgets only after its MFD cell exists. The machine driver binds those two
components and owns card links. Board DTS owns physical routes, supplies,
amplifier and jack wiring. Modem, Bluetooth, FM and hostless endpoints are
separate transports and are excluded from the first ordinary card.

## Current-source matrix

| Question | Public-current result | Consequence |
| --- | --- | --- |
| Does an MT6797 AFE driver exist? | Yes. `mt6797-afe-pcm.c` matches `mediatek,mt6797-audio`, maps one resource, requests one IRQ and uses runtime PM. | No new AFE driver is justified. |
| Is the binding current? | The 2018 `mt6797-afe-pcm.txt` is still present; no MT6797 AFE YAML exists. | A text-to-schema conversion is useful independently. |
| Are all eight clocks real consumers? | Yes. Seven names are acquired by `mt6797-afe-clk.c`; `mtkaif_26m_clk` is a DAPM clock supply used by both ADDA playback and capture. | Preserve exactly eight ordered names; do not “fix” the count to seven. |
| Are the SoC providers current? | `clk-mt6797.c` exposes the named audio clocks; `mtk-scpsys.c` implements `MT6797_POWER_DOMAIN_AUDIO`; the public power header defines ID 4. | The disabled AFE node has a truthful provider graph once it includes the public power header. |
| Does current DTS contain the AFE? | No. Current `mt6797.dtsi` has clocks and scpsys but no `0x11220000` audio node or power-header include. | Adapt 0045 after the binding; keep it disabled. |
| Are codec and machine drivers present? | Yes. `mt6351.c` and `mt6797-mt6351.c` exist; the machine driver requires platform and codec phandles. | Reuse these drivers, but presence does not create a usable card. |
| Is MT6351 instantiated in current MFD? | No MT6351 match/core/cell is present in the inspected `mt6397-core.c` or parent binding. Those pieces exist only after local patches 0008 and 0010 are applied to the v7.1.3 package. | A codec phandle has no current upstream provider; machine-card work remains blocked on the separate MFD topic. This is not an upstream removal. |
| Is analog board routing known publicly here? | No public-current DTS or binding in the inspected set describes Gemini speaker, microphone, amplifier or jack wiring. | Do not add or enable the board card. |

The current AFE regmap caps accesses at the driver's `AFE_MAX_REGISTER` inside
the 4 KiB resource described by the legacy binding. This review found no public
current source reason to enlarge the node aperture or copy a vendor audio ABI.

## Patch dispositions

### 0064 — adapt as the first topic

Keep the compatible and exact eight-clock interface, but turn the patch into a
true conversion:

- delete the superseded AFE text file in the same commit;
- retain `reg`, one interrupt, one power domain, eight clocks and eight ordered
  clock names as required properties;
- give each clock a useful description and include a complete example;
- retain `additionalProperties: false` unless focused schema validation shows a
  current common-property requirement; and
- update the schema `maintainers:` field only to people who actually agree to
  maintain it. This public review does not infer willingness from an old email
  address.

The patch is removable from the project series once the targeted upstream base
contains an accepted equivalent YAML schema, the legacy AFE text file is gone,
and the eight-name split is unchanged. A mere public posting is not the removal
condition.

### 0045 — adapt as a follow-up

Retain the `0x11220000/0x1000` resource, SPI 151 level-low, AUDIO domain, eight
clock specifiers/names and disabled status. Against current mainline:

- add `#include <dt-bindings/power/mt6797-power.h>`;
- place the node in unit-address order rather than at its historical local
  context;
- reference only current clock/provider symbols; and
- keep `status = "disabled"` with no codec or sound-card node.

The disabled node is acceptable as a follow-up because it describes a real SoC
block with an existing driver and providers and supplies a schema-validated DTS
consumer. It is not evidence of a usable card. Remove the local patch only when
the targeted upstream base contains the equivalent disabled node with the exact
resource contract; an accepted schema alone does not supersede it.

The repository currently orders 0045 before 0064 by patch number. That local
historical order is not the proposed upstream order. This item does not edit
`patches/series`; any later replacement/reordering must audit every manifest
profile under the repository invariant.

## Upstream route and validation story

The current `MAINTAINERS` file routes sound bindings and ASoC code through Liam
Girdwood and Mark Brown on `linux-sound`, using the ASoC tree, with Devicetree
binding review for the schema. The DTS follow-up routes through ARM/MediaTek SoC
maintainers Matthias Brugger and AngeloGioacchino Del Regno on
`linux-arm-kernel` and `linux-mediatek`, after the binding is accepted or has an
immutable maintainer acknowledgement.

The later implementation contract should run, at minimum:

1. `scripts/checkpatch.pl --strict` on each generated patch;
2. focused `dt_binding_check` for
   `mediatek,mt6797-afe-pcm.yaml`, including its example;
3. a mechanical assertion that schema order, current clock array and ADDA DAPM
   supply jointly account for the same eight names exactly once;
4. for 0045 only, build the affected MT6797 DTB and run focused `dtbs_check`
   against the accepted schema; and
5. the repository manifest-series invariant after any eventual patch
   replacement or ordering change.

No ASoC object build is required to establish a binding-only change because the
driver source is unchanged. A later DTS build proves syntax/schema composition,
not runtime audio. Playback/capture, mixer, codec, clock, power, speaker,
microphone, jack, modem and Bluetooth tests remain outside both topics.

## Authorship and limitations

Both local patches name Julien Etienne and include a matching `Signed-off-by`.
This review confirms only the text present in the files; it cannot certify that
the DCO statement is truthful. An adapted submission may retain that identity
and sign-off only if Julien actually authored the adaptation and can make the
certification. Otherwise it must use the actual author and must not invent a
sign-off. The conversion commit message should credit Kai Chieh Chuang's 2018
binding commit `22d9f80904b4510296c133db15f8d3291292023b`.

The accepted MT8173 conversion precedent is commit
`bb90e0c91d375ec5db8a4f8cd2555900aea0725f`: it creates the vendor-prefixed
schema and removes the legacy text source in one patch. It demonstrates current
conversion shape, not maintainer pre-approval for MT6797.

This review establishes source compatibility and an offline validation plan
only. It does not establish MT6351 MFD readiness, machine-card correctness,
analog wiring, safe volume, runtime PM on Gemini, or any audio hardware support.
It made no build, device access, private-evidence access, implementation,
upstream contact or shared-file change.

Review-ready UTC: `2026-09-07T20:12:34Z`.

Accepted UTC: `2026-09-07T20:15:58Z`, after one documentation repair that
reconciled locally patched versus official-upstream MT6351 provenance. The
technical topic ordering was unchanged.
