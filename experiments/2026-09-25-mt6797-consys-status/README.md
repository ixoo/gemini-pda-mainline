# Passive CONSYS power-status gate

Status: candidate preparation; no new board result yet.

The first Wi-Fi hardware question is whether retained firmware leaves CONSYS
powered at mainline late init. The working Gemian boot is an active-WLAN
reference, so its enabled `pg_conn` clock does not answer that handoff question.
The retained MT6797 sequence identifies CONN bit 1 in both SPM power-status
registers at offsets `0x180` and `0x184`; see the
[power-domain analysis](../2026-09-05-mt6797-wifi-contract/POWER_DOMAIN.md).

[Patch 0545](../../patches/v7.1.3/0545-soc-mediatek-observe-MT6797-CONSYS-power-status.patch)
uses the existing SPM syscon, already shared by the A72 platform-state reader,
to read those two registers twice during late init on Gemini. It classifies
only the CONN bit as `off`, `on`, `mixed`, `moved`, or `unavailable`. It makes no
power, reset, remap, firmware, radio, or DMA request and never treats a status
as an ownership grant. It is default-off outside the named
[`mt6797-a53-consys-status-snapshot`](../../kernel/manifest.json) profile,
which retains the tested A53 service foundation and its RAM-boot facilities.

## One-boot decision

Use one guarded boot2 image assembled from the validated package and the
accepted RAM candidate, with only the kernel and its exact release gate
changed. Authenticate the mainline boot and preserve its complete log before
recovery. The unique measurement is the single `mt6797-consys-status` line
bound to that boot identity and candidate hash.

- Stable `off` in both reads permits designing a separately reviewed shared
  CONSYS/EMI/AP-DMA owner; it does not authorize activating the radio.
- `on`, `mixed`, or `moved` means the handoff is not an attributable cold-off
  state. Stop active Wi-Fi bring-up and investigate the retained owner.
- `unavailable`, a missing record, or an unverified boot identity makes this
  boot inconclusive. Diagnose the observation path before any new boot.

Do not repeat an identical image without a decision-changing measurement.
The owner selects boot2 physically after the guarded write and clean shutdown.
Use the established authenticated USB/RAM collector and reviewed return path;
confirm changed-boot Gemian afterward.

This gate establishes neither usable Wi-Fi nor the shared manager, firmware
load, station association, or traffic. Those require separate implementation
and measured device tests under the [shared owner contract](../2026-09-05-mt6797-wifi-contract/SHARED_OWNER_IMPLEMENTATION.md).
