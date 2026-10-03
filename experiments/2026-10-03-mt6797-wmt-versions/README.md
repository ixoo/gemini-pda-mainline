# Experiment: checked pre-negotiation WMT versions

| Field | Value |
| --- | --- |
| ID | `2026-10-03-mt6797-wmt-versions` |
| Status | kernel integration checkpoint; build/schema pending |
| Profile | `mt6797-a53-wmt-versions-compile` |
| Subsystem | MT6797 CONSYS, BTIF and WMT |

The [checked-read draft](../2026-10-03-mt6797-wifi-audit/VERSION_READ_OWNER.md)
and [measured chip reply](../2026-10-03-mt6797-wifi-audit/CHIP_REPLY.md) establish
the next identity-only measurement. HW/ROM response variants remain strict
hypotheses until tested; the owner accepts no fallback tuple or unknown format.

Proposals 0099–0100 reuse `mediatek,one-shot-wmt-identity-capture` for checked
identity reads in this selected series and expose the sole root `wmt_versions`
trigger. No new selector or board patch is added. Historical capture profiles
retain their original implementation. Existing default-query and negotiation
exclusions, exact WMT memory preparation and deferred-start prepower guards
remain unchanged. The shared CONSYS mutex and consumed deferred-start attempt
span the entire lifetime. The caller runs reviewed BTIF setup once, then checked
chip, HW and ROM reads in order. Separate persistent records retain all counters
and bounded raw bytes after IRQ retirement.

This implements the [current plan's](../../docs/ROADMAP.md#current-plan-2026-10-03-review)
identity measurement only. The re-triggerable common-init executor remains the
next implementation step after the tuple is measured.

The existing query-only continuation guard excludes HIF, EMI-set/copy, WLAN
firmware START and scan; WLAN remains disabled. No negotiation, DLM, patch,
MCU-clock, PA/calibration or radio action follows the version reads. Power and
clocks remain retained after success or failure for reviewed recovery.

[Integration validation](results/integration.json) covers exact scoped forward
and reverse replay and strict Checkpatch. The actual leaf and mocked-owner
fixtures are recorded by the draft. These establish neither Linux compilation
nor live replies, resource admission, applicability or Wi-Fi support.

Build from clean pushed inputs only:

```sh
KERNEL_PROFILE=mt6797-a53-wmt-versions-compile \
  ./scripts/build-kernel --backend buildbox
```

Focused binding/DT validation, candidate construction, finite runtime protocol,
guarded deployment and physical owner boot2 selection remain required. A future
measurement must preserve the first unknown reply without retries, seal the full
session, run the established A53 regression and confirm changed-boot Gemian
recovery. Working Wi-Fi still requires common initialization, calibrated
management reception, association and traffic.
