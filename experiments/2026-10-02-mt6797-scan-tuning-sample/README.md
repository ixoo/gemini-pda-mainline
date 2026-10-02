# MT6797 passive scan tuning samples

Status: source diagnostic drafted; no build, candidate or hardware result yet.

The [consumed counter scan](../2026-10-02-mt6797-passive-scan-count/results/runtime-1.json)
reported zero firmware management-processing count and no host frame or BSS.
The [retained analysis](results/tuning-analysis.json) shows that the selected
scan state advances toward passive listening without checking tuning's return.
Requested channel metadata is written before one tuning failure point, whereas
the completed band cache is written afterward. The scan result therefore leaves
channel setup and receive processing before the counter unresolved.

Patch 0081 adds an isolated, default-off diagnostic for four read-only queries
of two fixed ordinary firmware RAM words. There is no arbitrary address or set
interface. Role 0 reads the completed band-base cache; role 1 reads packed
channel metadata. The query branch's target load has no target write; request
buffer, reply allocation/queue and normal command-credit effects are admitted.
Special firmware prefixes, register writes and calibration changes are excluded.
The archive author is synthetic; this patch has no DCO certification and is
not submission-ready.

## Single-session protocol

Hypothesis: completion with zero management count can result from channel setup
that has not established the requested software state. The unique observation
is two pairs of channel-state samples during one 500 ms passive channel-40 scan,
joined to the existing firmware counter and host frame/BSS result.

Preserve the parent's firmware, private record, board DT, authenticated userspace,
broadcast-filter and BSS setup. Retain the five-second scan deadline, 256 polls,
sixteen packets per tick, 4096 packets overall, TC4 accounting and retired lifetime.
Start pair 0 no earlier than 100 ms and pair 1 no earlier than 300 ms after host
scan submission. Each pair consists of separate band and channel queries; they
are not atomic. Record host submission/reply times and whether a matched reply
arrives after the scan-done event within its existing bounded RX tick.

Use fresh shared command sequences and at most one outstanding query. Each
exact 16-byte event must reflect its fixed address and sequence within 100 ms.
Replies never refund TC4; only the existing returned-page reconciliation does.
Missing, malformed, duplicate or unmatched query replies fail the diagnostic and
retire its lifetime without further cleanup I/O. Do not extend polling after
DONE or issue queries after observing it. Early completion can leave fewer than
four samples; this is an incomplete diagnostic, not proof of tuning failure.
No probe request, association, key, data TX, IRQ enable or packet DMA is added.

- Band base 5000000 and channel metadata 40 during both pairs with zero count:
  prioritize receive/filter processing before the counter. This does not prove RF.
- Stale or different band/channel software state: prioritize tuning/setup, while
  retaining the possibilities of other writers and sample timing.
- Positive firmware count without host frame: investigate firmware-to-host delivery.
- Valid beacon and standard BSS: establish management reception for that candidate.
- Missing/incomplete samples, transport or ownership failure: preserve an
  inconclusive result and retire the lifetime.

Verify exact candidate and boot identity before START. Build and package checks,
guarded live-GPT boot2 installation, full readback and owner physical selection
precede the test. Preserve unique evidence before reviewed recovery; confirm
changed-boot Gemian. A source analysis or successful build is not hardware support.

## Validation

The focused wire test checks the two-address whitelist, query flag, packet
extents, fresh sequence history, command-credit debit with no reply refund,
transport failure, wrong address/sequence/event and truncated replies. Kernel
compilation and lifecycle review remain required before candidate admission.
