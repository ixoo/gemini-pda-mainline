# Firmware lifetime boundaries — offline audit results

Owner direction, 2026-10-23: Track B resolved negatively. Keep protected re-arm,
key-slot reuse and rekey disabled. Dormant proposals 0229/0230 remain necessary
host prerequisites for Option A; they do not prove retirement. No command,
sampler, rebuild, installation or boot is performed by this work.

## Negative event/credit result

The preserved P2E-D2 kmsg SHA-256 is
`006210923ecddecc6c9f652e00b23f4c910e3d828c4d3b2cc69787e66c7c41e4`,
with 4,966 records. The offline fixture verifies that digest and these exact
records without publishing raw captures or device addresses:

| Key | Released-page credit record / timestamp (us) | Key-done record / timestamp (us) | Event after credit |
| --- | --- | --- | --- |
| Pairwise | 2031 / 22738443 | 2035 / 22743502 | 5059 us = 5.059 ms, about 5.06 ms |
| Group | 2042 / 22798396 | 2043 / 22799475 | 1079 us = 1.079 ms, about 1.08 ms |

The MAC's join-credit log follows subtraction of `account.released_pages`
from `join_page_debt` in `mt6797_mac_join_guard()`. This is released-page
reconciliation, not unrelated host bookkeeping. The owner's static dispatcher
evidence supports the same distinction: dispatch calls the command-table
handler and releases its command page immediately afterwards; the event is
produced later. The exact supplied dispatcher/table locations are retained in
the ignored offline evidence note. No new binary analysis was executed here.

**No host-visible ordering point proves that all earlier firmware events have
been emitted. A second protected lifetime cannot be admitted on credit or drain
evidence.** A later reply, empty queue or quiet interval cannot repair that
missing guarantee. Same-firmware protected reconnect is blocked on a firmware
capability we cannot add; retain the one-lifetime driver. Option A is a separate
firmware-instance boundary investigation, not a workaround using elapsed time.

## Intended Option A boundary

After lifetime 1 ends, preserve its traffic, delivery and whole-ledger cleanup
evidence; quiesce all owned host work; stop firmware through the identified,
reviewed and exercised stop path; require positive stop completion and retirement
of its event/data producers. Only after that boundary may a new firmware-instance
generation be anchored. Re-run the existing complete start sequence against
fresh, validated host/firmware state, then admit a fresh join. Keys and PN state
come from the new handshake, never from lifetime 1.

A software flag, `mac80211 .stop`, process termination or a message containing
"firmware stopped" is insufficient to establish that boundary. The currently
inspected CONSYS source's `stopped:` label only logs `state retained`; it sends
no firmware stop and performs no reset there. `mt6797_mac_stop()` closes host
join/scan work and clears `started`; it does not stop firmware. This establishes a result: **no firmware stop/off counterpart is implemented
in the inspected driver**. Its start-only WMT/MTKE sequence performs WMT
negotiation/common init, MTKE image transfer and HIF START; MAC `.start` is not
that sequence. `mt6797_hif_start_submit()` refuses `start_attempted`, giving one
START per HIF context; because the built-in owner is retained for the boot,
that is one start per boot by construction. Do not substitute a new reset,
power operation or command.

## Ranked boundary decision — cheap provider re-probe evaluated first

| Boundary, in cost order | Offline result | Decision |
| --- | --- | --- |
| **1. Provider re-probe** | The provider is built in, suppresses bind attributes, has no removal callback, retains the global `bound` owner and returns `-EBUSY` on a second probe. No successful-removal path retires firmware/HIF/wiphy or restores cold domain/EMI state. | **Unavailable in the current driver.** The actual-source fixture reproduces refusal before reinitialization. Unknown hardware state independently forbids a device attempt. |
| **2. NIC power-cycle (`0x04` disable/enable)** | Firmware keeps running; its event producer survives. | **Not a lifetime boundary.** It may be part of reinitialization but cannot resolve event ordering. No command issued. |
| **3. New WMT stop/off command** | No counterpart is implemented. ROM WMT stop/off semantics and shared BT/FM/GPS effects need analysis. | **Owner decision required before starting that project.** No handler analysis, command design or implementation is begun here. |

