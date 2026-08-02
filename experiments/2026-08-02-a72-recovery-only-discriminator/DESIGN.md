# Recovery-only discriminator design

## Ownership transition

The normal Gemian kicker serializes its global state and every ordinary
external-watchdog kick beneath `wd_common_drv.c`'s `lock`. The discriminator
uses that same lock. It first proves the kicker and watchdog API are ready,
sets `g_enable` to zero, and calls the low-level arm helper without releasing
the lock. Any kicker already inside the lock completes before takeover; any
kicker waiting behind takeover encounters either disabled kicker state or the
low-level terminal-owner interlock.

The low-level helper serializes all TOPRGU access beneath
`rgu_reg_operation_spinlock`. It refuses an uninitialized mapping or any
timeout other than 12 seconds before claiming ownership. Once claimed, later
`mtk_wdt_restart()` calls cannot reload the timer. The helper writes length,
reset-only mode, and one restart key in that order and returns readback.

## Failure domains

- Before low-level ownership, failure restores `g_enable=1`; the ordinary
  kicker remains the recovery owner.
- At or after low-level ownership, failure never restores the kicker and never
  rewrites the previous watchdog mode. It emits a terminal failure marker and
  waits for reset.
- CPU8 and CPU9 are rejected at the first line of the MT6797 PSCI boot callback
  while this configuration is enabled. No A72 owner or firmware request is
  reachable.

## Trigger and attribution

The built-in discriminator schedules one delayed-work invocation 15 seconds
after the normal watchdog work callback finishes. There is no procfs, sysfs,
debugfs, module parameter, ioctl, or userspace trigger. The 12-second watchdog
window begins only after the ownership lock closes the kicker race.

The armed marker includes a fixed ABI, stage, timeout, and explicit A72
prohibition. `console_lock()`/`console_unlock()` provides a synchronous console
drain before the work item becomes idle. Console-ramoops is already a
registered console under the pinned configuration; recovery still requires
the exact marker from the subsequent known-good boot rather than assuming the
flush was durable.

## Exit criteria

Patch generation and compile review are necessary but not sufficient. The gate
passes only after one checksum-attributed `boot2` deployment yields all of:

1. selected recovery-only kernel identity;
2. exact marker recovered from console-ramoops;
3. bounded watchdog reset and changed boot ID;
4. known-good Gemian identity after reset;
5. CPU8 and CPU9 absent throughout;
6. unchanged `boot2` checksum after the cycle.
