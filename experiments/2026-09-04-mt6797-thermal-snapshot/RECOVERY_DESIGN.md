# Reported-temperature recovery: offline contract

Status: prospective host design and thermal evaluator only. No new device
execution, shutdown, boot or source change is admitted. The consumed attribution
protocol remains closed. The [register audit](REGISTER_CONTRACT.md) found no
verified passive freshness signal, so this design retains unknown sample age.

## Hypothesis and evidence

The observed bank 0/sensor 0 rise may be transient in the reported measurement.
One post-completion time point can distinguish a decrease, unchanged value or
continued increase after the finite owned workload has ended. This does not
prove physical cooling, identify sensor location or discriminate hardware
filter history from actual temperature. Slot 0 is the preselected focus because
the published attribution run identified it; retain all seven slots and never
select a winner after seeing the new result.

Reuse exact deployed candidate `666961b636b21b8598a64999e9dbf72af280ad99f07a6b745045320f24ca361b`,
kernel `7.1.3-gemini-thermal-snapshot`, and the exact existing A41 record. A new
host protocol must bind a clean shutdown receipt from the consumed attribution
boot `056703de-bf29-4956-891e-ff69d19fdd68` and require a new boot ID, exact
identity, pristine full lifecycle and zero observer accounting before admission.
No rebuild or partition write is needed for this design.

## Fixed observation and work budget

Keep one CPU admission, one CPU9 down/restore, four rounds per writer/peer
reader, the original 1914704-byte payload and checksum, and spin limit 1000000.
Keep the three frequency reads at the inherited before/writers-waiting/after
boundaries. The writers-waiting liveness gate remains mandatory even though
there is no thermal snapshot at that boundary in this protocol.

Use exactly three snapshot requests on an admitted complete run:

1. Post-lifecycle and before starting owned workers (`pre-workload`).
2. After all four owned workers have completed (`workers-complete`).
3. After cleanup and a single two-second sleep (`post-completion`).

The third snapshot start must be 2,000,000,000 through 3,000,000,000 ns after the
second snapshot end. Two seconds provides a separate post-work interval rather
than another adjacent request; the upper bound allows one second for shell and
observation overhead. These are experimental timing choices, not hardware
conversion, settling or thermal time constants. No spin, new worker, hash or
load is allowed during that interval. It is not a whole-system idle claim:
background kernel and initramfs activity continues. No CPU idle-state control
is added. The sleep does not extend an owned workload.

Keep the two ordinary zone reads for initial admission and final accounting.
The final state must retain exact terminal lifecycle, CPU0--9 online, three
frequency attempts, three snapshot attempts, same boot/record, read-only sysfs,
all 16 hashes, independent bounded CPU8/CPU9 ticks, absent temporary files and
all owned workers reaped. Fewer requests are permitted only on a permanently
retained refusal, never by retry or replacement. No diagnostic request can be
added to recover incomplete evidence.

## Stop and classification rules

Initial aggregate and every slot must be within 0--58500 mC with the existing
100 mC representation. Invalid/incomplete snapshots, temperature outside that
absolute bound, identity changes, structural workload failures or accounting
mismatches stop without additional observation. Preserve cleanup guarantees and
record a refusal. These are refusal criteria, not thermal protection.

The two boundaries shared with the original baseline retain rise targets
700 and 900 mC, tolerance 5000 mC, and spread limit 5000 mC. A numerical
comparison failure within the absolute bound may retain the one predeclared
post-completion observation after successful worker completion and cleanup.
It stays a comparison rejection regardless of recovery. This is the same
separation between complete comparison rejection and malformed/unsafe execution
used by attribution postflight; it is not a raised threshold.

There is no writers-waiting temperature sample in this protocol. Do not invent
one, compare recovery to the old during sample, or claim the full baseline
comparison passed. Report the two shared-boundary comparisons separately and
always preserve the historical rejection. The recovery sample receives the
absolute bound and timing checks, not an invented baseline rise target.

For each slot, report complete-minus-pre and recovery-minus-complete values.
A negative/zero/positive recovery delta is called decreased/unchanged/increased
at the recorded precision; one step is not statistical significance. Even a
large decrease establishes only a transient in reported temperature. The
result never claims hardware freshness, cooling, protection or integrated
repeatability.

## Offline implementation and remaining admission work

The [thermal assessor](scripts/assess-recovery-thermal.py) pins the existing
strict snapshot parser, validates timing and converted values, preserves
comparison rejection and emits per-slot response without an overall workload
pass. It has no transport or device action. Its
[fixtures](scripts/test-recovery-thermal.py) cover all three responses, timing
edges, falling-maximum/rising-slot attribution, nonpromotion of within-bounds
results and 18 malformed, incomplete, reordered, over-budget or out-of-bound
inputs. See the [offline result](results/recovery-thermal-offline.txt).

This evaluator cannot prove stage placement, worker quiescence, source/candidate
identity or the device action budget. Before execution, implement the complete
source-pinned builder and classifier, exclusive durable one-shot capture,
shutdown/cycle receipt and pristine/postflight gates. Test those predicates
against the actual generated program, including signals, timeout and refusal
paths. Validate with the exact candidate BusyBox before publishing an admission
revision. A host exit code zero from this assessor means only that its two
shared-boundary comparisons are within bounds, never device admission.

Broader hotplug, cpufreq/OPP, conversion triggers, filter changes, interrupt
reads, longer stress, idle/suspend and default integration remain closed.
The [roadmap](../../docs/ROADMAP.md) owns implementation order.
