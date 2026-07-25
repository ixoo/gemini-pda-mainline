# Experiment: Gemian A72 load-assisted observation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-23-gemian-a72-load-assisted-observation` |
| Status | `completed` |
| Subsystem | MT6797 HPS/PPM and Cortex-A72 transition observation |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-23 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Will short, bounded userspace CPU-load pulses make the unmodified Gemian
`3.18.41+` HPS/PPM policy bring CPU8 or CPU9 online without any CPU-online,
HPS, PPM, frequency, voltage, register, firmware, or partition write?

This is a trigger-calibration experiment. Even a positive result cannot
authorize Candidate AM, the first active mainline CPU8 experiment, because
sequential userspace reads cannot capture the owner-locked regulator,
isolation, secure-register, clock, PSCI, secondary, and DCM transaction.
Candidate AL is instead the separate mainline I2C6/DA9214 resource-only
predecessor and requests neither A72.

## Provenance and environment

- Running OS: exact known-good Gemian `3.18.41+ #7`, AArch64, built
  2019-03-29 with GCC 6.3.0-18. The active boot image and Android kernel field
  have SHA-256
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`
  and
  `b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`.
- Public source: initial policy decoding used
  `gemian/gemini-linux-kernel-3.18` commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`. Later reconciliation showed
  that the active March 29 image is not the May 24 `gbp59e00a` installed
  package. The exact active public commit remains unresolved; `59e00a` is the
  chosen equivalent for verified observer-hook blobs, not exact active
  provenance.
- The live HPS configuration reports 40 ms periods, 95%/three-sample CPU-up
  policy, 98%/one-sample rush boost, and heavy-task handling enabled. The load
  probe requires the previously recorded fixed HPS values both before and
  after its pulses and again before every stage; printing them is not treated
  as validation. It also requires the known zero HPS service, thermal, battery,
  power-service, and ultra-power-saving core-limit inputs.
- The companion read-only observer is the already audited v2 collector in
  [`../2026-07-22-gemian-a72-readonly-discovery/`](../2026-07-22-gemian-a72-readonly-discovery/).
- Both live GPT-resolved TEE slots match the exact privately analyzed payload;
  see
  [`../2026-07-22-a72-firmware-power-contract/results/live-tee-identity-20260723.txt`](../2026-07-22-a72-firmware-power-contract/results/live-tee-identity-20260723.txt).

## Safety assessment

The owner explicitly authorized synthetic CPU load and further binary reverse
engineering. The load changes scheduler demand only. It performs no explicit
userspace control or value write to a CPU-online, HPS, PPM, cpufreq, voltage,
thermal, register, raw-memory, I2C, SMC, firmware, filesystem, partition,
watchdog, or reboot interface. Successful vendor HPS action is expected to
change CPU, clock, voltage, and firmware-owned state indirectly. The companion
partial observer also performs its already documented driver-serialized
DA9214 I2C register-address phase plus read; that is not a value write, but it
is not a zero-effect observation.

The remote process verifies the expected kernel release, architecture, root,
topology, passwordless sudo, USB power, and a Full/100%/Good battery before
starting. It
first requires CPU8 and CPU9 to remain offline through a five-sample baseline,
then requires two stable-off CPU8/CPU9 read brackets immediately before every
stage. It uses 1, 2, 4, 8, then 10 `yes >/dev/null` workers. Each worker has its
own three-second TERM deadline and one-second KILL grace. Worker launches are
slightly staggered, so the
capture records the requested population and the live population both before
and after every sample instead of claiming an exact simultaneous three-second
stage. It accepts a full-`N` association only when all `N` workers bracket the
observation; partial or expired populations receive distinct attribution. The
script kills and reaps every recorded worker after each stage.
Detection during a pulse removes load immediately after that sample; detection
between stages stops the next stage and is labelled as a delayed observation.
Pre-existing A72 activity causes all synthetic load to be skipped.

Because the live thermal zones report `mode=disabled`, the experiment does not
rely on vendor trip enforcement. It independently aborts and removes load at:

- CPU or AP temperature at or above 50 C;
- PMIC temperature at or above 60 C;
- DA9214 temperature at or above 80 C;
- any USB-power, battery-status, capacity, or health drift;
- a read failure, SSH failure, signal, or host deadline. The remote load script
  has an independent 55-second plus 1-second hard deadline. The host bounds
  both exact SSH children and gives them a termination grace so remote traps
  can run before a forced kill. Spawn-time signals are deferred until each
  exact child PID has been recorded; every load worker also retains its
  independent deadline as the final race backstop.

After an A72 observation, or after the final stage, it retains a 15-second
no-load cooldown to observe the return mask and temperatures. No device reboot
or partition access is part of this experiment.

The host does not use a fixed sleep to assume observer overlap. It waits until
the companion observer has completed natural sample 1 before launching load,
then requires the observer's first and last sampled uptimes to bracket the
load probe's complete baseline-through-cooldown uptime interval. The observer
SSH child has a 105-second host deadline; the load child has a 65-second host
deadline. If A72 activity is observed, it also requires a companion observer
sample timestamp within 1.5 seconds of that observation. All three executed
collector inputs are pinned by SHA-256.

