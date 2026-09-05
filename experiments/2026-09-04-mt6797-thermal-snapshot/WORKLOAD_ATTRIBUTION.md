# Prospective bounded workload thermal attribution

This design and its offline thermal evaluator do not authorize execution.
The first [no-workload observer gate](results/no-workload-runtime-pass.txt)
passed; that boot's three-read budget is consumed. A complete source-pinned
builder, whole-runtime classifier, host runner, failure-cleanup tests and fresh
power-cycle receipt remain required before a boot is selected.

## Hypothesis and decision

The already-built exact candidate can attribute each aggregate temperature to
its converted bank/sensor slots around the inherited finite lifecycle/workload
sequence. Candidate, release and provenance remain those frozen in
[NO_WORKLOAD.md](NO_WORKLOAD.md). No source/configuration change or rebuild is
currently justified: the three-read observer budget suffices for the three
existing observation boundaries.

The independent evidence is the complete per-slot trajectory, tied maxima,
first winning slot and callback timing at each boundary. A rise in the same
slot, movement of the winning slot, invalid/missing evidence and no reproduced
rise are distinguishable outcomes. None independently proves a defect,
conversion freshness, calibration accuracy or a physical cause. Repeated
sensor IDs across banks must not be counted as independent physical sensors.

The old aggregate-only comparison remains rejected. This is an attribution
experiment with a changed observation path, not another assertion that the
old candidate's thermal repeatability passes. A passing thermal envelope is
only one necessary term of a complete runtime classification.

## Exact measurement boundaries

Preserve the source-pinned production builder's three existing frequency
observations and replace each adjacent ordinary aggregate temperature read
with one bounded snapshot read from the existing scan. Derive the printed
aggregate from that very record; do not add a second ordinary temperature read
for agreement. Retain all seven raw converted rows and timing fields.

| Record | Explicit stage | Existing program boundary |
| --- | --- | --- |
| 1 | post-lifecycle | After the completed stage-18 CPU9 down/restore and topology gate, before worker creation |
| 2 | writers-waiting | Both pinned writers alive immediately before and after observation, before publishing their start barrier |
| 3 | workers-complete | After both writers and both peer readers have completed and returned success |

The inherited `during` label means writers waiting at a barrier, not a sample
inside the hashing loops. Preserve the existing scheduling/order boundaries;
do not add a release delay or move record 2 inside the workload. An initial
ordinary aggregate in the pristine frame precedes CPU admission. There is no
per-slot pre-admission baseline: attributing the admission-only change would
require a different allocation of the observation budget and is outside this
three-record design.

## Admission, bounds and classification

Require the exact full-readback deployment identity, a recorded clean shutdown
and fresh boot distinct from deployment, both consumed workload boots and the
no-workload boot. Require full pristine lifecycle and frequency accounting,
CPU8/CPU9 offline, exact provenance/release, read-only sysfs, unique root-only
observer/status and attempts zero before triggering. A saved earlier pristine
frame cannot replace the new frame after publication.

Keep one admission, one CPU9-only down/restore, three frequency observations,
three snapshots, four rounds per writer and peer reader, the same 1914704-byte
payload identity and spin ceiling 1000000. Retain exact affinity, 4+4+2 topology,
positive independent scheduler progress, all 16 hashes, complete lifecycle and
observer accounting, worker exit and RAM-file cleanup. No partition access,
backup, retry, reboot, warming workload or longer stress belongs in the run.

The initial aggregate must remain 0--58500 millicelsius. Every converted slot
must remain 0--58500, retaining the stricter no-workload bound even for the last
record. For the three maxima, preserve the old rise targets 700, 700 and 900
relative to the initial aggregate, with absolute differences at most 5000.
Preserve aggregate spread at most 5000. These are experiment refusal thresholds,
not hardware thermal protection or statistical reliability limits. Do not
silently relax them if per-slot attribution supplies an interesting result.

The [offline evaluator](scripts/assess-workload-thermal.py) rejects malformed
records and initial state. For structurally valid records it retains every
per-slot delta, all tied maxima and callback timing even if a thermal envelope
rejects, returning nonzero for thermal rejection. It deliberately reports the
overall workload classification as not evaluated. It has no transport and
cannot certify identity, stage placement, CPU/RAM results or cleanup; the
future complete classifier must validate all of those independently and bind
the thermal records to the actual transcript boundaries.

