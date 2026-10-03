# Bounded TX submission accounting

The [TX helper](tests/wmt-full-stp-tx.h) implements the submission boundary in
[the BTIF transfer review](BTIF_TRANSFER_REVIEW.md). It has no MMIO or kernel
caller. Its concrete purpose is to retain one encoded frame's position while
submitting a command larger than the 16-byte hardware FIFO, then to distinguish
full submission from enqueue or a partial write.

## Contract

Initialization validates one complete encoded WMT data or ACK frame using the
[codec](FULL_STP.md). The caller keeps those bytes immutable and alive throughout
the span. Serialized batch preparation takes one fresh normal-bank LSR snapshot:
TEMT offers at most 16 bytes, otherwise THRE at most 8, otherwise none. It never
offers more than the remaining frame. The snapshot's room applies to that one
batch only. Another batch before commit retires the span.

The caller must perform the actual THR writes under the resource/IRQ ownership
contract, checking the deadline, then report their exact count once. Only a
complete on-time batch advances successful progress. A partial or late batch
records its actual writes but retires the span. Reporting more writes than were
offered, committing twice or using a retired span is a refusal. A completely
written but late frame is not successful submission. No suffix retry follows
from these counters.

The host draft limits each span to 256 room observations, including no-room
observations; a further observation retires before offering bytes. A maximum
1011-byte frame needs at least 127 batches when only eight bytes are offered.
The limit is a finite offline design bound, not a measured latency/IRQ allowance
or admitted effect budget. The future kernel owner must define per-IRQ and
whole-initialization budgets plus real deadlines and prove their coverage.
The expiry input must come from its current protected deadline check, not a
cached flag. Actual MMIO ordering, IRQ serialization and freshness cannot be
proved by this hardware-free helper.

Mark [the exchange sent](FULL_STP_STATE.md) only after the span completes.
Keep buffered RX intact until that commit, then classify complete frames with
[the collector](FULL_STP_STREAM.md) and exact event state. The four-byte outgoing
host ACK uses its own completed span before its ACK obligation is released.
Reinitialization after a failed effect-bearing span is not a retry permission;
the caller retires the lifetime and preserves evidence/resources for recovery.

## Focused checks

```sh
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/2026-10-03-mt6797-wifi-audit/tests/wmt-full-stp-tx-test.c \
  -o /tmp/gemini-wmt-tx-test
/tmp/gemini-wmt-tx-test
rm /tmp/gemini-wmt-tx-test
```

The test submits a maximum frame through alternating no-room, half-FIFO and
empty-FIFO observations and checks exact output bytes and no early sent state.
It composes successful submission, a collected piggyback-ACK event, host ACK
submission and final exchange completion. It refuses room reuse, partial writes,
late completion, exhausted no-progress observations and pre-write expiry.
Malformed initialization leaves its output state unchanged. Strict compiler
warnings and address/undefined behavior sanitizers pass.

The [receipt](results/full-stp-tx.json) pins authored files. There is no kernel
integration, FIFO timing, IRQ-concurrency, peer-response or Wi-Fi result. First
[default-query liveness](../2026-10-03-mt6797-wmt-default-query/SESSION.md) remains
the hardware gate before further transport effects.

The [composed IRQ draft](FULL_STP_IO.md) now exercises these helpers through
bounded mocked MMIO services. Kernel/resource integration, real concurrency
and hardware admission remain unverified.
