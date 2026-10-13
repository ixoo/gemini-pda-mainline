# ND5 — reviewed active native-beacon diagnostic successor

Kernel input `eaafab2fa0d6f886768c7d0aa6f5c586d1f163cf`, profile
`mt6797-a53-wifi-native-delivery-diag`, exact approved0188
`f2d5c61673b278eb1c57dee731a18ea2258e9915896cfbe4fb9710f5b3a09ad1`.
[Source review](NATIVE_BEACON_REVIEW.md) labels the mechanism a hypothesis:
[ND4](ND4_RESULT.md) did not establish actual ACTIVE native-beacon presence.

Final source/replay pins: native-beacon.h
`86800ed1163078ad2c4195d8508b230c96614ae19f77bd2f55bda917374d9303`,
mac.c `0327fcd9ddddae40dff6575296da9cff496adbb691141dc8c56c557799555e28`.
The source is reviewed16cb, not the earlier67d export. Focused layout/extracted
actual-dispatch tests and parent negative pass under ASan/UBSan, as do original
actual-HIF/ordinary-data20000mutation/phase/classifier/native-loop/flags/budget
fixtures. Synthetic checks do not establish live management/crypto/concurrency.

Only the native explicit series and canonical archive gained0188. All18 other
explicit profile series, manifest/configuration and frozen historical inputs
remain byte-identical. Four historical global-series consumers inherit the
append under existing coordinator approval; they are not build/boot foundations.
Common publication gate and exact staged diff check passed. Checkpatch has only
the acknowledged internal archive missing-signoff/new-file MAINTAINERS exceptions,
no style warning/check; no fabricated DCO.

The ordinary managed Buildbox-1 build was launched from clean pushed input,
32jobs/modulesfalse/experiment selector unset, capacity/disk/quota/locks checked,
one heavy job. Build, managed validation/fetch and explicit fetched-package
validation passed. No candidate/deployment digest is invented.

## Validated build identities

- Actual job `eaafab2fa0d6f886768c7d0aa6f5c586d1f163cf-mt6797-a53-wifi-native-delivery-diag-m0`,
  completed `2026-10-13T23:05:04Z`; 683 selected patches in canonical order.
- Package inventory
  `3f6754e02895ea3b12094d8520c79e8eac743180e454a89d64a3ef483a39d919`.
- Image.gz `759f12a22a9a6ea7927437eeff05cddc256f03dea46df3c7773e6fe4d137550e`;
  decompressed15960072 bytes / effective size16580608 bytes.
- Configuration `33a50989755c6e226e3a4f388177d35956d407702f4e08120e737f28d6b2bf43`,
  unchanged from ND4. Patchset
  `c182c1b322ced48ab0316ad3f0f31028b43e6b3b7fa73d8f28eae22362a15a43`.
- Actual built native-beacon.h/MAC match the approved86800ed1/0327fcd9 full
  digests above. Ordinary decoder remains
  `02179812099659607a99e0d092c58c031960375f64d502a566274c413106134a`;
  native flags/budget header remains
  `905b6763ac1a15cbdca1ef0643db70585dfa443d2fdd36af223b349d157ccae0`.

Focused beacon/layout/extracted-dispatch/parent-negative and original actual-HIF/
ordinary20000mutation/phase/classifier tests pass against the ACTUAL built source
under ASan/UBSan. Native-loop/flags/budget fixtures pass there too. Only inherited
patch whitespace and unrelated unused CPU-hotplug inventory warnings; no build
error or new beacon warning. No configuration/DT change, no DT-schema rerun or
device test. Synthetic tests remain distinct from live MLME/firmware/crypto.

## Composition, runtime and deployment boundary

[build-native-candidate-5.py](build-native-candidate-5.py) pins the actual package/
Image above and reuses frozen ND4/ND2 private C32 config/RAM/board/LK gates.
Its actual namespace/CLI and inherited gate bodies are checked against the
validated package. Root completed private composition within this admitted task
and returned the REAL receipt. Exact fresh bindings below use that receipt,
not placeholders. ND5 is **not installed or runtime-tested**. No wrapper-only
rebuild or extra assembly approval is needed. Worker device access and synthetic
deployment summaries are forbidden.

### Real composition and fresh runtime identities

The custodian reports all frozen C32/config/RAM/inventory/provenance/PSCI-smc/
clock/LK gates passed, all six file hashes/sizes independently verified and
exact16MiB zero padding verified. Only kernel changed from ND4; config/board DT/
whole64-member private RAM root are byte-identical. The author verified the
real receipt digest and byte-exact imports, plus unchanged ND4 metadata pins.
Private images and RAM-root members were not transferred into public Git.

- [Real receipt](results/native-delivery-candidate-5.json) and byte-exact
  [runtime identity](runtime-nd5/results/candidate.json):
  `25893fa2bf4b67364e0821e635c0105c212f110d37156748d8e5a9338a612ef8`.
- Raw boot `f6b3a0d30d4955655c9c7d0fdcc3b7ef8aef880655e976fdc517ae5aa574fe50`,
  12668928 bytes; candidate directory must be `candidate-` plus this full digest.
- Full boot2 `6fec5cf5227f58deef91c0c1b0213956ab6c88f61292961d2817a6e6ec273ae0`,
  16777216 bytes. Composition is not deployment/boot evidence.

