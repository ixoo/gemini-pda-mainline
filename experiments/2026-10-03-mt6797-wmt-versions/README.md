# Experiment: checked pre-negotiation WMT versions

| Field | Value |
| --- | --- |
| ID | `2026-10-03-mt6797-wmt-versions` |
| Status | one checked tuple passed; evidence sealed, A53 regression and Gemian recovery passed |
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

[Build and focused schema validation](results/build-schema.json) passed. The
[candidate](results/candidate.json), [finite protocol](PROTOCOL.md), and adapted
guards are ready for guarded deployment and physical owner boot2 selection. A future
measurement must preserve the first unknown reply without retries, seal the full
session, run the established A53 regression and confirm changed-boot Gemian
recovery. Working Wi-Fi still requires common initialization, calibrated
management reception, association and traffic.

[Deployment](results/deployment-1.json) resolved inactive logical boot2 from live
Gemian GPT, verified the guarded full-partition write/readback and confirmed
clean shutdown. Capture and preservation/recovery preparation pass offline.
The owner must physically select boot2 before any runtime measurement.

## Runtime measurement (2026-10-04)

The [runtime receipt](results/runtime-1.json) records one changed mainline boot
with checked chip/HW/ROM replies `0279/8a00/8a00`. Each exchange sent 26 and
received 22 bytes in six services; all three terminal results were zero. WMT
setup preserved the suffix and verified the cleared prefix before the sole
version trigger. The independent classifier accepts the sealed full log, not
merely the trigger exit. Sysfs returned read-only, the A53 service regression
passed, and the reviewed native recovery confirmed a changed-boot Gemian.

This candidate is consumed; do not repeat it without a decision-changing
measurement. The tuple resolves checked version selection for this power
lifetime. It does not prove patch applicability/application, common init,
calibration, Bluetooth or Wi-Fi support. Raw logs and memory remain private.
The next device packet is Gemian session A, beginning with passive logs/live
DT; every register read still needs its own admitted access path.
