# CPU8 late-hold design

## Parent and delta

The parent performs synchronous CPU8 callbacks at +1 and +6 seconds after the
attributable `cpu8-online-held` completion. It protects CPU8 from HPS and every
public `cpu_down()` caller before notifier dispatch and forbids CPU9 startup
and CPU_OFF.

The child changes only the delayed work state machine:

1. sample 1 at +1 second must execute on CPU8 with CPU8 online and CPU9 offline;
2. sample 2 at +6 seconds repeats the same substantive checks;
3. sample 3 at +10 seconds repeats them again and is the only success terminal.

Sample 1 schedules sample 2 after 5,000 ms. Sample 2 schedules sample 3 after
4,000 ms. Each successful sample increments the exact atomic hit count once.
Any IPI error, wrong callback CPU, missing CPU8, present CPU9, wrong hit count,
or failed delayed-work schedule emits one fault and stops.

## Unique terminal

The only success terminal is:

```text
gemini-a72-hold-v2 result=pass sample=3 cpu=8 cpu8=1 cpu9=0 hits=3
```

It is reachable only after all three synchronous callbacks and checks. At the
parent's measured completion time it should occur near 11.932 seconds, within
the prior retained 9.166--14.010-second console window and about two seconds
before the unchanged watchdog recovery.

## Decisions

| Observation | Decision |
| --- | --- |
| exact sample 1, sample 2, and sample-3 pass state, with no fault/down-veto/panic | bounded CPU8 execution/accounting extends to about ten seconds; design a separate longer stability/thermal gate |
| any v2 fault | reject the run and classify its exact sample/error |
| any down-veto or notifier/panic | reject the implementation or classify the unexpected caller |
| terminal absent from a changed watchdog cycle | inconclusive; improve durable observation without an unchanged retry |
| CPU9 online or CPU_OFF evidence | stop immediately; safety contract violated |

No outcome authorizes CPU9, CPU_OFF, load, OPP/cpufreq, thermal claims,
suspend, or default/upstream enablement.
