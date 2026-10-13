# ND4 result — zero native eligibility, regulatory cancellation, verified recovery

One completed negative diagnostic run. Phase A, preservation/seals, quiescence,
service regression and exactly one reviewed recovery passed. Native delivery
and the healthy four-state cycle did not pass. No firmware-mode acceptance,
authentication/replay, sustained throughput or maintained-driver claim.

## Exact identity and evidence

- Kernel `258c88b1dff36b04e2dc9546c8e14d8d021aa86e`, native diagnostic profile;
  [reviewed source](ND4_SOURCE_REVIEW.md) and [build/preparation](ND4_PREPARATION.md).
- Package `178cf67da473b49e9a665fa503395e27f8538d06e5f5d9b2ddaa88ba0d026f2a`;
  runtime/tooling `36f446eefb3f81d4f7ff49fb5b1ffc927df2cba9`.
- [Real receipt](results/native-delivery-candidate-4.json)
  `b7ca24a196fb416b25ce6e078770087b96d3ea240dd9928230d1e3156d7dd079`;
  raw boot `f6eb9084c6cad5bc466359d3858df6253bb950983e82d50ffe9e9cd6cb2864c3`,
  12668928 bytes; full boot2
  `7ce16dc852c1d89881c3ed4e676713fde1f8af755f297cc3e9671cddf6819a0c`,16777216 bytes.
- Custodian-reported guarded installation: actual derived installer
  `519fc894d4ec55e32265a67d5e31a9f8fd5b886986d7dcce224f6a1a17e58bdc`,
  real deployment receipt
  `9910c1cea811ae9c1c2ee1d8c6cdcaf178553775e7df4301a81636ab3658f02b`;
  live Gemian/GPT/root/power and ND3 predecessor verified, full16MiB readback
  matched ND4, clean shutdown and owner physical boot2 selection completed.
  The deployment receipt digest is custodian metadata, not newly fabricated
  deployment evidence or an independently rehashed receipt import here.
- Mainline `fcd9b371-0a18-41d0-939b-c3244b227ace`, exact native release/aarch64;
  strict identity and wpa_cli pin verified. Phase A ran once, common-init285
  passed, `ready_for_scan=true`.
- Complete log `fc1b2243272ec09ae234939d25da307381ca8715ac2aec2686e9bb78ec239ddf`,
  159528 bytes /2053 records, sequence-zero-through-explicit-seal coverage.

The author verified all13 payload checksums in the supplied sanitized14-file
bundle. Raw retained captures remain private with the sole laptop custodian.
No payload, AP/own address, PSK, IV, PN, key, lease identifier or personal host
path is published. Boot IDs and deployment/evidence digests are publishable
under project policy. Worker analysis used source and sanitized metadata only.

## Actual native window

| Sequence | Boot microseconds | Observation |
| --- | --- | --- |
| 2033 | 219867057 | DATA opens: budget6188ms / teardown margin5000ms |
| 2034 | 219887618 | Enable pending: state1 / action1, total0 |
| 2036 | 219912719 | ACTIVE: state2 / action0, total0 |
| 2037 | 219959661 | Sole first-call descriptor sample, below |
| 2038 | 220311625 | DATA TX PID5 / pages3 / bytes342 |
| 2039 | 220312871 | PID5 TX-done status0 |
| 2041 | 221399583 | DATA ends: disconnect, elapsed1532ms, TX queued/done1, failed0, credits3; inherited RX unicast/group/dropped0 |
| 2043 | 221415589 | Disable submitted: state3 / action2, total240 /56711B /native0 |
| 2044 | 221431684 | Terminal -ECANCELED, first0, submitted0x801, debt1, cleanup0, branch9 |

CLOSED was not recorded. Actual original classifier replay on the supplied
numeric chronology and SSH receipt exactly matches the supplied native verdict:
`counts_ok=true`, `sequence_ok=false`, `fault=true`, `malformed_records=0`,
`eligible_delivery=false`, `native_delivery_pass=false`. New telemetry did not
corrupt its strict grammar. There is no first queued-native MPDU/crypto flag
record: absent samples are not evidence that bypass flags were set.

