# Fresh eMMC session — coordinator handoff, not a boot request

The [current-state receipt](KNOWN_GOOD_CURRENT_STATE.json) confirms the retained
Gemian kernel and unchanged previously confirmed Gemian boot ID. The preceding
mainline identity attempt timed out without output. Its budget remains consumed;
no eMMC read was attempted. This preparation creates no new boot claim.

Reuse the installed candidate pinned by [SESSION_PACKET.json](SESSION_PACKET.json):
raw SHA-256 `a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf`,
padded SHA-256 `a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821`,
candidate manifest `54b07f0c70e77fd1e34fde4fc1c929980f0d8c3410f0a97ce3f15ffec1a66179`.
The retained deployment receipt is
`5aed5d6554922835ad6e50091056f9145b2fc1b07d40507353c38202e4b50543`.
No rebuild, marker change, reinstall or baseline repetition is proposed.

## Measurement and decision

One input-only read of the complete live-GPT-selected boot2, exactly 16 MiB,
compares its bytes with the installed padded candidate. Before/after guards
attribute serviceability to one newly observed mainline boot. A complete sealed
independent controller log is required to distinguish an apparently correct read
from a read accompanied by controller errors.

A matching read plus serviceability and complete error-free log permits separate
recovery review; it establishes only this bounded read on this exact session.
A checksum mismatch or attributable controller error rejects the read and sends
its evidence to storage diagnosis. Transport interruption, unknown identity,
missing log coverage or deadline failure is inconclusive; stop without retry and
review preservation/recovery separately. A failed preflight never admits the
read. No result automatically admits another queued test.

## Prepared admission and prompt capture

A separate private fresh-session draft has a new UUID and the currently enabled
source identities. Its candidate and accepted supplemental prerequisite closure
were reverified offline. Physical selection and stable power remain explicitly
false, so the admission validator refuses execution. The earlier draft and all
consumed attempt evidence are preserved. No observation claim was created.

Before issuing an owner instruction, the coordinator must admit the new session,
confirm stable connected power and battery state, assign exclusive custody and
review timing. The custodian remains available for the owner's immediate boot2
reply. The new one-time identity-check budget, if approved for this fresh session,
uses the previously reviewed fixed identity/uptime/logger guard without a baseline
observer. It must establish a new boot and age below 400 seconds. Any failed check
ends that budget with no retry. The previous session's check is never reused.

On a passing timely check and actual owner facts, finalize and hash the new
custody/admission bytes, recheck exact enabled source and candidate closure, and
start the single guarded pre/read/post sequence promptly. Its maximum 130 seconds
plus the separately admitted 30-second seal must fit the original 600-second
logger lifetime; elapsed coordination time must be included. If the interval no
longer fits, defer the read. Preserve and review the result before native recovery.

## Owner wording for the coordinator to use only when ready

Keep power connected. When I say the session is ready, use the usual physical
boot2 selection for the already installed test kernel. As soon as its screen
appears, reply “boot2 started” and say whether the text is readable. Leave the
device untouched while the single storage read and log capture run. If the screen
shows an error or the device behaves unexpectedly, report exactly what you see
and wait for recovery instructions; do not restart it on your own.

This wording is prepared, not delivered as a request to boot. Any shutdown needed
before physical selection remains a separately coordinated action. The owning
[roadmap](../../../docs/ROADMAP.md) determines subsequent work order.
