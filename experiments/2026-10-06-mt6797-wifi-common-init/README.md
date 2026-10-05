# Experiment: MT6797 Wi-Fi common initialization

| Field | Value |
| --- | --- |
| ID | `2026-10-06-mt6797-wifi-common-init` |
| Status | Driver draft; host and schema checks pass; runtime untested |
| Profile | `mt6797-a53-wifi-common-init-compile` |
| Subsystem | MT6797 CONSYS WMT common initialization |
| Date | 2026-10-06 |
| Device action | None |

## Decision and purpose

The owner chose the upstream shape on 2026-10-06: the sequence lives in the
CONSYS/WMT owner driver as a fixed table, and private inputs load as firmware
files. There is no userspace command channel. This draft implements Phase A's
common-init step up to, but not including, WLAN START and scan. The
[common-init review](../2026-10-03-mt6797-wifi-audit/COMMON_INIT_REVIEW.md)
owns the selected branches.

## Sequence

The new `mediatek,one-shot-wmt-common-init` flag extends the one-shot
negotiation. After the checked full-mode query, in the same root trigger, the
driver runs 285 steps in the selected vendor order for chip 0x0279:

| Steps | Content | Accepted reply |
| --- | --- | --- |
| 0–2 | DLM power: three masked writes to `0x80100060` | exact register event |
| 3–6 | MCU clock raise: enable, ratio, divider, HCLK | exact register event |
| 7–270 | Both ROM patches: two address commands, all fragments, a WMT reset, per patch | exact events |
| 271–273 | MCU clock restore | exact register event |
| 274–278 | LTE coexistence table, external component zero | exact coexistence event |
| 279–280 | VCN33-BT, then VCN33-WIFI on at 3.3 V | rail reads enabled |
| 281 | RF calibration `01 14 01 00 01` | six bytes starting `02 14 02 00`; status captured |
| 282–283 | Both PA rails off | regulator success |
| 284 | Antenna mode from `mediatek,coex-antenna-mode` | exact coexistence event |

The vendor expects calibration to reply `02 14 02 00 00 01` but never compares
it. The driver records the two status bytes instead of declaring success from
them. Crystal trim, co-clock, merged PCM and FM strap are not selected.

The two ROM patches load with `request_firmware` from `mediatek/mt6797/` and
must match pinned SHA-256 digests and the selected metadata before any command
is sent. The retained `WMT_SOC.cfg` sets only `coex_wmt_ant_mode=1`, already
recorded in the [WMT configuration summary](../2026-07-12-connectivity-wmt-recovery/results/wmt-config-summary.txt).
With no filter-mode key, the vendor defaults select the LTE table above, so the
kernel needs no configuration parser; the antenna mode is one DT property.

Each exchange, calibration included, has the vendor's 2 s event wait within
a 60 s budget; see the timing correction below.
The first failure stops the sequence and keeps power, clocks and rails for
reviewed recovery. The flag requires the AFE region, so the AFE stage always
runs before MCU release, and it excludes the Bluetooth H1 flag.

## Patches

- [0111](../../patches/proposals/0111-dt-bindings-soc-mediatek-mt6797-consys-add-one-shot-common-init.patch)
  adds the flag and `mediatek,coex-antenna-mode` to the binding.
- [0112](../../patches/proposals/0112-soc-mediatek-add-one-shot-MT6797-WMT-common-initialization.patch)
  adds the step table, the existing ROM patch constructor and the executor.

The profile is the STP task-routing profile plus these two patches; the C3
profile is unchanged.

## Validation

[test-common-init.c](test-common-init.c) runs the whole sequence with synthetic
patch files of the exact sizes. It checks 285 steps, 281 exchanges and four
rail steps, full body coverage, exact vendor vectors for DLM, clock restore,
resets, the LTE filter, calibration and antenna mode, and refusals that leave
outputs unchanged. It passes with ASan and UBSan.

```sh
d=$(mktemp -d); cp PREPARED/drivers/soc/mediatek/{stp-full,wmt-full-stp,wmt-rom-patch,mt6797-wmt-common-init}.h "$d"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -I"$d" test-common-init.c -o "$d/t"
setarch "$(uname -m)" -R "$d/t"
```

The binding passes `dt-doc-validate`. A test DTB with the flag, antenna mode,
supply and AFE region validates. Adding the Bluetooth flag, dropping the
antenna mode or dropping the AFE region each fails. Both patches pass strict
checkpatch, excluding only the missing sign-off and the new files' maintainer
entry.

## Candidate inputs, later

A runtime candidate needs both ROMv3 patch files in the RAM root under
`lib/firmware/mediatek/mt6797/`, with these digests:

| File | SHA-256 |
| --- | --- |
| `ROMv3_patch_1_1_hdr.bin` | `5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e` |
| `ROMv3_patch_1_0_hdr.bin` | `450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630` |

It also needs the negotiation and common-init flags, the antenna mode, the
VCN33-BT supply and the AFE region in the CONSYS node. A protocol, the C3
result and the owner's review come first. Calibration success semantics and
WLAN START composition remain open.