All consumed native sample traffic was attributed to ACTIVE: descriptor class2
count238, class7 count2. Pending/drain/CLOSED counts0. These descriptor bits do
not identify MPDU type, protection, peer or authentication. Exactly238 actual
ordinary-native decoder calls were recorded, blocked0 and eligible0:

| First failed gate | Calls |
| --- | ---: |
| Header translation | 35 |
| Conservative FCS metadata filter | 2 |
| Reported header length not24/26 | 153 |
| MPDU span too short under the current group/header interpretation | 5 |
| Version/frame-type check | 43 |
| **Sum** | **238** |

Each call contributes only its **first** failed gate. All238 failed before the
Protected check; protection and later crypto shape were not evaluated, not
proved absent. The two other consumed classes are not decoder rejections.
Inherited translated RX unicast/group/dropped0 is not decoder-call evidence.
No eligible frame was queued, so no authentication/replay conclusion follows.

```text
one-shot WLAN native RX descriptor: phase=1 bytes=442 fields_valid=1 type=0x4e00 channel=40 header=0x18 groups=0x7 msdu=0 status=0xe004
```

This is one admitted call's buffered descriptor metadata, not payload evidence.
`fields_valid` attests byte availability, not correctness of the assumed layout.
Its reported header24/group mask7 gives the current parser offset64; it cannot
characterize the153 reported-header rejections or establish protected EAPOL,
management subtype, on-wire DHCP traffic or firmware mode semantics from442B.
No other descriptor or payload sample exists.

## Branch9: source-defined host cancellation, not ND3's HIF error

There is **no HIF refusal line** in the complete retained log. ND3's branch4
`-EPROTO` was not reproduced; its root cause remains unresolved.

The exact built mac.c SHA
`47dbe9567a216aef6ae2703ee13204c49eb9594c1015c64f369e45598dd4c751` has one
explicit branch9 caller: `mt6797_mac_join_regulatory_stop`, called by the
regulatory notifier under RTNL and the MAC mutex, before policy submission.
It deliberately fail-stops with `-ECANCELED` when a joined lifetime is running,
not retired and not fully cleaned up. This names the cancellation caller, not
a firmware error. The footer prints first_error before latching the new failure.

