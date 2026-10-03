# Bounded full-STP IRQ draft

The [kernel-style draft](tests/mt6797-wmt-full-io.h) composes the codec,
[exchange state](FULL_STP_STATE.md), [collector](FULL_STP_STREAM.md) and
[TX accounting](FULL_STP_TX.md). The [fixture](tests/wmt-full-io-test.c) invokes
that actual draft with mocked MMIO, time, IRQ masking and locking.
There is no kernel caller, profile change, build package or hardware admission.

## Ownership and setup boundary

Storage belongs to the CONSYS owner and is persistent, initially zeroed and
never stack allocated. The link is initialized only at the reviewed full-mode
boundary and persists across ordinary WMT resets. Preparation encodes the
command and validates argument bounds without MMIO. Command input and expected
event bytes must live outside the context being cleared; expected bytes remain
immutable until retirement. Failed or unfinished contexts refuse preparation.
After successful retirement, seal the command evidence and synchronize the IRQ
before preparing the next command; preparation clears the previous context.

The future caller must establish exact full-mode negotiation, retained clocks,
normal register bank, DMA exclusion and exclusive registered IRQ ownership.
It must check empty entry RX, configure the selected source enables and perform
the initial locked service with CPU IRQ disabled, then enable CPU delivery only
for a nonterminal context. IRQ enable/disable/free sequencing, initial-kick
failure cleanup and resource lifetime remain integration work. The draft does
not acquire clocks, request/free IRQs or select/reset transport mode. Never call
it against arbitrary register mappings or use it as a standalone device test.

## Finite progress

A service reads at most eight RX bytes, rechecking IIR and time, and preserves
those bytes in bounded private context storage. It then gives TX an opportunity
using fresh LSR and the tested one-batch accounting. Received bytes are parsed
only after the complete command has been submitted. Parsing itself is bounded
by stored bytes and frame count. Exact event/peer ACK acceptance creates the
host ACK span; its completed submission is required before success.

The draft bounds one command to 512 services including the initial kick,
1043 RBR reads, eight complete received frames and at most 1015 THR writes
(1011-byte command plus four-byte host ACK). Each TX span also has its 256
room-observation cap. These are offline proposed limits, not measured timing
or an admitted whole-initialization budget. Real deadlines are supplied by the
caller; the draft checks before service, RX reads, TX writes, parsing and the
final completion decision. Partial TX records actual writes and retires.

Initial pending RX, spurious IRQ causes, bad/extra data, overflow and exhausted
budgets retire without retry. Once both exact event and peer credit are known,
queued or partial further input is refused before issuing host ACK writes.
Late peer ACK is supported while waiting for credit. Timeout retirement must
hold the same lock as IRQ progress. Retirement masks the local source, disables
CPU IRQ delivery once and signals completion; clocks/power and private bytes
remain for evidence and reviewed recovery. No speculative FIFO clear, wake,
DMA request or calibration operation occurs inside this draft.

## Focused validation and limitations

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-10-03-mt6797-wifi-audit/tests/run-wmt-full-io-test.py
```

The runner supplies temporary stub kernel headers and removes the compiled
binary. Strict warnings and address/undefined behavior sanitizers pass. The
fixture models a 16-byte FIFO draining eight bytes between services and verifies
maximum-command bytes, late ACK, host ACK completion, RX quota under continuous
input, total-RX overflow, partial TX on expiry, failed-context reuse refusal,
expiry at final completion, queued extra input, wrong IRQ identity, initial RX
refusal, aggregate service limit and no writes after retirement.

The fixtures do not model real spinlocks, IRQ races, posted MMIO, system-time
behavior or a physical FIFO. Their FIFO/status model follows the pinned source;
it cannot settle the contrary register-table assignments. No Linux kernel
compile, device exchange, ROM patch applicability, calibration or RF reception
is established. Review kernel integration, setup/cleanup and complete command
budgets after [first-query liveness](../2026-10-03-mt6797-wmt-default-query/SESSION.md),
then use the required clean pushed Buildbox workflow before any candidate.
The [receipt](results/full-stp-io.json) pins all authored inputs.
