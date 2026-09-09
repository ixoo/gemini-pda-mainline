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

## Minimal startup direction and kernel actors, 2026-09-09

Use a candidate-specific minimal startup as the design direction for the first
load/shutdown observation. It should start only the reviewed connectivity
prerequisites and collector, keep WLAN/P2P interfaces administratively down,
and issue no scan, association, AP/P2P-mode or packet-transmission request.
This avoids introducing full Android classes, ConnMan, Bluetooth and GNSS
consumers into a WLAN lifetime discriminator. It is a design choice, not a
completed initramfs, a claim that firmware cannot transmit, or authorization
to change the current Gemian session. The exact loader prerequisites, capture
storage and recovery window still require closure before implementation.

The [kernel-actor receipt](results/startup-kernel-actors-review.json) identifies
one additional control path that userspace isolation alone must not obscure.
Five prepared source files were compared byte-for-byte with Git objects at
`59e00a9144d782e148332009a835b99c43382467`. The retained compile package's log
records their five compilations; its symbol map has a global text definition
of `kalBoostCpu`, as well as the performance-start and framebuffer callbacks.
This supplements the [compiler-input review](NATIVE_SOURCE_FEASIBILITY.md#recorded-compiler-command-follow-up-2026-09-09).
It is source/link evidence, not executed instruction or current-boot evidence.

`initWlan()` registers `wlan_fb_notifier_callback` independently of the ConnMan
plugin. For accepted blank events, the kernel callback clears the performance
monitor's disable flag on unblank, or disables the monitor on powerdown, after
its halt-lock checks. Unblank does **not** call `kalPerMonStart()`. Initialization
sets the monitor stopped and gives its timer a 1000 ms period. The two start
calls found in the gen3 C sources are in station and P2P transmit entry points:
the station call additionally requires successful enqueue and carrier; the P2P
call requires a connection or a nonempty client list. `WIFI_write`'s first-byte
`1` branch requests WMT function-on without a netdev-open or mode-selection call
in that branch. The `S`/`P`/`A` branches remain outside the proposed cycle.

The MT6797 platform source supplies a non-weak `kalBoostCpu` implementation.
For a nonzero request it submits a CPU-count request, capped by possible CPUs,
and a 2,000,000 kHz frequency request through the PPM API. Zero submits release
requests. This is a request to policy code, not proof that any CPU was enabled
or ran at that frequency. The weak no-op definition in `gl_kal.c` therefore
cannot justify calling the selected platform path harmless. The performance
handler can make nonzero requests after a throughput-level change; stopping a
running monitor also calls the zero-request path.

For the minimal cycle, retain the native monitor behavior and require no
performance-monitor start or CPU-boost call in the attributable capture,
alongside no station/P2P transmit entry and no mode/association request.
Keeping interfaces down and excluding network managers is the source-backed
way to avoid the identified starts; a live state snapshot alone is not proof
of their absence throughout the cycle. A display unblank by itself is not a
counterexample, and no speculative boost-suppression patch is needed from this
review. Unexpected start/boost activity invalidates this isolation predicate
and must be preserved, not reclassified as an ordinary load/shutdown pass.
This does not exclude unrelated kernel CPU policy or establish that the wider
candidate's power behavior is bounded.

No service, framebuffer state, CPU policy, radio or kernel was changed. The
source review narrows the startup/capture contract without admitting a build
or selecting a new device candidate.

The [startup dependency follow-up](STARTUP_DEPENDENCIES.md) identifies the
concurrent patch-search responder and separate common/WLAN firmware lookups.
It fixes the next startup ordering work without selecting a live command.

The [single-attempt correction](OPENMTTOOLS.md#single-attempt-startup-policy)
now removes an internal retry path that could multiply a single userspace
request into three initialization attempts. Its complete source file now
[compiles on Buildbox](OPENMTTOOLS.md#complete-source-file-compilation), but
the patch is not a device candidate; cleanup and recovery remain unvalidated.

## Controller route and operation timeout

The [five-file source receipt](results/controller-route-sources.json) pins a
further review of the existing native control routes. Select
`WMT_IOCTL_FUNC_ONOFF_CTRL` on the already initialized WMT descriptor for the
minimal experiment design. This is reuse of the vendor experiment interface,
not a proposed mainline ABI or an admitted runtime controller.

The first-byte `0` branch of `WIFI_write()` can call `pf_set_p2p_mode` with a
disable request before function-off whenever the netdev and callback exist.
Both its on and off failure branches invoke `WMT_CHECK_DO_CHIP_RESET`, which
can assert/reset the chip when `g_IsNeedDoChipReset` is set. The corresponding
WMT ioctl case calls only the selected function-on/off wrapper and translates
its boolean to zero or `-EFAULT`. It avoids those character-device wrapper
actions and the wrapper's separate `powered` shortcut. It does not remove
reset/error handling deeper in the stack or prove that WMT actually changes
state. The controller must still capture the real lifecycle calls.

In the reviewed 64-bit ABI the ioctl is `_IOW(0xa0, 6, int)` (`0x4004a006`).
Despite the encoding, the implementation uses the scalar argument directly,
not a user pointer: bit 31 selects on, and the low nibble selects the function;
`WMTDRV_TYPE_WIFI` is 3. Thus the design uses only scalar `0x80000003` for on
and `3` for off. No such ioctl was issued during this review.

The shared `mtk_wcn_wmt_func_ctrl()` gives Wi-Fi operations a 4000 ms signal
wait for both directions, independently of the larger non-Wi-Fi constants.
Its wake/PSM work occurs outside that wait. More seriously,
`wmt_lib_put_act_op()` returns an operation to the free queue after timeout
without removing it from the active queue or cancelling a running worker.
It also reads `pOp->result` after timeout diagnostics, so a late zero result
can produce success. The worker retains and later signals its operation
pointer after `wmt_core_opid()` returns. A timeout therefore cannot authorize
a second request, cleanup by descriptor close, or a successful-cycle verdict.

The fourth [experiment patch](patches/0004-wmt-retain-timed-out-operation.patch)
forces nonpositive waits to fail and omits the waiter's free-queue return on
that path. This deliberately retains a possibly worker-owned operation; it
does not reclaim it when the worker eventually completes. The normal
experiment must stop issuing requests on failure and must not reinitialize
the WMT library. No generic cancellation or indefinite-service pool policy is
introduced. Positive completion and unsubmitted-operation cleanup keep their
existing behavior; other reset/completion races remain outside this fix.

The [actual-function regression](test-operation-timeout.py) reproduces original
timeout recycling and late success, then verifies the changed behavior. Eight
injected cases cover ordinary success, worker error, timeout, late success,
negative wait, queue refusal, coredump blocking and asynchronous submission.
The host compile used C11 and `-Wall -Wextra -Werror`. Checkpatch passed with
the previously pinned checker and explicit legacy `CAMELCASE` exception.
These are sequential injected tests, not a worker-cancellation or scheduling
proof. Full-file compilation of the fourth patch remains outstanding.

The next controller implementation must anchor capture and an independently
reviewed recovery owner before the first effect-bearing request. A reported
operation error ends the normal cycle; a successful on request is insufficient
without an attributable completed load. Off is issued only after that joined
success, with its own complete teardown evidence. The four-second wait is
neither a total operation bound nor an excuse to extend the consumed historical
watchdog experiment. Persistent capture and recovery integration remain open.
