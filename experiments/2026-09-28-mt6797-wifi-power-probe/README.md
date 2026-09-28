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
in the `mt6797-a53-wifi-power-probe` profile. Its synthetic author carries no
DCO certification. The active DT property is confined to this named profile;
the passive firmware profile remains unchanged. A validated Buildbox package
and exact boot2 candidate are prerequisites for any owner-selected device boot.
