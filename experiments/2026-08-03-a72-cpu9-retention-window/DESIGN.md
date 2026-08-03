# CPU9 retention-window design

## Accepted parent and observed boundary

The exact parent is the rejected CPU9 cluster-reuse artifact. Its result is not
reclassified: retained pstore proves CPU8 and CPU9 online with two synchronous
callback rounds, while 83 HPS CPU9-down requests and the missing out-of-window
third terminal reject its declared predicate.

The first request is now directly attributable to HPS because every inherited
`cpu_down(9)` veto was immediately paired with HPS `CPU 9 --!`. Repetition is
HPS policy pressure under low load, not evidence that CPU_OFF ran.

## Child hypothesis

Without changing CPU9 startup, power state, or the public CPU-down prohibition,
can CPU8 and CPU9 complete three synchronous pair rounds before the inherited
watchdog recovery while one bounded HPS-attributed record proves the veto was
exercised?

## Exact changes

1. Keep the initial pair sample one second after CPU9 completion.
2. Replace the following five- and four-second delays with two seconds each.
   The expected samples move from about completion +1/+6/+10 seconds to
   completion +1/+3/+5 seconds.
3. Keep every public `cpu_down(8)` and `cpu_down(9)` return at `-EPERM`, before
   maps, notifiers, or platform callbacks.
4. Suppress the inherited generic per-request console marker only for the CPU9
   profile. At the already-observed HPS caller, atomically emit one exact
   `hps-down-held-first` record for the first `-EPERM`; suppress later identical
   HPS warnings. Calls and vetoes continue unchanged.
5. Version pair markers from `gemini-a72-pair-v1` to `v2` so this candidate is
   uniquely attributable.

## Pass predicate

All of these must be retained in one changed boot cycle:

```text
gemini-a72-retain-v1 result=hps-down-held-first cpu=9 error=-1
gemini-a72-pair-v2 result=sample sample=1 cpu8=8 cpu9=9 online8=1 online9=1 hits8=1 hits9=1
gemini-a72-pair-v2 result=sample sample=2 cpu8=8 cpu9=9 online8=1 online9=1 hits8=2 hits9=2
gemini-a72-pair-v2 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3
```

There must be exactly one `hps-down-held-first` record and no pair fault,
CPU9 startup fault, parent startup fault, panic, Internal error, or Call trace.
The HPS record is expected policy pressure and proves the fail-closed barrier
dominated. A request for CPU8, an error other than `-EPERM`, or more than one
record rejects the implementation.

## Safety boundary

The child does not enable CPU_OFF, modify the watchdog, replay cluster power,
touch DA921x, alter voltage/frequency, add load, or expose a control surface.
All post-PSCI failures retain both A72 CPUs until the fixed watchdog recovery.
No result authorizes stress, CPU_OFF, cpufreq/OPP, thermal, suspend, default
profile enablement, or an upstream support claim.
