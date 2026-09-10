# Restart exclusion before shared effects

The [restart-wrapper correction](FULL_KERNEL.md) reaches the watchdog guard
before RTC mode writes. It does not cover the earlier steps in an ordinary
restart: `kernel_restart_prepare()` calls reboot notifiers and device shutdown,
and ARM64 `machine_restart()` stops other CPUs before the wrapper. An emergency
restart also invokes the dump path before architecture restart. These source
paths can precede the existing guard while capture owns the watchdog.

The [restart gate](patches/restart-gate/0001-watchdog-arbitrate-takeover-before-restart-effects.patch)
uses one atomic claim shared by restart and watchdog takeover:

* A restart claim made first permanently refuses subsequent takeover with
  `-EBUSY`, before its first watchdog register read or write.
* A capture claim made first parks restart before notifiers, dump callbacks,
  device shutdown, CPU-stop operations and low-level reset effects. It does not
  stop the CPU completing takeover or reload the watchdog.

The guard is first in `kernel_restart_prepare`, `emergency_restart`,
`machine_restart` and the low-level `wdt_arch_reset`. Repeated restart guards
before capture are harmless. The takeover still uses its register lock, now
with local IRQs saved and disabled across the claim and timer programming.
Without that change, an IRQ on the takeover CPU could park that CPU after its
claim but before arming. A competing restart on another CPU can park while
the takeover CPU completes its existing three writes and readback.

The claim is never released during this one-attempt experiment. Existing
repeat-takeover and programming-failure ownership rules remain: a failed
readback does not release ownership or permit a timer reload. Normal builds
compile the new call sites to an empty inline function; the atomic state and
takeover changes are confined to the experimental configuration.

## Evidence and limits

The [receipt](results/restart-gate.json) pins the four parent and changed files
against the verified 44-patch prepared source. The
[focused test](test-restart-gate.py) compiles the actual watchdog and restart
function bodies with injected hardware/callback effects and a C11 atomic shim.
It reproduces the parent's earlier restart effects, tests all four entries in
both orders, and forces three concurrent claim orderings, including a restart
while another CPU is between claim and timer programming. IRQ-state assertions
require the local exclusion during takeover. This is host control-flow evidence,
not a simulation of ARM64 interrupt delivery or physical timer behavior.

Strict checkpatch passes with the missing-signoff category excluded for the
synthetic, non-certifying experiment archive. The patch is entry 45 in the
[full-kernel inputs](full-kernel-inputs.json); native compilation and linked
inspection are pending.

The gate changes no power-off, halt, suspend, panic body, direct firmware call
or unrelated shared-resource consumer. It is not an NMI/FIQ safety mechanism.
A refused restart busy-waits until the fixed cutoff; admission must account
for that failure behavior and thermal recovery separately. This correction
does not establish complete kernel actor isolation, retained-RAM survival,
boot admission or hardware support. No device access occurred.
