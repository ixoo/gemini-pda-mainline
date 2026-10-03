# Bounded full-STP IRQ draft

The [kernel-style draft](tests/mt6797-wmt-full-io.h) composes the codec,
[exchange state](FULL_STP_STATE.md), [collector](FULL_STP_STREAM.md) and
[TX accounting](FULL_STP_TX.md). The [fixture](tests/wmt-full-io-test.c) invokes
that actual draft with mocked MMIO, time, IRQ masking and locking.
A process-context exchange wrapper is now included in the host-tested draft.
There is no integrated kernel caller, profile change, build package or hardware admission.

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
normal register bank, DMA exclusion and exclusive IRQ availability.
The wrapper requests the exclusive IRQ with `IRQF_NO_AUTOEN`, enables the local
RX/TX sources and performs the first bounded locked service while CPU delivery
remains disabled. Initial failure masks the local source without adding another
CPU disable depth. A nonterminal kick marks the IRQ armed before enabling CPU
delivery; no other start/timeout caller may run concurrently. Handler retirement
adds one CPU disable only while armed. The process samples jiffies once for the
remaining wait, retires a missing completion under the same lock, then joins the
handler with `synchronize_irq()` before freeing its registration. Every completed
registration is freed once; request failure performs no transport MMIO.

This addresses a concrete composition gap: the earlier service draft disabled
CPU delivery unconditionally, including failure before the initial enable. The
old fixture counted disable calls but did not model nested depth. That contract
could not be used safely as a reusable command wrapper without explicit depth
ownership. The new fixtures retain depth one on initial failure and after normal
retirement; an unconditional-disable mutation fails their terminal depth check.
The wrapper retains transport clocks, power, link state and evidence. It does
not select/reset transport mode or supply the resource prerequisites above.

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
CPU IRQ delivery once when armed and signals completion; clocks/power and private bytes
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
refusal, aggregate service limit and no writes after retirement. Wrapper checks cover
matched success, wait expiry, initial partial-TX expiry, pending entry RX, IRQ
request failure, a callback retiring during enable and repeated-call refusal.
Each acquired registration is synchronized and freed exactly once. Tests model
nested IRQ depth; an unconditional initial-disable mutation is rejected.

The fixtures do not model real spinlocks, IRQ races, posted MMIO, system-time
behavior or a physical FIFO. Their FIFO/status model follows the pinned source;
it cannot settle the contrary register-table assignments. No Linux kernel
compile, device exchange, ROM patch applicability, calibration or RF reception
is established. Review actual kernel compilation, resource setup and complete command
budgets after [first-query liveness](../2026-10-03-mt6797-wmt-default-query/SESSION.md),
then use the required clean pushed Buildbox workflow before any candidate.
The [receipt](results/full-stp-io.json) pins all authored inputs.

The [lifecycle receipt](results/full-stp-irq-lifecycle.json) pins the revised
draft and fixture; the earlier receipt remains historical.

## Mandatory set-options integration checkpoint

After the [successful default query](../2026-10-03-mt6797-wmt-default-query/results/runtime-2.json),
the same authored IRQ/FIFO draft now prepares one fixed mandatory set-options
request using separate persistent context storage. It reuses TX byte accounting
but does not pass mandatory bytes through the full-frame CRC/checksum validator.
The strict [set reply parser](tests/wmt-stp-options.h) handles the distinct
12-byte frame; no full-STP peer sequence or host ACK is applied to that event.

The set path requires initially empty RX/TX in the normal bank and checks that
TX observation in the initial service. It admits at most 32 services including
the kick, 13 RBR reads and 15 THR writes, with eight RX reads per service and the
caller-supplied deadline checked before every effect/parsing step and successful
retirement. Malformed/extra data, exhaustion or expiry retires without retry.
The caller must prove the completed default query, retained clocks and DMA
exclusion; this preparation helper does not establish those prerequisites.

The actual service/wrapper fixtures pass the matched response, malformed status,
extra input, exact receive exhaustion, initial nonempty FIFO, request failure,
partial TX, missing reply, final-observation expiry and repeated-call refusal.
IRQ depth, synchronization and registration cleanup remain balanced. A separate
full-mode query uses the existing event/credit/host-ACK path in the same fixture.
All earlier full-STP fixtures still pass under strict warnings and address/undefined
sanitizers; the changed header passes strict kernel style. The
[receipt](results/mandatory-set-io.json) pins these final bytes. Earlier receipts
remain historical and no longer identify the current draft.

This remains an incomplete integration checkpoint. Next connect fresh resource
setup, checked initial query, this set exchange, source-matched full-mode reseed
and 10-ms wait, and the full-query wrapper under one CONSYS owner with an explicit
whole-negotiation budget and preserved phase evidence. No new candidate, kernel
build, mode-switch device test or common-initialization effect is admitted here.