| Tool | Actual ND5 binding |
| --- | --- |
| [prepare-native-delivery-5.py](prepare-native-delivery-5.py) | Exact receipt pin before evidence creation, fresh `native-delivery/session-nd5`, `capture-nd5` left absent for its one-attempt claim |
| [install-native-5.py](install-native-5.py) | Real receipt/ND4 predecessor/actual program digest, deployment `mt6797-wifi-native-delivery-deployment-5`; unchanged live GPT/root/power/write/readback/shutdown guards |
| [laptop-capture-native-5.py](laptop-capture-native-5.py) | Exact receipt, `capture-nd5`, `session-nd5/deployment-summary.txt`; unchanged Phase-A capture gates |
| [passive-host-native-5.py](passive-host-native-5.py) | Actual `session-nd5`/`capture-nd5` namespaces, `runtime-nd5` identity and helper receipt; same finite protocol/verdict |
| [laptop-session-native-5.py](laptop-session-native-5.py) | Actual prepare/check_ram_root namespace selects ND5, mandatory inherited supplicant/wpa_cli/private source/calibration checks retained, actual installer routed to ND5 |

Tool SHA256 pins:

- Installer `81996cde2330aa9253715b4e075ae71d96fa666d182cdded5f8efd4a2691792f`.
- Standalone prepare `89a1f452bf23bce4861b3d884eb5bc1d321da3c9f60ae53b4f47b623d4da37aa`.
- Capture `7acce54380269f12d5a5530865ad92166add99775c30f893170be49b7957fd48`.
- Host `4e2066c36b517db136c0d8907a57926900dbf44192f5a3a623a67f529b463e24`.
- Session `6aaa9e39c8bff0c2f39604a67255882e58909fbd962cd6136b7000cf8ea046c4`.

[Actual-module wiring tests](tests/nd5-wiring-test.py) pass: standalone CLI
receipt/fresh-root/reuse and changed/missing receipt refusal before evidence
creation; actual installer/self-digest/deployment/predecessor derivation and
bad-candidate refusal; standalone-host/capture/session/prepare/check_ram_root
namespaces and mandatory supplicant/wpa_cli flags. No deployment summary was
created. ND4/ND3 wiring regression and original classifier/helper tests pass.
Temporary synthetic fixtures do not validate the private images or provide live
identity. Real private64-member session API/installer/capture preflights remain
with the custodian. The full-host pre-deployment dry run must refuse missing REAL
deployment evidence; that private full-host check is not claimed by the fixtures.
Same one-cycle leaf/helper/classifier/finite/quiescence/seal/regression/one-recovery
contracts, no reconstruction or eligibility/crypto bypass change from bindings.

The latest verified installed predecessor is ND4 full boot2
`7ce16dc852c1d89881c3ed4e676713fde1f8af755f297cc3e9671cddf6819a0c`,
returned Gemian `2099d541-361a-4866-8560-4f717779d130`. Historical identities do
not admit a later write. Root freshly verifies live Gemian/GPT/root/power/full
predecessor and derives the reviewed guarded installer before installation;
full readback, clean shutdown and owner physical boot2 selection remain required.
ND4/ND3/C35 inputs/artifacts/evidence are immutable.

## Unique observation and unchanged protocol

ND5 tests whether intact, strictly matched class2 native beacons can be queued
through normal mac80211 during ACTIVE, and whether the observed local beacon
loss/early disconnect changes. `beacons=` is incremented ONLY by successful
admitted native-beacon decode plus normal helper delivery; unchanged class7
beacon logs cannot substitute for it. It is not ordinary-native eligibility,
authentication, firmware-mode acceptance, throughput or full-driver support.

All prospective sample/drain/lifetime/radio ceilings, one ordinary descriptor
sample, eight terminal phase report lines, ordinary-data predicate/crypto flags,
class7 paths, no-radio/stop/regulatory/credit/cleanup and READY contract remain
unchanged. No reconstruction, monitor disable, forced lease/READY, extra read,
budget expansion, poison clearing or credit forgiveness. Same one-lifetime
quiescence/preservation/seal/regression/exactly-one-reviewed-recovery protocol.

- Native `beacons>0`: confirms this new host hook queued source-defined intact
  beacons, not that MLME accepted every frame or the AP was authenticated. Correlate
  retained disconnect/monitor/phase/helper outcome; persistent failure must not
  be hidden by relaxing monitoring or readiness.
- `beacons=0`: no successful new-hook delivery, not proof no target beacon
  arrived or firmware rejected the mode. Retain class/gate/phase/sample evidence.
- Beacons delivered but protected ordinary native0/no challenge: distinct
  partial progress, not a crypto/station PASS. Existing strict classifier still
  requires exact healthy owned cycle, ordinary delivery with flags clear and
  fresh post-ACTIVE boot/mode-bound Wi-Fi exchange.
- Protocol/identity/preservation/quiescence failure: preserve exact candidate/
  boot/status/ledger records, fail-stop and recover only through the unchanged
  reviewed gates. No unchanged retry or speculative live correction.

Full maintained lifecycle/reuse/rekey/replay/IRQ/DMA/clean-profile objective is
still incomplete. IRQ/DMA advice remains a separate future data point, not this
candidate's source/resource/admission scope.
