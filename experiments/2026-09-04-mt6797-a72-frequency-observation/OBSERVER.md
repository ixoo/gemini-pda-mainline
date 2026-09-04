# Bounded live-frequency observer

## Purpose

Expose one attributable read-only interface for the already stable MT6797
protected-clock and BigiDVFS transports. The interface exists only in a named
experiment profile and feeds their raw records to the hardware-free decoder
proved by canonical patches `0525` and `0526`.

This closes the measurement boundary needed before the next finite dual-A72
RAM/coherency run. It does not implement cpufreq, choose an OPP, alter a clock,
or make CPU8 or CPU9 available.

## Interface and lifetime

When `CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER=y`, the existing A72 hotplug
snapshot platform device gains one `a72_frequency_observation` read-only sysfs
attribute. The attribute has no write method.

Each successful read returns one line containing:

- the observer ABI, attempt ordinal, hard limit, and remaining attempts;
- the protected-clock and BigiDVFS sample generations;
- raw `ARMPLLDIV_MUXSEL`, `ARMPLLDIV_CKDIV`, BigiDVFS PCW, and BigiDVFS
  enable/post-divider words;
- masked B-cluster PCW, post-divider, mux and divider selections; and
- decoded LL, L, B, and CCI frequencies in kHz.

The same successful line is emitted once to the kernel log so the serial
console is an independent observation path. Failures emit only their attempt
ordinal and errno; no invalid raw value is promoted to evidence.

## Bounded transport contract

The per-device controller permits exactly three attempts per boot. It consumes
an attempt before invoking either transport, so a failing backend cannot be
retried without limit. The fourth and every later read returns `-ENOSPC`
without a transport call.

One admitted attempt has this maximum envelope:

| Operation | Count |
| --- | ---: |
| Protected-clock stable sample | 1 |
| Clock power-on write | 1 |
| Clock semaphore acquire writes | 200 maximum |
| Clock semaphore release writes | 200 maximum |
| BigiDVFS stable samples | 2 identical samples |
| BigiDVFS register reads | 8 |
| BigiDVFS SRAM/voltage writes | 0 |
| CPU/PSCI/hotplug requests | 0 |
| Frequency, OPP, regulator, thermal-policy changes | 0 |
| Retained-memory or storage writes | 0 |

The protected-clock writes are the existing bounded semaphore transport, not a
clock programming operation. There is no polling or sleep in the new observer.

## Hardware-free gate

Before the option may enter a device profile, Buildbox must generate two normal
patches from the hash-pinned source through `0526`:

1. production observer, read-only attribute, and snapshot-adapter registration;
2. injected five-case KUnit suite.

Generation must pass exact replay, changed-path validation, the source oracle,
strict Checkpatch, and package checksums. The admitted focused profile must then
compile on Buildbox and pass only `mt6797-a72-frequency-observer` in no-network
arm64 QEMU. The cases cover the live raw values and 845000 kHz B result, three
successful attempts followed by transport-free refusal, failure budget
consumption, malformed-generation refusal, and null-source guards.

## Eventual device attempt

The observer will be composed with the exact successful stage-18 4+4+2
lifecycle configuration and the runtime-proven thermal DT/configuration. The
single bounded run will take the three frequency samples after lifecycle
success: immediately before, during, and after the already-proven finite
dual-A72 volatile-RAM exchange. Temperature, topology, per-CPU accounting,
hashes, and all three raw/decoded observations must be captured in the same
boot-ID-bound frame.

Success requires all three observation records to decode, CPU8 and CPU9 to
remain online, the thermal zone to remain plausible, exact 4+4+2 topology,
independent CPU8/CPU9 accounting movement, and all finite RAM hashes to match.
A transport or decoder failure selects observation repair without increasing
load. A lifecycle failure selects the existing lifecycle evidence path. A
thermal anomaly stops the run. Longer load, cpufreq/OPP, extra hotplug, idle,
and suspend remain closed.

The first admitted successor boot completed stage 18 with both A72 CPUs online
and independently retained that success, but its first observer read failed
before a sample. The original host failure path omitted the already-generated
kernel failure line, so the exact errno was lost before automatic Gemian
recovery. One identical-candidate repeat is therefore permitted solely with a
new independent observation path: after a failed first read it immediately
emits the existing `attempt=N/3 ret=-ERRNO` line and CPU/lifecycle status, then
proves no second observer request or load occurred. The errno must determine
the next repair, and no further identical-artifact repeat is authorized by this
exception.

The admitted repeat consumed that exception and captured two consecutive
kernel callbacks from one userspace read, both `ret=-71` (`EPROTO`). The frame
proved CPUs 0--9 and terminal stage-18 state, made no additional observer
request, and started no load. Source review leaves three observer-local
`EPROTO` branches: clock-record shape, BigiDVFS-record shape, or decoder
validation. No exact-artifact repeat remains permitted. A new candidate must
first add hardware-free-tested failure-stage attribution without adding a
transport call or increasing the three-callback budget.

Canonical patches `0531`--`0532` now implement that source boundary. Each
failed callback names one of clock transport, clock shape, BigiDVFS transport,
BigiDVFS shape, or decode and emits the already-returned ABI, generation,
reserved, mux/divider, and PLL fields. The success path remains `none`.
Injected KUnit fixtures cover all six states and exact call accounting; patch
replay, source/path validation, and strict style checks pass. This is not yet a
compiled or runtime result. The focused suite and production profile must pass
on Buildbox before a new candidate can be considered.
