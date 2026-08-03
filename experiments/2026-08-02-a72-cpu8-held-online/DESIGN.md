# CPU8 held-online design

## Accepted parent

The exact parent is the one-way CPU8 candidate whose retained marker proves
BUCKB, isolation, SRAM-LDO, PSCI secondary completion, CPU8 accounting, CPU9
absence, and DCM. No parent startup operation may change.

## Down-policy barriers

Two barriers are required under `CONFIG_MTK_A72_ONE_WAY_CPU8`:

1. In HPS, identify the cluster by exact CPU bounds 8 through 9 and clamp its
   target to at least one whenever CPU8 is online. This precedes its descending
   loop and therefore prevents the observed `cpu_down(8)` call.
2. At the public `cpu_down()` entry, reject CPU8 and CPU9 with `-EPERM` before
   `cpu_maps_update_begin()`, `cpu_hotplug_begin()`, profiling wrappers, or
   `CPU_DOWN_PREPARE`. This is the fail-closed boundary for any non-HPS caller.

The existing platform CPU-disable rejection remains as a final unreachable
defense. Neither barrier may alter CPU0 through CPU7.

## Bounded execution proof

After the existing `cpu8-online-held/complete` marker, schedule static delayed
work. It performs two synchronous `smp_call_function_single()` calls to CPU8:

- sample 1 at one second after secondary completion;
- sample 2 five seconds after sample 1.

The callback records only its executing logical CPU and an atomic hit count.
Each sample requires the synchronous call to return zero, callback CPU 8, CPU8
online, CPU9 offline, and the exact expected hit count. It emits one compact
ramoops-visible record. The second valid sample emits the unique terminal:

```text
gemini-a72-hold-v1 result=pass sample=2 cpu=8 cpu8=1 cpu9=0
```

Any mismatch emits one `result=fault` record and does not retry. There is no
synthetic workload, writable interface, CPU affinity change, hotplug request,
or watchdog refresh.

## Timing and recovery

The first sample is expected near two seconds of kernel uptime and the second
near seven seconds, leaving about five seconds before the already-armed fixed
twelve-second hardware reset. The watchdog remains exclusive and unrefreshed.
Known-good recovery must prove a changed boot ID, exact retained marker(s),
CPU8/9 offline, watchdog-class reason, and unchanged boot2.

## Decision table

| Result | Meaning | Next action |
| --- | --- | --- |
| two exact samples and one `result=pass` | CPU8 executed coherent synchronous callbacks and remained accounted online through the bounded hold | design a longer thermal/accounting stability gate; CPU9 still separate |
| early down-veto marker | an unexpected non-HPS caller requested CPU8/9 down, but no notifier ran | classify caller; no unchanged retry |
| `result=fault` | IPI, CPU identity, or online accounting failed | preserve pstore and inspect exact sample; no retry |
| cpuhvfs notifier/panic before terminal | HPS barrier or generic dominance failed | reject implementation |
| startup terminal other than success | parent startup did not reproduce | return to parent-stage analysis |
| restart without exact retained marker | inconclusive | improve observation; do not infer stability |

No result in this experiment authorizes CPU_OFF, CPU9 startup, stress, OPP or
cpufreq changes, thermal claims, suspend, or upstream/default enablement.
