# Serialize ordinary watchdog setters with takeover

The unselected [patch](patches/recovery-setters/0001-watchdog-serialize-setters-with-diagnostic-takeover.patch)
implements the ordinary setter part of the [recovery design](RECOVERY_INTEGRATION.md).
It adds checks under the existing register lock in timeout, mode, enable and
ordinary reload operations. A caller that was already waiting for the lock
cannot change these registers after takeover. A rejected enable operation
returns `-EBUSY`; the other three interfaces return void. Before takeover,
their existing operations are preserved.

This is a source-only extension of the historical low-level takeover helper.
The [receipt](results/recovery-setters-sources.json) pins that prerequisite
patch, both complete source states, the unchanged recovery declaration header,
native register definitions and operation enums. No historical profile or
consumed boot artifact is selected. The conditional experiment symbol remains
the prerequisite's symbol; it is enabled only for this compile/test comparison.
The archive author is synthetic and supplies no DCO certification.

## Scope and remaining ownership

The earlier fast check in `mtk_wdt_restart()` remains, including for the
no-lock branch. An additional check inside its ordinary locked branch closes
the reproduced check-before-lock race. No-lock callers still require the
independent CPU-hotplug exclusion; this patch does not serialize them.

Direct reset, DRAM retention, request routing, SPM power transitions and
out-of-band register writers remain outside this correction. In particular,
the retention function can still perform an unlocked MODE read/modify/write.
The patch is not a complete exclusive watchdog owner and does not admit a
Wi-Fi cycle. It neither arms a timer by itself nor supplies the controller
entry point, capture join, global resource isolation or restart approval.

## Verification

The [fixture](test-recovery-setters.py) executes the complete native timeout,
mode, enable, arm and reload function bodies with the native register macros,
enums and recovery-state declaration. MMIO is memory-backed, locks use pthread
mutexes, and device-tree discovery is excluded from this host fixture.

Twelve parent/child comparisons cover all four operations before takeover,
after takeover, and already waiting to acquire the register lock when takeover
occurs. A condition-variable handoff fixes the last ordering, including passage
through the old reload fast check. The parent allows all four raced operations
to write afterward; the child allows none, retains register/software state and
returns the enable refusal. Ordinary pre-takeover operations still write.
All comparisons pass with C11, `-Wall -Wextra -Werror` and pthread support.
This tests injected ordering and register requests, not real spinlocks,
posted-write completion, timer timing or hardware recovery.

Patch reversal/replay and strict Checkpatch pass with the existing legacy-name
and synthetic-sign-off exceptions. The [Buildbox check](check-recovery-setters.py)
compiles the complete parent and child watchdog source with the pinned native
compiler command and generated headers, verifies header selection and the
non-SPM/non-dummy path, and runs the fixture there. Invoke it from a clean,
published checkout with its exact commit argument under the existing Buildbox
build lock. Native compilation is pending at this source checkpoint.

Full linking, complete recovery ownership and an admitted device session remain
necessary. No kernel image or device action is selected here.