At disable submission the shared ledger gains one page and pending credit.
The later debt1/cleanup0/absence of CLOSED is consistent with regulatory
cancellation before that credit was reconciled; it does not prove firmware
refusal, nonacceptance or verified retirement. No deauth subtype12 was submitted
(mask0x801, unlike ND3's0x1801). Fail-stop closes host producers and stops the
worker; it neither refunds the owed page nor proves firmware cleanup.

The actual downward STA-state callback can end DATA with reason=disconnect and
request cleanup. Upstream cfg80211 also has an asynchronous disconnect-triggered
regulatory restore path. The retained complete supplicant export records
BEACON_LOSS, followed by locally generated disconnect reason4 and
COMPLETED-to-DISCONNECTED; a later reason3 belongs to cleanup. This establishes
local beacon-monitor disconnect, not an AP/firmware failure. Supplicant line
order has no aligned monotonic timestamps; the exact regulatory requester/
initiator remains unlogged. Regulatory channel flags may already have changed
before the notifier; simply ignoring or deferring it is not admitted.

### Existing beacon path under native sampling

Supplemental kernel records show only two beacon deliveries:
sequence2011 at219736683us and2028 at219839860us, each bytes378/RCPI110/keyed0,
counts1/2. Both precede ACTIVE at219912719us. The delivery helper logs the first
four, so absence of a third log is not exhaustion of its four-record print cap.
This is evidence of no subsequent delivery through that helper in the retained
run, not evidence that no beacon arrived on wire.

Both existing beacon selectors execute before the ordinary-native hook, but
their descriptor gates exclude class2:

- `mt6797_scan_frame` requires `(type & 0xe00f) == 0xe001`; it walks groups4/1/2/3
  with sizes16/16/8/24 and an optional two-byte pad, requires header24, vector
  group, unprotected beacon/probe FC and its strict clean metadata. The join
  caller further requires successful association, channel40 and matching AP
  addresses before handing the original buffered MPDU to normal mac80211.
- `mt6797_join_keyed_beacon` requires exact type0xee01, groups1/2/3 at fixed
  offset64, exact keyed descriptor/status/index fields and an unprotected
  beacon with broadcast destination and matching AP addresses. It is admitted
  only with group key installed and cleanup not done.
- Observed first-call type0x4e00 fails both descriptor gates before either can
  inspect its MPDU. For groups7/header0x18, the current shared group walk gives
  offset64, remaining378 bytes, the same length as the pre-ACTIVE delivered
  beacons. That numerical fit is **not** an FC/address/payload proof of a beacon.
  The ordinary-data decoder rejects non-data/version shapes before Protected;
  its43 first frame-type failures are not confirmed beacon subtypes.

This is a concrete host-selector mismatch for a hypothetical correctly formed
native class2 beacon, consistent with the observed local beacon-loss mechanism.
It does not yet establish the actual class2 management-frame layout/content or
authorize reconstructing a header, fabricating a beacon, disabling monitoring,
weakening the ordinary predicate or delivering unidentified buffered bytes.
Exact built scan-wire.h/action-frame.h and MAC call-site source, not a later
phase-b tree, must ground any normal-MLME native-management proposal.

## Readiness, preservation and final recovery

Helper: named join fault, READY absent, SSH not attempted; group quiescent/safe,
not timed out. Retained leaf scalars are DHCP exit137/bound0/lease0/listener0/
READY0/data_checks_failed1. Only an80B udhcpc log was exported from cycle1; cycle evidence
reports `complete=false` without truncation. That incomplete data/check cycle
does not contradict complete kernel logging/preservation. No lease/READY is
not proof that no DHCP reply arrived on wire or was withheld. No readiness
contract bypass or positive station result.

Device quiesced with boot match and empty faults. Independently all63 seals
matched manifest
`45b73d575651a63f5c45448993de1fda4116f46bedea1d4ebb99ae293a004f60`.
Final `deferred-start-result` reports service regression PASS and recovery
requested/confirmed. Exactly one reviewed recovery request; its return collector
made two connection attempts, not two recovery requests. Independent strict
Gemian verification confirmed `3.18.41+`, aarch64, changed boot
`2099d541-361a-4866-8560-4f717779d130`. The interim request record's
`recovery_confirmed=false` predates that final confirmation and is not the result.

## Next decision boundary

No unchanged ND4 retry, new source/test implementation, build or device action
is admitted by this result. The supplemental disconnect/leaf files independently
passed their checksum manifests. They narrow the issue to local beacon loss,
while regulatory requester and actual native-management content remain unknown.
The smallest proposed next test is an actual-source selector/dispatch fixture
for a source-defined native class2 management beacon, proving where the current
selectors withhold it and validating group/pad offsets. No source correction is
admitted until the coordinator's bounded source/RE interpretation establishes
the layout and normal-MLME delivery contract. The dominant first-header rejection
also needs its actual value; retargeting the existing single descriptor sample
to the first admitted HEADER rejection remains a conditional alternative, not
the selected next patch. No implementation has begun; await advisor then
coordinator decision, preserving all eligibility/crypto/monitor/readiness guards.

[ND3](ND3_RESULT.md), frozen inputs and C35/R36 remain unchanged. No maintained
lifecycle/reuse/rekey/hostile-replay/IRQ/DMA/clean-profile acceptance is claimed;
the full maintained Wi-Fi objective remains incomplete.
