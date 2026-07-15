# Experiment: compare the bsg100 Gemini Linux bring-up

## Record

| Field | Value |
| --- | --- |
| ID | 2026-07-13-bsg100-gemini-linux-comparison |
| Status | completed (comparative audit; no hardware action) |
| Subsystem | Cross-subsystem hardware and mainline bring-up evidence |
| Device variant | Gemini PDA, MT6797X / Helio X27; exact bsg100 unit variant is not independently established |
| Date(s) | 2026-07-13 |
| Investigator(s) | Codex |
| Tracking issue | None |

## Question or hypothesis

Can the public bsg100/gemini-linux work be used as corroborating evidence for this project, and where does it disagree with the live Gemian device or with our Linux 7.1.3 design?

The repository is treated as an independent report, not as an authority. A claim is promoted only when it has source context and agrees with live observation, an upstream interface, or a repeatable hardware experiment.

## Provenance and environment

- Source: https://github.com/bsg100/gemini-linux
- Audited revision: 82321ce64752d5bf006fe7c40c331edbd0dfb702
- Revision date: 2026-07-13T08:52:33+08:00
- Fetch method: shallow, single-branch clone into a disposable directory; no source, binary, firmware, or document was copied into this repository.
- Reference-tree file hashes and keyword audit: [`results/audit-current-20260714.txt`](results/audit-current-20260714.txt).
  The audit script and output were rerun byte-identically on 2026-07-14;
  their SHA-256 values are recorded in the result header.
- Reference patch inventory: 35 files under patches/v6.6/; aggregate SHA-256 is recorded in the result file.
- Our comparison baseline: Linux 7.1.3, 72 local patches, current package
  `linux-7.1.3-gemini-a9a7c5002038`, patchset SHA-256
  `a9a7c5002038022c5df87ed48f61cd68778b422370f7d038d07e73a086490632`.
- Live device baseline: Gemian Debian 9 userspace on the user's Gemini at 192.168.1.50; observations are linked from docs/hardware/ and subsystem experiments.

## Safety assessment

This audit is read-only. It inspected a public Git repository and local sanitized notes only. It did not connect to the device, run a reference binary, access private firmware, or write any partition. The reference repository contains flashing utilities, vendor-derived material, and binary artifacts; none are imported or executed.

## Associated code

- [`audit-reference.sh`](audit-reference.sh) — read-only metadata, hash, and
  keyword audit. Run it with the disposable reference tree as its only
  argument; it never imports or executes reference code.
- [`results/audit-current-20260714.txt`](results/audit-current-20260714.txt) — output from the pinned revision.

## Procedure

1. Clone the public repository into a disposable directory.
2. Record the commit, date, selected document hashes, and patch count.
3. Read the project overview, hardware inventory, kernel plan, driver notes, safety rules, and selected hardware logs.
4. Compare each claim with the current live-device resource map and the Linux 7.1.3 source/design records in this repository.
5. Record agreements, contradictions, and unverified assumptions below.

## Observations

### Agreements that are useful corroboration

| Topic | bsg100 evidence | Current project comparison | Assessment |
| --- | --- | --- | --- |
| SoC | MT6797X / Helio X27, ten-core ARM SoC | Live device and vendor DT identify MT6797X; ten PSCI CPU nodes are retained in the local DT; bsg100's hardware logs bring up CPUs 1–7 but stop at CPU8/A72 without `maxcpus=8` | Corroborated at SoC level; generic PSCI is reusable, but full ten-core behavior is still a runtime gate in the current 7.1.3 tree. See the [CPU cross-check](../2026-07-13-cpu-psci-timer-recovery/results/bsg100-cpu-psci-crosscheck-20260714.txt) |
| UART | UART0 at 0x11002000, 921600 baud, GPIO97/98; mainline name ttyS0 | Live ttyMT0 maps to the same UART resource; Linux 7.1.3 reuses 8250_mtk with DMA disabled for the console | Strongly corroborated; hardware boot capture remains pending for our candidate |
| Legacy baseline | Android/Linux 3.18 is the vendor baseline | Live Gemian reports kernel 3.18.41+; our project keeps it as evidence, not as a source tree | Corroborated |
| eMMC | 6.6 experiments reached the internal card and all 33 partitions after correcting IRQ polarity, pinconf, supplies, and MT6797 register-layout assumptions | Our live map independently identifies MSDC0 at 0x11230000; Linux 7.1.3 adds an MT6797-specific compatibility record and currently caps the board node at 25 MHz | Useful hardware evidence for the level-low IRQ, explicit rails, pinmux-only pads, and MT2701-generation register profile; not a reason to copy the bsg100 compatible string blindly. See the [MSDC cross-check](../2026-07-12-mt6797-msdc-recovery/results/bsg100-msdc-crosscheck-20260714.txt) |
| Display identity evidence | Later bsg100 hardware logs identify an AUO/Solomon SSD2092, FHD 1080x2160, video-mode module with direct SEEPROM/DSI observations | Our named-device capture selects `aeon_nt36672_fhd_dsi_vdo_x600_xinli` but does not read silicon; its vendor `compare_id()` is unconditional | Shared geometry is useful, but controller identity conflicts across evidence sets. Keep both descriptors disabled until the named device is probed. See the [panel cross-check](results/bsg100-panel-crosscheck-20260714.txt) |
| AW9523B | Address 0x5b, ID 0x23, shutdown/reset on GPIO58, keyboard matrix | Live Gemian probe and our resource map report the same address/ID/reset relationship; Linux 7.1.3 has reusable AW9523 pinctrl and matrix-keypad frameworks | Strong corroboration; adapter numbering differs (Linux adapter 3 corresponds to SoC I2C5) |
| FUSB301A | I2C CC controller at 0x25, treated as separate from FUSB302 | Live resource map finds FUSB301-compatible clients at 0x25; local support stays disabled pending connector/IRQ/role evidence | Identity corroborated; runtime behavior remains unproven |
| CONSYS | Wi-Fi is an MT6797 integrated/SoC path rather than a drop-in SDIO/mt76 device; BT uses MediaTek BTIF/STP concepts | Our live resource map independently recovers MT6797 AP-DMA/AHB Wi-Fi and BTIF/STP contracts and rejects btmtksdio/mt76 as drop-in matches | Architecture corroborated; transport details still require controlled reverse engineering |