**No firmware lifetime boundary is available in the current driver today.**
Provider re-probe has been tested offline first; its failure does not authorize
WMT lifecycle development. The one-boot allowance remains unconsumed.

## Provider re-probe prerequisite inventory

Classification describes the required treatment, not a working restart path.
Any UNKNOWN prevents candidate preparation. Known host reinitialization work
also must be implemented and fixture-verified before this inventory can close.

| Item | Classification | Actual source assumption / required closure |
| --- | --- | --- |
| CONSYS hold/ownership and provider lifecycle | **Re-initialise** | The static `bound` owner persists, `.suppress_bind_attrs=true`, and no `.remove` callback exists. A second probe returns `-EBUSY`. No path currently reinitializes the owner; do not clear the latch to evade refusal. |
| Power-domain/reset state | **UNKNOWN** | Probe attaches an OFF domain; power-on also requires OFF and initial rail/reset state. Successful firmware use retains the powered owner; no supported reverse lifecycle restores these conditions. |
| WMT negotiation and STP transport | **UNKNOWN** | CONSYS retains `wmt_query`, `wmt_negotiate`, version/BT state and transport sequence/ACK state. Whether WLAN-only stop preserves usable WMT state or requires full negotiation is not established. |
| WMT setup completion/preparation/trigger | **Re-initialise** | `wmt_init_attempted`, `wmt_init_complete`, `deferred_start_armed`, `deferred_start_attempted` are boot-owner gates; preparation also requires the domain off and original EMI/remap state. The same deferred trigger refuses after the first attempt. No authorized reset of these gates exists yet. |
| EMI mapping, protection and contents | **UNKNOWN** | Region reservation identity is reusable, but runtime writes, retained contents, sealed policy, ownership and legal copy/reseal order after the selected stop are unproved. `emi_set_attempted`, `emi_copy_attempted`, `emi_sealed` are not reset by teardown. |
| Firmware image and immutable inputs | **Reusable** | Exact validated input bytes can be retained/re-requested; this says nothing about reusable runtime RAM, mappings or hardware state. |
| HIF INIT and normal credits | **Re-initialise** | Fresh HIF/INIT/normal transactions must follow a proven cold firmware boundary, not a software-ledger reset alone. INIT assumes 104 pages; normal pools and data debt need their independently established initial state. |
| HIF cold hardware state | **UNKNOWN** | The start worker requires no pending port record, correct chip identity and WLAN-ready clear. No same-boot post-stop guarantee currently establishes these conditions. |
| Adapter, wiphy and BSS/station slots | **Re-initialise** | The built-in owner retains HIF/wiphy for the boot. Fresh registration/configuration and station/BSS state need a reviewed object teardown/recreation lifecycle. Reusing a terminal MAC would encounter closed/scan/CCMP guards. |
| Private board record | **Re-initialise** | `mt6797_wifi_record_prepare()` allocates and validates a record per call and release frees it. Re-request the exact validated bytes and repeat supported configuration; do not infer firmware application from an old `configured` flag. |
| Regulatory/domain/power configuration | **Re-initialise** | `mt6797_mac_load_record()` sends supported policy/NVRAM/power settings and sets `configured`. Repeat on fresh firmware; confirm notifier/RTNL lifetime and no old-wiphy callback survives. |
| RF calibration and common init | **UNKNOWN** | Common init includes ROM patches, coexistence, rail steps, antenna mode and RF calibration. Whether the selected WLAN stop invalidates these or safely permits replay is unknown. Retained `completed`, result, calibration bytes and rail/transport state cannot certify a second init. |
| Keys, PN epochs and generation | **Re-initialise** | Anchor generation only after proven firmware stop. New handshake and fresh per-key contexts; old contexts retired only at that proven boundary. No same-instance slot reuse or protected re-arm. |
| Snapshot and retained diagnostic state | **Re-initialise** | Quiesce any existing session/reader, retain evidence, and create fresh owner state. No snapshot/sampler is run to establish restart. |

### One-shot guards and retained state requiring treatment

