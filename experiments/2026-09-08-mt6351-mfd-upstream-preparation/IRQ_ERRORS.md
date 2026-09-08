# MT6351 IRQ error-path review

Source review of the nine-patch compile topic, 2026-09-08. No device access,
interrupt injection, suspend attempt, or register write was performed.

## Inputs

The prepared Linux tree for project commit `843c46ae` uses upstream commit
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c` plus the recorded nine patches.
The following files were read directly on Buildbox:

| File | SHA-256 |
| --- | --- |
| `drivers/mfd/mt6397-irq.c` | `34bf992b5e41ce5532392927b9d001f88d8d232a46c27de550da40ec89d6c8b4` |
| `kernel/notifier.c` | `04dd85fc0c2a41d0072b28f58c1390d3add6054f03367b88b1403eb9766a14ab` |
| `kernel/power/suspend.c` | `71c4a16ad3db8cac349b7d8b52cdfddae26a8918216f18ec54a68c1761077576` |
| `kernel/irq/manage.c` | `ce0db3d162604dc793fa9e2e4d3f6ba3e6314b39e37d79d34061744ad58aa735` |

## Observed control flow

| Path | Current source behavior | Consequence and limit |
| --- | --- | --- |
| Initial mask programming | Returns the first failed write before domain/handler registration | Covered by the earlier mask-error patch and focused fixtures |
| Status read | Returns before dispatch or acknowledgement when `regmap_read` fails | A failed read does not become a fabricated status word; the thread still examines other banks and returns `IRQ_HANDLED` |
| Status acknowledgement | Dispatches mapped set bits, then ignores the acknowledgement write result | Failure is not reported here; repeated assertion/delivery is possible but unmeasured |
| Normal mask synchronization | Writes every requested mask and ignores each result | The requested software mask is not proof of the hardware mask; this void callback cannot propagate a bus errno directly |
| Suspend preparation | Writes wake masks, enables parent wake, ignores all results, returns `NOTIFY_DONE` | Partial programming and failed wake enable do not veto suspend |
| Post-suspend | Writes normal requested masks and disables parent wake, ignoring results | Restoration is unproved, and wake disable is attempted even if the corresponding enable failed |

These are source facts and their direct control-flow implications. They do not
establish an interrupt storm, lost event, failed wake, or unsafe voltage on the
Gemini. No such runtime result is claimed.

## Why a simple notifier error return is insufficient

`suspend_prepare()` invokes the robust notifier chain before freezing processes.
On a prepare error it restores the console and returns. The robust chain calls
the recovery event for `nr - 1` callbacks: it explicitly excludes the callback
that returned the stopping result. That callback must recover its own partial
changes before returning failure; it will not receive an automatic
`PM_POST_SUSPEND` from this error path.

Therefore, adding `notifier_from_errno(ret)` immediately after a failed mask
write would leave earlier wake-mask writes in place. A failed wake-enable call
after successful mask writes has the same restoration requirement. The IRQ
core also resets the wake depth when the first enable fails, so unconditional
post-suspend disable cannot serve as balanced ownership in that case.

The post-suspend notification is invoked for its effects; its result is ignored
by the shown callers. Reporting a callback error there does not itself repair
the device or turn an incomplete restoration into a successful one.

## Implementation boundary

Do not apply an error-return-only suspend patch. A bounded successor needs to:

1. Establish serialization between normal mask synchronization and suspend mask
   programming; preparation occurs while processes are still running.
2. Restore the normal requested masks within the failing prepare callback,
   attempting all banks and retaining evidence of restoration errors. A failed
   transport still leaves the physical state unknown; do not label an attempted
   restoration successful.
3. Track actual ownership of the parent wake reference and release only an
   acquired reference, including later-notifier failure and normal resume.
4. Define how resume/restoration failure is reported without claiming that a
   notifier return value provides a recovery mechanism.
5. Exercise each mask-bank failure, wake-enable failure, restoration failure,
   and a later notifier's failure with the actual callback code before compile
   and a separately admitted hardware test.

This identifies the required error contract, not an admitted implementation.
Status acknowledgement reporting can be a separate small correction. It must
not add an automatic retry or claim that returning `IRQ_NONE` clears an asserted
hardware interrupt. Shared VCN33 ownership remains independent of this review.
