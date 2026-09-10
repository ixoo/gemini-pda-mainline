# Transport setup prerequisites

The two unselected [patches](patches/transport-setup/) repair transport setup
and exclude display-triggered power work for the isolated recovery experiment.
They follow request capture and its operation-ownership prerequisites. They
do not yet connect the [controller](CONTROLLER_INIT.md) to the responder or
authorize a device cycle.

## Observed launcher and proposed configuration

Two completed read-only Gemian inspections on 2026-09-10 retained boot identity
`f2b923f9-f952-4cdb-80e0-72142282cc4f` before and after each inspection. Exactly
one launcher process was found. Its executable resolved to
`/system/vendor/bin/wmt_launcher`; arguments were
`/vendor/bin/wmt_launcher -p /vendor/firmware/`, with no mode or baud override.
A separate executable check required the same process start time before and
after hashing. SHA-256 was
`79ec10a6cc96642c042a6ae160d838e5b5a9cb63e6447f1761fc6a78000ac8bc`, matching
the retained binary. An earlier unprivileged inspection stopped at a process
permission failure and is not counted as a completed identity check. Raw
captures remain private; no service, radio, parameter or boot state changed.

Private static analysis in the RE VM located the launcher's MT6797 branch
setting transport 3 and FM communication 2, and its SoC ioctl construction at
`0x3158..0x3178`. The selected source design is scalar `0x23` for native ioctl
`0x4004a005`: BTIF transport, FM communication, no UART baud. The native
`wmt_lib_set_hif()` selects BTIF from the low nibble and FM from the next nibble;
BTIF does not use the UART baud field. The live ioctl argument and cached chip
query result were not observed. This is a source-backed candidate choice,
not a measurement of that process's ioctl traffic.

## Correct setup completion

The native `WMT_IOCTL_SET_STP_MODE` case previously returned zero when no free
operation was available. The first patch returns `-ENOMEM` for that failure.
The experiment symbol also changes the operation's zero timeout to 4000 ms.
With the existing operation-ownership repair, `wmt_lib_put_act_op()` then waits
for and checks the worker result instead of reporting queue acceptance.
`hif_info` is set only after success. Ordinary builds retain their zero timeout.

This wait does not cancel a timed-out worker, restore software transport state,
or extend the twelve-second watchdog cutoff. Configuration already mutates
software state before operation allocation. The future controller must stop
normal requests after any failure, without retry or rollback. Its fixed-input,
single-attempt gate, configuration records and ON/OFF ordering remain open.

## Exclude display-triggered power work

The framebuffer POWERDOWN callback schedules `gPwrOnOffWork` even when
`hif_info` is zero; UNBLANK can schedule it after configuration. The alternate
early-suspend callbacks also schedule that worker. The worker can invoke
loopback function ON/OFF with retries. Leaving `hif_info` unset therefore does
not isolate the test.

The second patch omits both callback registration and corresponding unregister
when `CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR` is enabled. The work object and lock
are still initialized. This excludes these callback entry paths from startup;
it does not claim isolation of other power, reset, thermal or userspace actors.

## Verification

The [source receipt](results/transport-setup-sources.json) pins the exact parent,
intermediate result, final source and both format patches. Strict Checkpatch
passes with the archive's existing author/path/name exceptions.
The [focused test](test-transport-setup.py) executes the native HIF ioctl case
with injected allocation and worker returns in ordinary and experimental
builds. It checks four outcomes in each, copied operation contents, wait value
and readiness publication. It does not exercise actual scheduler timing.

The existing Buildbox checker accepts `COMMIT --transport-setup` for the complete
native `wmt_dev.c` object. The [native compilation receipt](results/transport-setup-object-compile.json)
records successful baseline and experimental objects at
`4d8f85e471612bade24b964465500ae8fa2a409e`, with the pinned GCC 6.3 toolchain
and Gemian configuration. The experimental object has neither
`fb_register_client` nor `fb_unregister_client` references; the baseline
registers the callback. The focused fixture also passed on Buildbox. All eight
package files match the remotely validated inventory and checksum manifest.
An initial attempt stopped in source preparation before object compilation;
the checker now preserves all prerequisite sources before narrowing compilation.

The native compiler command retains `-w`, so this is not a warning-clean claim.
Both patches replay and reverse to their exact pinned sources. Complete linking,
the alternate early-suspend configuration and runtime behavior were not tested.
No kernel profile selects these patches and no image has been built or installed
for them.
