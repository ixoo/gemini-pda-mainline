# Space starts the attended keyboard test

The owner requested a start screen on the PDA instead of coordinating timed
prompts through chat. [space-ready.c](space-ready.c), prepared by [space-start.py](space-start.py), is a separate userspace
helper, delivered to executable RAM. It opens the admitted keyboard event node
and tty1, verifies their device identities and current Unicode VT, saves console
settings, and displays “Press and release SPACE”. It accepts one Space press and
release, requires matching console Space input, then waits for 500 ms without
queued input and verifies every key is released. It restores console settings
before returning a readiness witness. Wrong keys, lost events, stale input,
excess input, signals and the five-minute deadline refuse startup.

The helper starts before restarting the sealed kernel logger, so waiting at the
screen consumes neither the capture nor logger time budget. After its successful
exit and reader release, the launcher restarts logging and runs the unchanged
20-step capture with the [explicit same-boot retry](LOGGER_RESTART.md). The
readiness helper changes no keymap, VT, driver or hardware resource, and does not
launch the capture itself. No kernel rebuild, partition write or reboot is needed.

Build this separate helper from a clean pushed commit with the existing managed
userspace builder:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/buildbox_userspace.py --branch main --keyboard-space-ready
```

The package contains the static ARM64 helper, notices, exact source/header
identities and build provenance. Two stripped binaries must match, and
[test-space-ready.py](test-space-ready.py) exercises press/release, held Space,
wrong keys, release without press, dropped input, timeout and signal cleanup
under ARM64 QEMU with a real PTY and injected evdev/VT metadata. The fixture is
not a hardware result. Deployment still requires an exact package and live
session identity. The timed-capture binding selects the prepared same-boot retry; that retry
has not yet executed.

The first package build did not publish. Its fixture diagnostics were incorrectly
placed outside the builder’s retained failure-log list; that path is corrected.
A bounded diagnostic run of all seven cases using static ARM64 glibc and QEMU
passed. The retained second-build diagnostics identified fixture-only `_IOC_NR` and
`_IOC_SIZE` macros absent from musl. The fixture now compares its two exact
ioctl requests and fixed bitmap length. The production helper is unchanged;
acceptance still requires the ordinary musl package build and tests.

The accepted musl package was built at revision
`9982265768a31a0fe868f193b6f8ba4ac111054d`, with package identity
`f6584eeffe6659bb38aeea63c46830d250cd3d36ca4a0dcddfcad9d5482ded22`.
Both stripped ARM64 replicas match and all seven PTY fixtures pass, including
positive `EVIOCGKEY` return values. The generated RAM-delivery and readiness
shells pass Bash syntax and ShellCheck (excluding literal awk quoting).
This admits the readiness screen on the existing boot; it is not a live
readiness result or keyboard regression pass.

The first live readiness connection closed after 60.318 seconds with exit 255
and no readiness witness. The capture and restarted logger were not launched.
The server's 60-second channel-idle limit was not refreshed by SSH keepalives.
The readiness helper now emits a bounded waiting line every 20 seconds; its
five-minute limit remains. The logger wrapper likewise emits channel output
every 20 seconds while checking and reaping its child within five seconds,
inside the existing ten-second seal wait. Revised helper deliveries use a
package-qualified directory, preserving the original helper and wait evidence.

The revised package at `e5759fe0db3c20e92e14493180312c8b0c32c197` has identity
`a60137337512b9ed7d44220c94b4303aabe0676ac492af312cc0e052177b7b36`.
Its two ARM64 replicas match and all seven musl/PTY fixtures pass, with the
timeout fixture additionally requiring channel-status output. The logger
poll/wait loop was exercised under ARM64 BusyBox for both zero and nonzero
child exits. Generated delivery, readiness and logger shells pass syntax and
ShellCheck. The second live start-screen attempt is prepared, not yet observed.
