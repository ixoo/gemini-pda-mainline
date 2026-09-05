# Private HIF START execution

This delta connects the existing frozen INIT START transaction helpers to the
actual private kernel HIF core. It separates finite START submission from one
attributable WCIR readiness observation and retains one absolute deadline. No
runtime caller, probe, firmware loader or owner acquisition is supplied.

## Reuse and boundary

The existing `hif_init_transaction.h` already implements START validation, the
independent TC0 debit, shared CONFIG/START sequence history, submitted-state and
WCIR ready-bit transitions. Its `hif_start_transaction_test.c` already tests
those pure transitions. The private core already supplies ordered scalar MMIO,
PIO, a retained transaction, mutex and heap scratch. This change reuses those
implementations unchanged instead of adding a second encoder or state machine.
[inputs.json](inputs.json) pins the seven frozen headers, previous core inputs,
new source and unchanged regression fixtures.

The caller must prove complete whole-image execution, required EMI sealing and
actual retained resource ownership before START. The current whole-image plan
still refuses unresolved mixed-image execution; this internal primitive does
not replace that gate or accept a Boolean permission shortcut. The future owner
must retain resources before calling because even a failing write can already
have started firmware. Its binding and executor remain separate unfinished work.

## Operations and lifetime

`mt6797_hif_start_submit(hif, command, bytes, sequence, deadline_ns)` holds the
same context mutex and uses `mt6797_start_begin`, the existing PIO transfer and
`mt6797_start_submitted`. The caller supplies immutable command bytes and the
helper validates exactly 16. The core copies them into its existing heap scratch
and emits five ordered scalar writes: one setup word and four data words. It
reads no ACK and never reports firmware readiness merely because TX returned.

The one-attempt latch is set after successful nonwaiting lock acquisition,
before validation/debit or I/O. Invalid commands, invalid phase, exhausted
credits, expired deadlines and uncertain effects all poison that attempt. A
busy lock returns EBUSY without consuming an attempt. There is no retry/reset
entry point or TC0 refund; CONFIG TC4 is unchanged. Even a new sequence after
successful readiness cannot submit another START on the context. Ordinary INIT
downloads are also closed after any START attempt.

The absolute monotonic deadline must initially have positive remaining time of
at most one second, matching the existing development ceiling. It is latched
for START and cannot be extended by readiness observation or generic register
reads while readiness is pending. Readiness success ends that pending state;
it does not reset the START attempt or sequence history.

`mt6797_hif_start_observe_ready(hif, wcir)` performs one real WCIR command/data
read under the same latched deadline. It returns zero for the observed ready
level (bit 21), EAGAIN for pending, and a terminal error for deadline/I/O/state
failure. Pending calls may repeat only inside the original deadline; there is
no internal polling or sleep. The level does not prove START caused a transition.
A failed terminal observation clears its output. A second observation after
accepted readiness is refused; the successful result is the caller's evidence.

The caller retains the powered mapping, admitted transaction, driver ownership,
IRQ quiescence and reset exclusion for both operations and serializes lifetime.
Input/output buffers, context and transaction storage must remain distinct;
commands stay immutable through return. An owner-loss path must abort the
retained transaction under the same exclusion. Freeing the context releases
memory only, never owner resources. No software timeout can interrupt a stuck
MMIO accessor, and ordered kernel accessors do not return the injected host bus
errors used below. These are unchanged limitations of the private core.

## Offline validation

Run `python3 experiments/2026-09-05-mt6797-hif-start-core/scripts/verify.py`
from the repository root. It generates and exactly replays
[one logical patch](0004-wifi-mediatek-execute-bounded-start.patch), compiles the
actual new hif.c with the existing scalar/clock host substitutions, reruns all
old HIF fixtures and runs the new START cases. It does not compile a Linux kernel
or access a backend/device. [validation.json](validation.json) records identities,
flags and complete unfiltered strict checkpatch output.

The existing register and 662-position ordinary-section failure suites still
pass. New cases verify all five literal START writes, all five write failures,
both WCIR scalar read-path failures, nine scalar deadline boundaries and two
additional expiry points after completed scalar transfer but before success
publication. Failure stops immediately with no retry, no ACK read and no refund.
Tests also cover pending versus ready, unchanged deadline across calls, deadline
extension refusal, owner abort, malformed command/sequence/phase, busy context,
TC0 exhaustion, TC4-independent START, repeated START with a new sequence, and
actual CONFIG/ACK/PDA followed by START using one retained transaction. Strict
C11 plus AddressSanitizer/UndefinedBehaviorSanitizer passed without diagnostics.

Strict checkpatch has no source findings. The missing DCO error remains for the
synthetic non-certifying experiment author; no sign-off is invented. This patch
is not ready for upstream submission. Host fault propagation does not establish
real bus recovery, firmware execution or readiness on hardware.

## Future kernel integration

[proposal.json](proposal.json) names the exact two-file kernel delta, series
position and two new emitted functions. Append after the complete-plan patch;
the existing profile/config already selects hif.o, so no configuration change is
needed. The coordinator alone changes canonical series/manifest, audits all
shared-series consumers and serializes the managed source refresh. No duplicate
kernel checkout is needed and no build is selected by this proposal.

An admitted explicit Buildbox build must preserve the existing HIF/parser/CRC/
plan acceptance and additionally prove new source hashes, kernel .cmd compilation,
AArch64 nonzero definitions for both START APIs in hif.o, private archive
membership and matching linked vmlinux/System.map definitions. Review actual
ordered START PIO and WCIR accesses in disassembly. Do not expect hif.o to retain
its earlier checksum; unchanged parser/CRC/plan inputs remain separately pinned.
Scope no-initcall/no-export/no-registration checks to these private objects.
Compilation would establish linkage only. Runtime use remains blocked on the
actual owner and complete whole-image executor; no device boot is requested.
