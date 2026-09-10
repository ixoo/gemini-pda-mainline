# Emergency reset and reload ownership

The unselected [patch](patches/recovery-reset/0001-watchdog-preserve-owned-deadline-across-emergency-reset.patch)
closes two remaining low-level watchdog races after the
[ordinary setter correction](RECOVERY_SETTERS.md). It does not establish complete
reset isolation or select a boot candidate.

## Observed source problem

In the pinned Gemian source, `mtk_wdt_restart(WD_TYPE_NOLOCK)` checks recovery
ownership before its unlocked register store. A caller that passed that check
before takeover can reload the newly owned watchdog afterward. CPU-hotplug
exclusion covers the hotplug notification caller, but source also contains
no-lock reloads in AEE/IPANIC exception paths. Their exact selection and entry
conditions differ; minimal userspace alone is not an exclusion proof.

`wdt_arch_reset()` has no ownership check. It calls secure firmware to disable
DFD, then takes the watchdog register lock and reloads the timer, replaces MODE,
calls the PMIC reset preparation routine, and requests software reset. Its
MODE update clears watchdog ENABLE. The existing register lock therefore does
not itself preserve the owned deadline.

These observations come from the complete native functions in
[`mtk_wdt.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c)
and the watchdog API, AEE and connectivity caller search at that same revision.
The [source receipt](results/recovery-reset-sources.json) pins the exact edited
parent after the earlier ownership and setter patches.

## Experimental behavior

Under `CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR`, the no-lock branch makes one
`spin_trylock()` attempt. Contention refuses the reload without waiting on a
possibly interrupted lock holder. Once locked, it checks ownership again and
keeps the lock through any permitted reload. Thus a pre-takeover caller either
finishes before takeover or refuses afterward. Contention before takeover may
also skip this exceptional reload; ordinary kicker behavior is unchanged.
The existing early ownership check remains only a fast refusal.

For direct reset, the experimental secure-firmware call moves inside the
existing register lock, after a new ownership check. An owned reset request
releases the lock and enters the function's existing terminal wait. It never
returns to its caller and reaches no secure-firmware, PMIC or watchdog reset
operation. A request already holding the lock can complete its original reset
sequence before takeover; the change does not claim ownership retroactively.
The lock-wait and terminal loop do not provide a software time bound. Recovery
still depends on the independently armed hardware watchdog.

Ordinary builds retain the original secure-call placement, direct reset and
unlocked reload behavior. No change is made to CONMCU reset operations:
`mtk_wdt_swsysret_config()` is used by the native connectivity power sequence,
so indiscriminately refusing every write to this register block would prevent
the intended WLAN startup.

## Verification and limits

The [focused test](test-recovery-reset.py) extracts the actual reset, reload and
arm functions and runs them with injected registers and thread scheduling. It
reproduces the parent's direct-reset and no-lock reload races, then verifies
pre-owner behavior, already-owned refusal, takeover between entry and lock,
and no-lock contention for the corrected functions. A trapped terminal loop
checks that reset refusal releases the lock and does not return. Secure-firmware
and PMIC calls are counted; they are stubs, not emulated hardware.

Both source versions pass their expected outcomes. The patch replays and
reverses exactly and passes strict Checkpatch with the archive's existing
sign-off/path/camelcase exceptions. The existing native object checker accepts
`COMMIT --reset` to compile both complete watchdog units and run this fixture.
No image, device state or firmware is changed by these tests.

The [native compilation receipt](results/recovery-reset-object-compile.json)
records successful parent and child watchdog objects at
`81c96acb7d38ff0d8e29515cb5c86bd2d86d0bfb`, using the pinned GCC 6.3 toolchain
and Gemian configuration. The fixture also passed on Buildbox. All 13 fetched
files match its validated checksum manifest. The native compiler retains `-w`;
this is not a warning-clean result, complete kernel link or device test.

The higher-level `arch_reset()` wrapper in `wd_api.c` can mark RTC boot modes
before entering this low-level reset function. This patch does not guard those
writes. Explicit restart entry points, other reset notifiers, watchdog request
routing, shared subsystem reset fields and direct register aliases still need
candidate-specific exclusion or ownership review. Retention and cpuidle
exclusions in the [integration decision](RECOVERY_INTEGRATION.md) remain required.
Neither these tests nor a complete object compilation proves watchdog timing,
physical reset, RAM retention or radio safety.