## Associated code

- [`scripts/remote-load-probe.sh`](scripts/remote-load-probe.sh): fixed-policy
  POSIX remote load and 200 ms mask/temperature/power sampler.
- [`scripts/bounded-exec.pl`](scripts/bounded-exec.pl): monotonic host bound
  with signal handling and exact-child terminate/wait/kill cleanup.
- [`scripts/collect.sh`](scripts/collect.sh): exact-target host orchestrator. It
  starts the pre-existing read-only partial observer, then the bounded load
  probe, and stores both captures privately below `artifacts/runtime-captures/`.
- [`scripts/test-static.py`](scripts/test-static.py): syntax, fixed-policy,
  forbidden-interface, checksum-pin, synchronization, and host-bound checks,
  plus dynamic exact-child timeout and signal-cleanup tests.

Run from the repository root:

```sh
experiments/2026-07-23-gemian-a72-load-assisted-observation/scripts/collect.sh \
  --tag attempt-1-20260723
```

## Procedure

1. Run the static test and shell syntax checks.
2. Confirm the named unit is in known-good Gemian on stable USB power.
3. Run the host collector once with a new tag.
4. Preserve both mode-0600 Git-ignored captures.
5. Summarize only sanitized masks, temperatures, stage timing, partial
   DA9214/B/CCI correlation, and filtered HPS/A72 messages.
6. Treat a positive A72 mask only as trigger calibration. Use the calibrated
   load later with a separately reviewed owner-synchronized in-kernel observer.

## Observations

Attempt 1 passed every identity, policy, power, temperature, cleanup,
same-boot, and observer-span gate. One worker did not expose an A72 CPU. With
two workers, CPU8 was stably online in both direct reads 1.11 seconds after the
stage began while both workers were alive before and after the sample. CPU9
remained offline. The immediately following no-load sample bracketed CPU8
changing from online to offline.

The load sampler recorded 107 samples. CPU temperature peaked at 35.3 C, AP at
28 C, PMIC at 27.03 C, and DA9214 remained at 60 C, all below the independent
abort limits. USB power and Full/100%/Good battery state were stable. The
15-second nominal cooldown produced 75 samples, the boot ID remained stable,
and a post-capture check found CPU8 and CPU9 offline with no `yes` process.

The companion observer completed 70 samples on the same boot. Its closest
sample ended about 0.19 seconds before the direct CPU8 observation and reported
DA9214 selector `0xd9` value `0x46`, cached B frequency 845 MHz, and an
unprotected derived CCI frequency of 988 MHz. It did not itself catch CPU8
online. Across all 70 samples, DA9214 `0xd9` remained `0x46`, cached B frequency
remained 845 MHz, and CCI varied from 325 MHz to 988 MHz. Filtered HPS logs show
policy action around the direct CPU8 event, but their local counts are not
completion proof.

The sanitized result is
[`results/live-attempt-1-20260723.txt`](results/live-attempt-1-20260723.txt).
Both complete private captures remain mode 0600 and Git-ignored.

## Analysis

`active-full-load-2` is a valid temporal association: all two requested workers
bracketed the direct CPU8 sample. It is not proof that two workers are the
causal or minimum threshold, because worker start times and deadlines are
slightly staggered and HPS acts asynchronously. It is nevertheless a precise,
low-cost trigger for a later instrumented run. CPU9 must remain excluded.

The sequential observer again missed the short A72 interval. Its near-event
DA9214/B/CCI values are useful correlation, but they do not reveal DA9214 page
and enable state, SPM/TOPRGU ordering, the protected clock tuple, raw PSCI
result, secondary completion, MP2 DCM, or the last-A72 offline transaction.

## Conclusion

`passed` for calibrating a bounded Gemian trigger: two workers produced one
directly observed CPU8 online/offline cycle with no safety-gate failure.
`rejected` as sufficient evidence for Candidate AM. The result changes the next
active-CPU action from trigger discovery to an owner-local in-kernel observer
capture. It neither proves nor rejects Candidate AL's resource-only I2C6 and
DA9214 path.

## Follow-up

Build an unlabeled Gemian observation image from the chosen `59e00a` public
equivalent with fixed-register, bounded hooks at the DA9214 owner, SPM/TOPRGU
paths, protected B/CCI clock owner, raw and mapped PSCI return sites, secondary
completion, MP2 DCM, and last-A72 offline path. Derive its configuration from
the exact active configuration and record only the observer delta; retain the
exact active ramdisk, appended DTB, and Android-v0 container contract. Then use
only the calibrated two-worker pulse and retain the same fail-stop gates. Do
not select draft patch 0093 or activate Candidate AM until that
transaction-local record is reviewed. Candidate AL remains the independent
resource-only predecessor.
