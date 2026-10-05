# C3 attended boot protocol

Status: draft, 2026-10-06. No candidate is composed or validated, and no
device action has been taken under this protocol.

## Hypothesis and unique observation

On the negotiated full-mode STP session, the ROM answers WMT Bluetooth
function-on and then HCI Reset on task 0, without a ROM patch or RF
calibration (H1). It also returns Read Local Version and Read BD_ADDR (H2).
The unique observation is the first non-WMT task reply ever seen on mainline.

## Candidate

Use the validated package from `9a1230ca`, profile
`mt6797-a53-stp-task-routing-compile`, package inventory
`172c1565465941ff7d7e9daae4c00d5cc20f79ecab7a927e5c6645d00d10202a`.
Compose it from the booted WMT-versions parent, as its
[build-candidate.py](../2026-10-03-mt6797-wmt-versions/build-candidate.py)
does. Change only the kernel image, the RAM-root release gate and these
DT properties. Resolve every phandle from the booted DT; never copy one from
the build.

| Node | Change |
| --- | --- |
| CONSYS | Remove `mediatek,one-shot-wmt-identity-capture`. Add `mediatek,one-shot-wmt-negotiate` and `mediatek,one-shot-bt-reset`. |
| CONSYS | Append the `afe` region, `0x180b6000` size `0x100`, as the tenth `reg`/`reg-names` entry. |
| CONSYS | Add `vcn33-bt-supply` pointing at the new VCN33-BT regulator node. |
| MT6351 regulators | Add `ldo-vcn33-bt` with `regulator-name = "vcn33-bt"` and no other constraints. |
| WLAN child | Keep `status = "disabled"`. |

The VCN33-BT node has no `regulator-always-on`. If the loader left the rail
on, late regulator cleanup would switch it off, and the driver's own check
would then refuse. Both outcomes are safe and visible in the log.

Validate that the composed DTB passes the CONSYS binding. The binding
rejects the Bluetooth flag without the negotiation flag or the supply.

## Sequence

1. Confirm the changed boot identity, release
   `7.1.3-gemini-a53-stp-task-routing-compile`, USB SSH and the active console.
2. Preserve region 19 and prepare WMT memory exactly as the WMT-versions
   session did.
3. Write `1` once to the `wmt_negotiate` trigger. In one call, the kernel runs
   the default query, the set-options exchange and the full-mode query (the
   control), then the five Bluetooth steps.
4. Save `dmesg`. The control passes only if the log shows
   `one-shot WMT negotiation: result=0`. Bluetooth passes only if the log
   shows `one-shot BT H1: result=0 completed=5/5`.
5. Seal the log, run the existing A53 serviceability regression, and return to
   Gemian through the reviewed recovery path.

Budgets: one trigger. Negotiation keeps its 1.6 s budget. The Bluetooth steps
have 600 ms each within 3 s. There is no retry, and no ROM patch, calibration,
WLAN start or scan. The raw Bluetooth reply bytes, including the address, stay
in the private log.

## Decision branches

- **Negotiation fails.** This is a regression of the validated control. Stop
  and diagnose offline; the Bluetooth result is void.
- **All five Bluetooth steps pass.** H1 and H2 hold. Bluetooth can proceed
  ahead of common init, and task 0 becomes the positive control for GNSS.
- **BT on passes, HCI Reset fails.** Task delivery or sequencing is wrong.
  Inspect the raw frames and link counters offline.
- **BT on fails.** Bluetooth function-on needs the patched image; H1 is false
  and Bluetooth waits for common init.
- Unexpected heat, power or recovery behaviour: follow the stop rules in
  [SAFETY.md](../../docs/SAFETY.md).
