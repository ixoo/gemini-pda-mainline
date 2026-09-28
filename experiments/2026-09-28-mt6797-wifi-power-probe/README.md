# One-shot MT6797 CONN power-on probe

The passive WLAN image validated its complete four-section firmware plan, but
has never obtained a powered downloader. This named experiment extends that
exact A53 patch selection with one opt-in CONSYS power-on attempt. Firmware
remains loaded for inspection only: no remap, EMI policy, ordinary transfer,
START command, radio registration or power-off is attempted.

The hypothesis is that the existing MT6351 regulators, TOPRGU reset controller
and modern MT6797 CONN provider can establish a stable ON state in the order
observed in the working Gemian source. Before effects, the owner requires an
initially OFF CONN domain, OFF VCN18/VCN28 regulator requests, the Gemian-seen
VCN28 clock-select fields, and the exact MT6351 regulator ancestry. It then
sets 1.8 V and 2.8 V selectors, votes VCN18 on, waits at least 240 µs, selects
VCN28 hardware control, votes VCN28 on and checks its two control bits. It sets
the claimed CONN-to-AP sleep-mask bit, asserts and checks CONMCU reset, checks
CONN still OFF, and makes exactly one runtime-PM resume request. The provider's
dual hardware status must subsequently confirm ON without a retained fault.
The test keeps reset asserted and does not access the CONSYS device window.

This is a one-boot observation, not a normal Wi-Fi power lifecycle. The owner
does not drop a regulator vote, reset claim or domain reference after any
uncertain effect. It disables runtime PM after its sole request to block another
transition and remains bound until the reviewed system restart. The selected
provider independently retains prerequisites when its transition faults. A
failed probe step is logged, while the host's authenticated A53 service and
complete kernel-log collector preserve evidence before reviewed recovery.

## Decision branches

- A source, schema, config, build or package failure rejects this candidate
  before any device use.
- An OFF/rail/clock-field/PMIC-ancestry admission refusal means the physical
  starting state differs from the observed reference; do not bypass the gate.
- A regulator, mode, sleep-mask or reset failure retains effects and redirects
  diagnosis to the first failing operation. No retry or generic unwind follows.
- A runtime-PM or confirmed-ON failure retains prerequisites and requires the
  complete log plus the reviewed return path before another candidate.
- One confirmed-ON record with a passing A53 service result demonstrates only
  this power-on slice. Next work must establish a safe reset release/readiness
  path and EMI owner before firmware execution. It does not demonstrate Wi-Fi.

The implementation is [patch 0036](../../patches/proposals/0036-soc-mediatek-probe-one-retained-MT6797-CONN-power-on.patch)
in the `mt6797-a53-wifi-power-probe` profile, with a distinct kernel
release. Its synthetic author carries no DCO certification. The active DT property is confined to this named profile;
the passive firmware profile remains unchanged. A validated Buildbox package
and exact boot2 candidate are prerequisites for any owner-selected device boot.

## Prepared candidate

The clean Buildbox build of commit `0d7f1582f4822c97b2c9803c9e1836485eab5364`
produced kernel package inventory
`47c065fdf0a54dac7d38ec1f1e62d51726d03bd8934a8d4219951c21bace1ab7`.
The exact binding passed `dt-doc-validate` and focused `dt_binding_check`;
the compiled Gemini DTB passed `dt-validate` against that schema. The
[checksum-only candidate receipt](results/candidate.json) identifies the
boot image and full boot2 padding. Private image bytes and the retained
firmware remain in ignored artifacts. No active-power device result is claimed
by this preparation.

`retarget-initramfs.py` changes only the authenticated RAM-root release
string. `build-candidate.py` checks the boot-tested passive parent, immutable
Buildbox package, retained firmware and DT delta before packaging. The
`install-passive.py` wrapper derives the reviewed guarded boot2 installer and
pins the predecessor; `passive-host.py` and `watch-boot.py` collect one
attributable result and reviewed Gemian return.

The parallel [HIF executor review](../2026-09-28-mt6797-hif-executor-review/README.md)
records the caller-owned transport gaps after power and EMI admission.

## First watch

The [first sanitized watcher result](results/watch-1.json) records an unchanged
`mediatek-20ff` USB stage for the 900-second window and zero device SSH
attempts. No mainline kernel log or power-probe outcome was obtained. A single
post-watch Gemian LAN connection also timed out; that check does not establish
the PDA's screen or boot state. This is not a tested failure of the CONN power
sequence. A fresh physical handoff and newly armed collector are needed before
another device observation; the expired watch itself does not authorize a retry.

## Power-on runtime result

The [sanitized runtime receipt](results/runtime-1.json) records a new,
authenticated mainline boot after a fresh USB-stage transition. The complete
private kernel log has one `domain confirmed ON, reset held` record, no
`power probe stopped` record, one registered provider, and acceptance of all
four retained-firmware sections as a plan. This confirms the provider's
point-in-time dual-status ON check after the single power request. The CONMCU
reset remained asserted; no CONSYS window read, firmware execution or mainline
Wi-Fi operation was attempted.

The host collector requested the reviewed Gemian return, but its return check
looked for the private SSH key under the isolated source worktree. That key
exists only in the primary ignored artifacts, so the collector marked the
return and full A53 regression inconclusive. A separate bounded read-only
connection using the primary pinned identity confirmed a changed Gemian boot
with WLAN carrier. The host wrapper now binds the return collector to the
primary private repository. This correction does not reclassify the original
collector result as a passing full regression.

The next distinct hardware observation must answer whether the CONSYS window
can be read safely with the domain ON and reset held, using the source-defined
chip-ID register as a positive control. Reset release, shared EMI ownership,
firmware execution and networking need separate admission and evidence. The
current boot image should not be rerun for an identical power observation.
