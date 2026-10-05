# Phase A protocol: common init, WLAN start, one passive scan

Status: draft for coordinator review, 2026-10-06. No candidate is composed and
no device action has been taken under this protocol.

## Hypothesis and unique observation

Earlier scan boots started WLAN firmware and completed passive scans with a
zero firmware management count and no frame or BSS. None of them ran the WMT
common initialization: ROM patches, MCU clock, LTE coexistence, PA rails and
RF calibration. The hypothesis is that common init is what the receive path
lacks. The unique observations are the calibration event's size and, after the
same scan as before, a nonzero management count or a BSS.

## Artifact

| Item | Value |
| --- | --- |
| Profile | `mt6797-a53-wifi-phase-a-compile` |
| Commit | `b6fa6a62f767609759cf6f4b35803bcafe1f8ed5` |
| Package inventory | `499233263a327fc49c31776ec22e15bb5180d12a9ea192ead4b75d7f2baf205d` |
| Release | `7.1.3-gemini-a53-wifi-phase-a` |
| Built board DTB | `07b097d581cae6208eea8387d534e14bb2c2bc30752b0d4b783f711284284734` |
| Builder | buildbox-2; remote validation, fetch and local checksums passed |

## Candidate composition

Start from the booted WMT-versions parent, as C3 did; its DT carries the BTIF
resources and its RAM root the WLAN firmware and board record. Resolve every
phandle from the booted DT.

| Node | Change |
| --- | --- |
| CONSYS | Remove `mediatek,one-shot-wmt-identity-capture`. Add `mediatek,one-shot-wmt-negotiate`, `mediatek,one-shot-wmt-common-init` and `mediatek,coex-antenna-mode = <1>`. |
| CONSYS | Append the `afe` region, `0x180b6000` size `0x100`. Add `vcn33-bt-supply`. |
| CONSYS | Keep the power, chip-ID, reset-release, HIF, EMI set, EMI copy, firmware-start, region-19 and deferred-start flags; Phase A runs that chain after common init. Must not contain `mediatek,one-shot-bt-reset`. |
| MT6351 regulators | Add `ldo-vcn33-bt` with `regulator-name = "vcn33-bt"` only. |
| WLAN child | Set `status = "okay"`, as in the passive-scan candidates. |

RAM root, relative to the parent:

- Add `lib/firmware/mediatek/mt6797/ROMv3_patch_1_1_hdr.bin`
  (`5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e`) and
  `ROMv3_patch_1_0_hdr.bin`
  (`450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630`) from
  the retained Gemian firmware.
- Ensure the pinned `iw` 5.19 and its libraries from the passive-scan
  candidates are present, with their recorded digests.
- Update the release gate to `7.1.3-gemini-a53-wifi-phase-a`.

Validate the DTB against the CONSYS binding from this package's source.

## Sequence

1. Guarded live-GPT boot2 install with full readback and clean shutdown. The
   owner selects boot2.
2. Confirm boot identity, release, USB SSH and console.
3. Preserve region 19 and prepare WMT memory exactly as in C3.
4. Write `1` once to `wmt_negotiate`. In one call: negotiation, the 285-step
   common init, then HIF, EMI set, EMI copy and firmware start.
5. Save `dmesg`. Required lines, in order:
   `one-shot WMT negotiation: result=0`,
   `one-shot WMT common init: result=0 completed=285/285`,
   `WMT common init complete; continuing to WLAN HIF`, then the existing
   firmware-start, regulatory and record-prepare success lines the earlier scan
   script checks.
6. Only if all are present, run one channel-40 passive scan with the earlier
   scan script, retargeted to this release, and capture the firmware
   management count and any BSS.
7. Seal the log, run the A53 regression, return through the reviewed recovery.

Budgets: one trigger; common init 2 s per exchange within 60 s; the scan's
existing five-second deadline and 256 polls; one scan. No retry, association,
TX, packet DMA or IRQ enable beyond the earlier scan contract.

## Failure behaviour

The first failed WMT step stops the sequence and returns; HIF and firmware
start do not run. CONSYS power, clocks and any PA rail stay on until the
reviewed recovery. A WLAN-stage failure behaves as in the earlier scan boots.

## Decision branches

- **Negotiation fails.** Control regression; stop.
- **Common init fails at step N.** Record the step, its raw reply and the
  link counters privately; diagnose that step offline. No WLAN result.
- **Calibration replies with a data event.** Since [runtime 2](RUNTIME_2.md)
  this is the expected form; common init continues by design. The classifier
  records only framing metadata: captured bytes, ACK frames, task and event
  size. Calibration content is not checked, so treat calibration as unverified
  when interpreting the scan.
- **Common init passes, scan finds a BSS or a nonzero management count.**
  Phase A's receive question is answered; Phase B starts.
- **Common init passes, scan still zero.** Common init is not sufficient on its
  own; compare the remaining vendor differences offline.
- Unexpected heat, power or recovery behaviour: follow
  [SAFETY.md](../../docs/SAFETY.md).
