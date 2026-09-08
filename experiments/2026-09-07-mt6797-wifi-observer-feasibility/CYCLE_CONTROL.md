# Wi-Fi cycle control and recovery assessment

## Decision

A single direct on/off write is not yet a controlled lifetime experiment.
The current Gemian session has active ConnMan, Bluetooth and WMT actors, and a
loaded display-driven ConnMan plugin. A candidate needs explicit startup and
shared-consumer control before its first observed WLAN load. Do not stop those
services or send radio commands to the current session on the strength of this
assessment.

The existing 12-second Gemian recovery discriminator supplies a useful proven
watchdog mechanism, but its trigger and window are not a validated Wi-Fi cycle
protocol. The observer remains unimplemented and unadmitted; this record pins
the concrete control and recovery requirements discovered during design.

## Native request and teardown paths

[Source identities](results/cycle-control-sources.json) pin the selected public
Gemian kernel and corresponding ConnMan package source revisions. This is
source analysis, not attribution of the installed machine code.

- `wmt_chrdev_wifi.c` 263–339 accepts first-byte `0`/`1` requests, but returns
  the write count immediately when its local `powered` flag already matches.
  Only the other branch calls WMT function-off/on. A successful write therefore
  cannot identify a load/shutdown cycle. Capture actual callback entry and
  completion, and distinguish a no-op request and reset/failure path.
- `gl_init.c` 2270–2400 places workqueue flushes, a 3000 ms halt-lock attempt,
  and three sequential 3000 ms thread-completion waits before adapter stop
  when multithreading is enabled. It logs completion timeouts and continues.
  The 12 seconds available to the historical watchdog cannot be treated as a
  complete worst-case budget for load, remove, firmware stop, OFF and export.
  The workqueue flushes and native power-status loops add further limitations.
- The same remove path clears `hif_thread` before `wlanAdapterStop`, even after
  an HIF completion timeout. Thus the ordinary remove path can select the
  direct WCIR-read branch discussed in the [native-site assessment](NATIVE_SOURCE_FEASIBILITY.md).
  A null pointer does not prove thread quiescence. Capture each completion
  result before clearing pointers; reject a timeout as normal-cycle evidence.
  Probe-failure cleanup is a different caller and needs separate classification.

## Current userspace control

The [read-only metadata receipt](results/cycle-control-gemian-metadata.json)
records six authenticated invocations on Gemian `3.18.41+`. Four completed their
before/after boot checks; two stopped during process-map inspection. The final
root inspection completed with the same boot ID and stable ConnMan MainPID.
Only file/process/service metadata and a software-plugin hash were observed.

ConnMan and Bluetooth were active, and `wmt_launcher` was present. A bounded
search of 135 init/service files found no selected WMT/WLAN strings. That
negative result does not identify the launcher parent or exclude Android-side
startup. No service, interface or radio state was changed.

ConnMan had `suspendplugin.so` mapped. Its installed package revision suffix
resolves to public commit
[`c0615773e2250f910e0ec9fc883a5f168dbcaeb5`](https://github.com/gemian/connman-plugin-suspend-wmtwifi/blob/c0615773e2250f910e0ec9fc883a5f168dbcaeb5/src/suspendplugin.c).
That source registers display-state handlers and handles initial display state
at plugin initialization. With an available interface, its helpers can send
`NL80211_CMD_SET_WOWLAN` and `NL80211_CMD_TESTMODE` with a suspend command.
Loaded code is not evidence that either command occurred during this snapshot.
The package name does not mean this is a simple WMT power-switch wrapper.

A future test must account for these potential commands as well as ordinary
network management and other CONSYS consumers. Disabling association alone is
not a source-backed exclusion of display-driven test-mode commands. Do not
assume Wi-Fi shutdown causes common OFF while Bluetooth or another common
consumer remains active.

## Recovery and capture requirements

The [recovery-only design](../2026-08-02-a72-recovery-only-discriminator/DESIGN.md)
and [runtime result](../2026-08-02-a72-recovery-only-discriminator/README.md)
prove their exact no-A72, fixed-12-second watchdog takeover and recovered marker.
The historical artifact is consumed and must not be replayed. Its delayed-work
trigger and CPU-hotplug exclusion cannot be transplanted into WLAN control
without a source/lock and candidate-specific recovery assessment.

Before implementing the observer, select a concrete candidate startup path
that bounds every preparatory radio action and excludes competing consumers.
Then specify the one native load/shutdown cycle, watchdog arm point and deadline,
read-preserving capture sites, fixed storage and overflow refusal, and export
before recovery. An ordinary RAM buffer cannot retain a stalled-cycle result
across reset; logging only a successful terminal can leave a reset inconclusive.
A new persistent writer needs its own exact range/write-budget contract.

No timeout, missing terminal, shortcut return, active competing consumer, or
empty recovered record may be classified as the required successful cycle.
This assessment adds neither an upstream vendor ABI nor a hardware-support claim.

## Android startup follow-up

Four further read-only invocations, recorded separately in the
[metadata receipt](results/cycle-control-gemian-metadata.json), kept the same
Gemian boot identity. The unique WMT launcher's ancestor chain led through
Android `/init` and `lxc-start` in `lxc@android.service` to host systemd.
The LXC configuration names `/var/lib/lxc/android/rootfs` and `/init`.
Inspection used the Android init process's root namespace, rather than assuming
that identically named paths in the host root described the container.

A bounded 52-file locator found the normal, factory and meta connectivity
rules. Only the normal rules were selected for the detailed startup assessment.
The root init configuration imports the hardware-specific rules, and
`init.mt6797.rc` line 3 imports `init.connectivity.rc`. Root init starts the
core, main and late-start classes at lines 585, 589 and 590.

In the normal connectivity rules, both WMT loader and launcher belong to core
and lack `disabled`; only the loader is `oneshot`. The file supplies no explicit
loader-completed dependency for starting the launcher. The GNSS helpers `mnld`
and `MPED` belong to main and also lack `disabled`. The two supplicant services
and `wifi2agps` are disabled declarations. These are configuration facts, not
observations that every service ran or acquired a common resource.

This rules out using an otherwise unchanged full Gemian boot followed by a
ConnMan stop as proof of a pristine, inactive connectivity starting state.
Starting Android's whole core/main classes also cannot be treated as a
WLAN-only action. A candidate must select its startup policy before boot and
observe actual driver registration, common-resource acquisition and first WLAN
callback. Class membership, launcher presence and a completed loader process
are insufficient readiness signals. Killing a process is not a reviewed
service-isolation procedure.

The next design choice is between a candidate-specific minimal startup and an
explicitly observed full-stack cycle that accounts for every participating
consumer. Neither is implemented or admitted here. Repeating the same service
inventory will not resolve that choice; it requires a concrete acquisition and
recovery design. The read-only follow-up changed no services, properties,
configuration, partition, firmware or radio state.