### Differences and corrections

1. Kernel target and maturity differ. bsg100 targets Linux 6.6 and has hardware-tested patches; this project targets stable Linux 7.1.3 and keeps 72 patches as a build/review layer. A 6.6 patch or API decision is not automatically valid on 7.1.3. Reuse the subsystem concept only after a source-level check against the current kernel.

2. The panel history is internally inconsistent across both projects. bsg100's README quick facts and older driver-port material retain R63419/WQHD/CMD wording, while its later hardware logs directly support SSD2092/FHD/video. Our named-device capture selects an NT36672-named LCM but has no silicon readback; it also contains an unbound `solomon_touch@0x53` candidate and an active NVT `cap_touch@0x62`, so its mixed `SSD2092` suspend label is not independently attributable. R63419 is retained only as an alternate/inactive vendor-DTB hypothesis; NT36672 versus SSD2092 remains a panel-variant/identity gate, not a settled board fact.

3. AW9523B mainline status is version-sensitive. bsg100's 6.6 notes say AW9523B was absent and add a new GPIO driver. Linux 7.1.3 already contains pinctrl-aw9523 support, so our preferred boundary is to reuse that and standard matrix input; this is not a contradiction about the chip.

The bsg100 hardware log also reports successful physical typing with a
53-key base capability set and an Fn layer implemented as AltGr. That agrees
with the fresh Gemian capability count of 53 and with the installed XKB
`<LWIN>`/ISO-Level3 function layer. It does not identify the evdev code for
the physical Fn position, nor prove that its 6.6 build used the same vendor
source as the running Gemian image; the local `KEY_FN` versus `KEY_LEFTMETA`
discrepancy therefore remains an explicit runtime/provenance gate. See the
[capability comparison](../2026-07-12-input-backlight-recovery/results/live-keyboard-capability-compare-20260714.txt).

4. PMIC strategy differs by evidence level. bsg100 correctly flags the absence of a mainline MT6351 MFD/regulator/RTC path in its 6.6 baseline and uses fixed-rail stubs. Our live device has a verified MT6351 E2 HWCID and the local series contains a new MT6351 MFD/regulator/EINT path with runtime consumer safety still gated. It is a source-audited 7.1.3 implementation, not an assertion that an upstream MT6351 driver already exists; runtime readback is still open.

5. eMMC compatibility is not generic. bsg100's successful 6.6 path first exposed that an MT6795 compatibility record produced the wrong divider and pad-tune layout, then used the upstream mt2701 record plus pinmux-only groups. Our 7.1.3 work instead carries a dedicated MT6797 record and a conservative board node. Both histories support evidencing the MT6797 register layout rather than inferring it from the nearest SoC name.

6. Boot/flash assumptions are intentionally not shared. bsg100 documents targeted mtk w boot2 and mtk w linux operations and a scatter/SP Flash Tool recovery path. Our repository keeps flashing outside the ARM64 VM, requires an explicit non-primary target, and does not make any write the default. Its partition names and scatter addresses have not been reconciled with the current live partition map; no address is copied.

7. Evidence packaging differs. The audited commit contains a Linux SP Flash Tool tree, vendor DTB/spec material, raw logs, and generated/binary artifacts despite README wording that some are “not in git”. Our policy stores hashes, sanitized observations, and scripts, while keeping extracted firmware and proprietary binaries in ignored, access-restricted paths.

## Analysis

The independent repository increases confidence in the following narrow contracts: SoC identity, UART resource/baud/pin assignment, the AW9523B address/reset identity, FUSB301A presence at 0x25, the need for MT6797-specific MSDC treatment, and the non-drop-in nature of MT6797 CONSYS. Its panel work supplies strong SSD2092 evidence, but the named-device capture selects an NT36672-named LCM; the resulting conflict demonstrates that even successful bring-up trees and runtime driver names must be checked against direct panel reads.

The bsg100 results do not establish that our Linux 7.1.3 DT or drivers will boot. They also do not establish PMIC rail safety, full ten-CPU PSCI operation, EINT delivery, USB role/VBUS ownership, or Wi-Fi/BT functionality for this device. Those remain gated by the current experiments and a non-primary hardware boot.

## Conclusion

confirmed as a comparative evidence audit, scoped to revision 82321ce64752d5bf006fe7c40c331edbd0dfb702. The source is useful input and contains independently matching observations, but it is not an authoritative hardware specification and is not copied into the patch layer.

## Follow-up

- Keep this revision and its file hashes as the reproducibility anchor for future comparisons; re-audit if the upstream repository changes.
- When a non-primary Linux 7.1.3 image is boot-tested, compare UART, CPU/PSCI, eMMC, AW9523B, panel, and USB observations against the contracts above.
- Before enabling the local panel consumer, capture a bounded panel ID/SEEPROM result on the named device and resolve the NT36672-versus-SSD2092 conflict.
- Continue the MT6797-specific PMIC, EINT, USB, display, sensor, and CONSYS experiments in their existing directories; do not enable a subsystem solely because bsg100 enabled it.
- Add any new direct hardware result to docs/hardware/ with source, confidence, method, and contradictions.
