# Reconnect closed as a limitation; single-lifetime baseline retained

Reconnect is closed for now, not a pending implementation task. Do not reopen it
without an owner decision. No key-installation guarantee or firmware ordering
point exists; the probe needs a new protected TX shape and another internal
owner. The active project is [PIO measurement then DMA/throughput](THROUGHPUT_BASELINE_PREDECLARATION.md).

Owner decision, 2026-10-23: use the TX probe below instead of the RX gate, make
one bounded implementation pass, and stop if the existing path needs new
mechanisms. That stop condition was reached offline. **Fallback selected:**
retain the working single-lifetime driver and move the next Wi-Fi work to
DMA/throughput. No second-lifetime capability, build, installation or boot.

## Standard change and corrected gate

The owner replaces the requirement that no stale event survive with the goal
that stale input cannot cause a confidentiality failure and at worst causes a
failed reconnect. The reasons are the absent firmware ordering guarantee,
vendor reconnect under the same event model, and the cost/shared BT/FM/GPS
scope of rewriting CONSYS lifecycle. These are the engineering rationale, not
proof that the goal is already satisfied. There is still
[no firmware lifetime boundary](FIRMWARE_RESTART_BOUNDARY.md).

The RX gate is rejected: raw descriptors lack key-generation identity. An old
decrypted descriptor can pass a fresh PN context and open a metadata-only RX
latch. A host generation label cannot repair this.

The replacement selected for this pass was one internal, payload-free,
protected QoS-null after key installation/station activation, before the data
phase. Only a matched status 0 inside the existing bound would admit data;
missing, flushed, late or unclassified completion, timeout or generation change
would refuse. Status 0 means transmitted, **not verified encryption**. The
payload-free probe discloses no application payload, even if its interpretation
is wrong; addresses are already known to the AP. It does not independently
prove that later payload data uses the correct encryption key.

Generation-owned key/TX/command operations, drain hygiene and per-key PN epochs
were to be wired together with that probe. 0229 is the dormant drain helper,
not an existing operation-generation implementation; 0230 supplies dormant
key/index/peer/generation contexts. The drain is hygiene only, never retirement
proof. No floor is carried or zeroed at stage 3. No partial production wiring
was made after the probe-path stop condition was established.

## One-pass actual-source result

The [actual-source fixture](tests/tx-probe-path-test.py) compiles the maintained
TX encoder and MAC PID-selection code with ASan/UBSan and fake host I/O:

| Existing-path requirement | Actual result | Consequence |
| --- | --- | --- |
| Native protected QoS-null, 26 bytes, ToDS + Protected + QoS-null | `mt6797_join_tx_descriptor()` refuses it; it accepts only unprotected authentication/association/deauthentication management shapes. | Supporting this frame requires a new native protected TX descriptor shape. The Ethernet data encoder cannot substitute for a payload-free native QoS-null. |
| Reuse the existing internal-frame owner | `skb == join_internal` selects reserved PID 127 once; another reserved allocation and ordinary allocations then refuse. | A probe there exhausts the deauthentication owner and blocks data. Distinct probe ownership is needed. |
| Keep existing completion semantics | Every completed internal frame sets deauthentication status/done and feeds 0228's deauthentication delivery report. | A probe requires distinct completion/lifetime state; relabelling it would corrupt delivery evidence and teardown. |

This is a source feasibility result, not a failed device reconnect. Passing the
diagnostic means the current path's refusal was reproduced, not that the probe
was made fixture-clean. The requested before/after/status/generation gate suite
was not completed: no supported probe transaction exists to test end to end.
No speculative encoder, second internal transaction owner, credit relaxation,
new command, or additional mechanism was introduced to force this pass through.
The timebox is closed; no further reconnect design round follows automatically.

## Requested run and verdicts — not admitted or executed

The intended single attempt was two lifetimes in one boot, 120 s each: join,
DHCP, three pings, SSH, teardown and whole-ledger stage 3 per lifetime, then
sealed export and reviewed return. The source would have required 0228, wired
hygiene/PN/operation ownership and the probe gate, a clean pushed Buildbox
rebuild, exact artifact verification, guarded install/readback and physical
boot2 selection. None of those build/device steps occurred.

The planned branches were safeguard admission refusal; second join with no
status-0 probe (failed reconnect/probe result, consistent with false key
installation but not a unique diagnosis); second lifetime complete (bounded
reconnect under the stated safeguards); any first error stops/export/return.
No retry of either lifetime. This plan does not consume or queue a boot.

## Fallback delivery and next Wi-Fi work

The single-lifetime source baseline is retained unchanged, including 0228's
verdict reporting and dormant 0229/0230. The installed kernel remains
`3da69187`; it is not a rebuilt 0228/0230 artifact. P2E-D1/D2 are consumed and
will not be rerun. The demonstrated 600-second gate, transmitted delivery and
whole-ledger cleanup remain the runtime baseline; general reconnect is not
claimed. Unproven cases remain unsupported rather than hidden by a successful
source diagnostic.

The [roadmap](../../docs/ROADMAP.md#phase-b-usable-wi-fi) now makes the next
Wi-Fi project DMA/throughput: start with the current PIO single-in-flight
completion/credit ownership and shared AP-DMA resource constraints. This is a
handoff, not an authorization in this pass for a new DMA mechanism, hardware
access or build. Key-slot reuse experiments, rekey, WMT stop/off, provider
lifecycle rework and NIC cycling as a boundary remain out of scope.

Residual risks remain explicit: a false key event does not certify installation;
a stale higher-PN descriptor is not bounded by a fresh context alone; stale
management input may disrupt or advance protocol state. The abandoned probe
would bound its own payload exposure and require matched fresh completion,
not prove retirement or encryption. The working one-lifetime driver avoids
admitting the unproved cross-lifetime state. The one-boot allowance remains
unconsumed.