## Build

Buildbox compilation on buildbox-3 and remote package validation pass for
input `04a42218`. Fetch and all local checksums pass.

| Item | Value |
| --- | --- |
| Package inventory | `aee609f8384b14912e94f54293d08d5c1123d5514ad231cb4ccd4538bc5d45f9` |
| Board DTB | `07b097d581cae6208eea8387d534e14bb2c2bc30752b0d4b783f711284284734`, identical to the C3 package |
| Release | `7.1.3-gemini-a53-wmt-versions`, inherited from the profile's fragments |

The image contains the executor's log strings and firmware names, and
`CRYPTO_LIB_SHA256` is built in. No new compiler warning appears.

## Timing correction (2026-10-06)

The [first C3 boot](../2026-10-05-mt6797-bt-h1/RUNTIME_1.md) got the STP
acknowledgement for Bluetooth function-on but no event within 600 ms. The
vendor waits `WMT_LIB_RX_TIMEOUT` = 2000 ms for every WMT event. Patch
[0113](../../patches/proposals/0113-soc-mediatek-wait-the-vendor-2-s-for-each-MT6797-WMT-event.patch)
applies that wait to the Bluetooth sequence and to every common-init exchange,
with budgets of 12 s and 60 s. It is in this profile only; the consumed C3
profile is unchanged. A Bluetooth retry uses this profile with the Bluetooth
flag and without the common-init flag.

The rebuilt package for input `025b2667` passes Buildbox compilation, remote
package validation, fetch and all local checksums, with no new warning.
Package inventory: `adda8f2de1ec2a3ad157676eb2103673e8e79d5f711d862a30aef829c62ca111`.
The board DTB is unchanged from the earlier package.

## Phase A composition (2026-10-06)

The common-init profile derives from the WMT line, which lacks the WLAN
driver's scan stack (0053–0081). The scan profile lacks the WMT line
(0086–0114). The two lines share 561 patches and diverge by 28 each, and both
edit `mt6797-consys.c`, so their union does not apply as is.

Both lines were rebuilt as git branches from the shared base and the WMT line
was rebased onto the scan line. Two commits conflicted, 0088 and 0092; both
conflicts were pure additions on each side (includes, owner fields), resolved
by keeping both. Six WMT patches then needed new context on the scan line:
0088, 0092, 0096, 0099, 0109 and 0112. Their ports sit next to the originals in
`patches/series` with an `-on-scan-line` suffix, the original messages and an
added port note. The other 22 WMT patches apply unchanged.

Patch [0115](../../patches/proposals/0115-soc-mediatek-continue-to-WLAN-start-after-MT6797-common-init.patch)
lets a completed common init continue into the existing HIF, EMI set, EMI copy
and firmware-start stages, each with its own DT gate. Any WMT failure still
returns at once with resources retained.

The new `mt6797-a53-wifi-phase-a-compile` profile is the scan-tuning profile's
patches and fragments, plus the WMT line, 0115, the WMT query fragment for
debugfs and a fragment giving the distinct release
`7.1.3-gemini-a53-wifi-phase-a`. Checks:

- The 618-patch series applies to pinned 7.1.3 with the project's apply
  method, and the result matches the rebased branch exactly in the CONSYS,
  WLAN, binding and DT directories.
- The twelve transport fixtures, the common-init sequence test and the
  Bluetooth prepare test pass against the Phase A headers.
- All seven new patch files pass strict checkpatch with the established
  exclusions.

A runtime candidate also needs the WLAN child enabled and the scan-line DT
settings from the earlier passive-scan candidates, plus everything in
"Candidate inputs" above. A protocol comes first.

Buildbox compilation on buildbox-2, remote validation, fetch and local
checksums pass for input `b6fa6a62`, with no new warning.

| Item | Value |
| --- | --- |
| Package inventory | `499233263a327fc49c31776ec22e15bb5180d12a9ea192ead4b75d7f2baf205d` |
| Release | `7.1.3-gemini-a53-wifi-phase-a` |
| Board DTB | `07b097d581cae6208eea8387d534e14bb2c2bc30752b0d4b783f711284284734` |

The configuration builds the WLAN mac80211 driver, passive scan, debugfs and
the SHA-256 library in. The image contains the common-init, Bluetooth and
continue-to-WLAN log strings.

## Phase A adapters (2026-10-07)

Offline tools for the [Phase A protocol](PROTOCOL.md), built on the existing
WMT-versions and scan-tuning chains. The [effect review](EFFECT_REVIEW.md)
covers what the sequence writes. No tool here touches the device; composition,
installation and the run are the laptop custodian's.

