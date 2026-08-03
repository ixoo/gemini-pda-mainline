# CPU9 self-contained terminal attribution design

## Parent evidence

The exact retention-window parent reached its unique sample-3 terminal at
10.885355 seconds with CPUs 8 and 9 online and three synchronous callback hits
on each. The retained 64 KiB console began at 8.847920 seconds and therefore
lost the earlier one-shot HPS record. Recovery and the boot2 identity passed;
the strict overall gate remained inconclusive.

## Child hypothesis

The HPS path can publish the first matching CPU/error and count every matching
CPU8/CPU9 `-EPERM` without changing the call or return path. The existing third
pair callback can then snapshot those atomics into one unique terminal. This
makes the decision durable under the observed pstore truncation.

## Exact changes

1. In the existing HPS CPU8/CPU9 `-EPERM` branch, increment one matching-request
   counter for every rejected request.
2. Replace the binary one-shot flag publication with three states: `0` means
   unclaimed, `-1` means the first CPU/error is being published, and `1` means
   the fields are complete. The winning caller stores the exact CPU and error,
   executes a write barrier, publishes state `1`, and emits the inherited
   one-shot text record. Later calls remain silent.
3. Add one read-only snapshot function. It returns publication state, first CPU,
   first error, and total matching count from atomics; it performs no hardware,
   policy, hotplug, or logging action.
4. At the existing sample-3 success site only, call the snapshot and replace
   the terminal with unique `pair-v3` text containing all four HPS fields.
   Earlier sample/fault markers remain `pair-v2`, and all timing is unchanged.

## Pass predicate

One changed watchdog cycle must retain exactly one terminal matching:

```text
gemini-a72-pair-v3 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=1 hps_cpu=9 hps_error=-1 hps_count=N
```

`N` must be a positive integer. The terminal must be accompanied by no pair-v2
fault, CPU9/parent startup fault, generic down-veto marker, panic, Internal
error, or Call trace. A changed-cycle watchdog return, exact recovery kernel,
offline CPU8/9, and unchanged boot2 checksum remain required. Earlier one-shot
text is optional because the terminal is the durable oracle.

## Rejected result classes

- `hps_reported=0`: no matching HPS request occurred before sample 3.
- `hps_reported=-1`: snapshot raced incomplete publication.
- first CPU other than 9, error other than `-EPERM`, or count below one: HPS
  attribution contract failed.
- pair fault, startup fault, panic, Internal error, Call trace, failed recovery,
  or changed boot2: reject and do not repeat unchanged.
- missing unique terminal: inconclusive; improve attribution with a changed
  artifact and do not repeat unchanged.

## Static and binary invariants

- `mt6797_a72_cpu9_boot`, generic secondary completion, and `cpu_down` source
  remain byte-identical to the exact parent.
- The initial one-second delay and both two-second delays remain exact.
- Only `arch/arm64/kernel/psci.c` and the MT6797 HPS algorithm file may change.
- The HPS caller still invokes `cpu_down(cpu)` exactly once per selected action
  and never changes `hotplug_ret`.
- The snapshot contains only atomic reads and a read barrier.
- Mutation checks reject relaxed veto assumptions, altered delays, unbounded
  one-shot logging, non-atomic count/state, missing publication barriers, and a
  terminal that omits any HPS field.

## Safety boundary

The child does not enable CPU_OFF, initiate hotplug, add load, alter startup,
touch a regulator or power register, change the watchdog, or expose a control
surface. Every CPU8/CPU9 down request still returns `-EPERM` at public entry.
All A72 CPUs remain retained until fixed watchdog recovery. A pass earns only
one exact repeatability run; coherency/load, CPU_OFF, DVFS/OPP, thermal,
suspend, default enablement, and an upstream support claim remain closed.