## Required implementation review

The existing builder source is
`experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/build-production-runtime.sh`.
Its materialized worker bodies must remain byte-identical except for explicitly
reviewed failure cleanup. The snapshot read must require the correct attempt
count before and after; failures must never lead to another observation.
The final runner must seal the one workload request before transport, retain
partial data and refuse reopening its exclusive capture.

An audit of the inherited concurrent shell's `cleanup()` found that it removes
RAM files but does not terminate or reap outstanding worker children. A newly
inserted observation refusal while writers wait cannot claim completed cleanup
on that basis. Before admission, implement and fixture-test cleanup that stops
only owned live children, reaps them and then removes their files; preserve
success-path payload/round/spin limits. Test failure before worker release,
during child execution and after completion, plus transport interruption and
no-retry persistence. Do not hide surviving children behind absent-file checks.

The [evaluator fixtures](scripts/test-workload-thermal.py) currently pass one
positive attribution case, four thermal-refusal cases and twelve malformed or
initial-state refusals. A single-slot 5700-millicelsius waiting-to-completion
rise remains visible while both rise and spread comparisons reject. These
fixtures are synthetic and make no new device observation.

cpufreq/OPP, broader hotplug, idle, suspend, thermal protection and default
integration remain closed. Implementation order and boot selection belong to
the [roadmap](../../docs/ROADMAP.md).


## Cooperative cleanup implementation and host fixtures

The [source-pinned transform](scripts/workload_cleanup.py) now adds cooperative
cancellation and child reaping without editing the consumed predecessor. Each
worker checks one RAM flag while waiting and before starting a new round. A
current foreground RAM operation may finish; the parent waits for every owned
worker before removing its files. This avoids signalling reused numeric PIDs.
Failed cancellation publication still joins finite children, then refuses.
The payload operations, four rounds and spin ceiling remain intact; added
cancellation checks can affect timing and are not a claim of byte-identical
instruction execution or unchanged thermal response.

Caught signals are deferred across each fork/child-handle registration window.
Normal waits clear their handles, and cleanup suppresses recursive caught
signals while joining children. Uncatchable termination and stalled kernel IO
remain outside a guaranteed cleanup result; missing transport evidence cannot
be promoted to successful cleanup.

The [host fixtures](scripts/test-workload-cleanup.py) and
[validation record](results/workload-cleanup-validation.txt) exercise actual
worker bodies through injected host adapters, signal cleanup, the registration
race and all four simultaneous handles. Mutations removing cancellation or
waiting reject. This is not yet a complete executable attribution protocol:
the materialized program must be integrated with the observation builder and
validated in the candidate's shell contract before any new device workload.


## Generated program and combined host classifier

The [offline builder](scripts/build-attribution-runtime.py) now integrates the
source-pinned cleanup before applying the inherited production observation
sequence. It binds the new kernel/record identity and refuses known consumed
boots. Its pre-admission checks include the exact pristine lifecycle hash,
unique observer pair, root-only modes and zero snapshot/frequency accounting.
The [observer fragment](scripts/attribution-observer.sh) emits each complete raw
record and derives its aggregate through a strict bounded parser, refusing
malformed or out-of-range values before another stage proceeds. It replaces
ordinary temperature reads rather than adding another scan at each boundary.

The [combined classifier](scripts/classify-attribution-runtime.py) checks raw
record/stage placement, aggregate equality, final accounting and owned-worker
cleanup before delegating the inherited CPU/topology/frequency/RAM predicate to
its hash-pinned classifier. It validates both new release fields before the
explicit normalization needed by that predecessor. Baseline frequencies and
bounded independent CPU progress remain mandatory. Its separate thermal
assessment retains per-slot attribution while rejecting the unchanged rise
and spread limits; the combined result stays nonzero on rejection.

[Program fixtures](scripts/test-attribution-runtime.py) cover generated shell,
the actual observer function with injected files, complete transcript mutations
and classifier exit behavior. See the [validation record](results/attribution-program-validation.txt).
These are host fixtures. The transport runner, fresh-cycle receipt, durable
no-retry state and candidate BusyBox shell validation remain required before
execution. No new boot or workload is admitted by this implementation stage.