The audit covers the actual CONSYS, HIF and MAC source identities in the
[scalars record](results/firmware-restart-offline-audit.json). It does not claim
that uninspected WMT/transport internals are closed; they remain UNKNOWN above.
These are guard families, not permission to clear sticky flags:

| Owner | Complete relevant guard/state family in inspected source | Treatment |
| --- | --- | --- |
| CONSYS | `bound`; `wmt_init_attempted/complete`; `deferred_start_armed/attempted`; `emi_set_attempted`, `emi_copy_attempted`, `emi_sealed`; `fw_start_attempted`; retained `fw_transaction`, `fw_hif`, `wlan_hw`; common-init result/completed/rail/calibration and WMT transport state | Fresh reviewed instance lifecycle required; hardware and WMT/EMI reset semantics UNKNOWN. Keep existing refusal paths. |
| HIF | `start_attempted`, `firmware_ready`, `capability_attempted/complete`, `tx_status_boot_attempted`, `tx_status_normal_attempted`, `tx_status_accounting_baseline`, `port0_attempted/reported`, `first_error`; INIT/normal transaction phase, sequences, deadlines, pools and scratch | Re-initialise only behind proven firmware-instance retirement. Duplicate START refuses and poisons; download after START refuses. No in-place clearing of poison. |
| MAC configuration/interface | `configured`, `started`, `closing`, `first_error`, vif/wiphy/regulatory state, `scan_ready`, `scan_used/active`, `bss_active`, scan counters/credit/tuning state | Fresh object lifecycle; `.start` alone skips firmware, board and policy initialization. `.remove_interface` latches `closing`. |
| Join ownership | `join_running/open/retired/closed`, `join_rearm_pending`, `join_lifetimes`, scan/peer/auth/association/BSS/channel/station latches, tokens/sequences/PIDs and slot ownership, in-flight/queued frames, command/data page debt, deadlines and bounded packet/poll counters | Re-initialise in a new owner after proven stop, not through protected re-arm. Preserve old errors/evidence. |
| Cleanup and keys | cleanup requested/done/stage, removal states and submitted flags, key-done windows, reserved-deauth ownership/status/timeout/late evidence, page quarantine/bounded debt and credit tracking | Require attributable terminal outcome and quiescence; new firmware/key instances get fresh state. |
| Protected/native diagnostics | `ccmp_closed`, PTK/GTK attempted/seen/active/seeded contexts and key pointers, TX readiness/decap, PM/DTIM/channel-release/loss and cleanup observations; native diagnostic state, sample/report/format latches, counters and budgets | Re-initialise in new owner only; do not reset an old epoch at stage 3 or infer a firmware restart from a host reset. |

## Actual-source fixtures and established results

The [fixture](tests/firmware-restart-boundary-test.py) compiles the actual HIF
START function and MAC `.start` plus the exact deferred-trigger predicate,
with fake transport/kernel environment only. It verifies:

- a second provider probe returns `-EBUSY` while the static owner remains bound;
- bind/unbind attributes are suppressed and no removal callback exists;
- a second deferred start trigger is refused before any power/start work;
- a second HIF START refuses with `-EIO`, retains poison and performs no transfer;
- successful MAC `.start` does not repeat HIF START or the required initialization;
  treating that host-only success as a restart is explicitly refused;
- a closed MAC refuses `.start`; the CONSYS `stopped:` tail only logs retained state.

These fixtures establish refusal/coverage of current source, not a working
second firmware start. The requested second-start success fixtures remain
unimplementable until an available lifetime boundary is established and all UNKNOWN items are resolved.
No driver or admission code is changed. These are source audit results, not a generic blocker note.

**Candidate does not proceed. No restart run is predeclared yet.** Once the list
is closed, the separate predeclaration must bind one boot to: lifetime 1 join,
120 s traffic and teardown/whole ledger; verified firmware stop; generation
anchor and complete firmware start; fresh handshake and lifetime 2 join,
120 s traffic and teardown/whole ledger; evidence export and reviewed return.
Second-start refusal/partial initialization is a boundary result; second join
with failed traffic is a host/start-state result; any first error stops the
procedure, preserves evidence and returns. No retry. Security state is always
re-established from the handshake. The one-boot allowance remains unconsumed.