| File | Role | Built on |
| --- | --- | --- |
| [build-candidate.py](build-candidate.py) | Compose the candidate | WMT-versions parent and builder pattern |
| [install-passive.py](install-passive.py) | Bind the guarded boot2 installer | port0-header installer; predecessor = C1-4 boot2 `144ac96d…` |
| [capture-private.py](capture-private.py) | WMT memory, one `wmt_negotiate` trigger, Phase A log classification | `wmt-before-start` capture |
| [passive-session.py](passive-session.py) | Bind the session to the 61-member RAM root | scan-tuning session |
| [passive-host.py](passive-host.py) | One passive scan, sealed log, A53 regression, recovery | scan-tuning host |
| [phase-a-scan.sh](phase-a-scan.sh) | The scan script with the Phase A release | scan-tuning `passive-scan.sh` |

### Inputs and provenance

- **Kernel.** Package commit `b6fa6a62`, inventory `49923326…`, built DTB
  `07b097d5…`; the builder checks provenance, configuration and the DTB.
- **Parent.** The published WMT-versions candidate (receipt manifest
  `d6a22f27…`, boot2 `391f44a8…`), every member re-hashed.
- **ROM patches.** `ROMv3_patch_1_1_hdr.bin` (`5732c073…`, 46472 bytes) and
  `ROMv3_patch_1_0_hdr.bin` (`450c2b09…`, 210904 bytes), retained Gemian vendor
  firmware, added at `lib/firmware/mediatek/mt6797/` with mode 0644. Order and
  metadata are in the [patch-order review](../2026-10-03-mt6797-wifi-audit/ROM_PATCH_ORDER.md).
- **`iw` userspace.** The six files pinned by the
  [passive-scan userspace receipt](../2026-10-01-mt6797-passive-scan/results/userspace.json)
  (`4aedbc77…`, Debian bookworm packages with verified signatures). The
  builder refuses unless the parent RAM root carries them unchanged.
- **Source.** Patch digests: 0111 `f3de60f8…`, 0112 port `6cee6703…`, 0113
  `65ca1ff0…`, 0114 `9cc3aac3…`, 0115 `d1a59ea8…`; `mt6797-wmt-common-init.h`
  `0aa9e908…`, `wmt-rom-patch.h` `1c20866e…`; CONSYS binding `8e36b807…`.

### Budgets

The trigger write carries negotiation (1.6 s), common init (2 s per exchange,
60 s total) and WLAN start, so its host process timeout is 120 s. The scan
keeps the existing 500 ms dwell, five-second kernel deadline and 30 s session
phase. The host runs the scan only if the capture classified the lifetime as
ready: negotiation and common init passed, both rails off, continuation logged,
the three WLAN readiness lines present, every prerequisite exactly once and in
protocol order (negotiation, common init, continuation, record, regulatory,
TC4), and no firmware stop or BT H1 line.

If the lifetime is not ready, or the capture never classified it, the host
skips the inherited host `main()`, which would require an accepted capture, and
calls the wiphy-probe prepare that the scan-tuning host wrapped and its execute
directly. Observation, log sealing, the A53 regression and reviewed recovery all
run without any capture prerequisite; no scan is attempted, and the results are
written to `failure-session-result.json` and `phase-a-session-result.json`.
The wiphy probe records an absent wiphy without failing the session.

### Checks run here

- [test-build-dt.py](test-build-dt.py) applies the DT edit to the Phase A
  built DTB made parent-like. It checks the flags, antenna mode, AFE region,
  the new VCN33-BT node and supply, the WLAN child re-enabled, every other node
  unchanged, and refusal of a second application. The edited DT validates
  against the Phase A CONSYS binding.
- [test-capture-classify.py](test-capture-classify.py) checks the classifier on
  synthetic logs: a pass, a step failure, an unexpected calibration status,
  rails left on, a firmware stop, a BT H1 line, a failed TC4 line and a
  duplicate common-init line.
- [test-capture-classify.py](test-capture-classify.py) also swaps adjacent
  prerequisite lines and requires each order violation to be refused.
- [test-host-select.py](test-host-select.py) checks the release, path and
  scan-script overrides at every host level, and that the scan prepare is chosen
  only for a ready lifetime.
- All adapters compile and import with an empty private repository.

### Gates before composition and the run

1. Fill `MANIFEST_SHA` in `capture-private.py` and `install-passive.py` with
   the SHA-256 of the committed `results/candidate.json`; both refuse until
   then. The runtime-1 receipt (`169cd7a7…`, boot2 `c04915b2…`) is kept as
   [results/runtime-1-candidate.json](results/runtime-1-candidate.json); see
   [RUNTIME_1.md](RUNTIME_1.md). The builder pins the rebuilt package
   `c943e1f0…` from input `0ca1944f`, which carries the ROM patch digest fix.
2. Private inputs on the laptop: the WMT-versions parent candidate directory,
   the two ROM patches, the fetched package, the private Wi-Fi record at
   `artifacts/calibration-live-20261001/record-1/WIFI.storage`, and the A53
   session credentials.
3. Coordinator review of [PROTOCOL.md](PROTOCOL.md) and the
   [effect review](EFFECT_REVIEW.md), including calibration as one bounded
   radio action.
