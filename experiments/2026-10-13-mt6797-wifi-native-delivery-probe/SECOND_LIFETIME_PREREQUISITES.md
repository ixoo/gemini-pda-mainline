# Second protected lifetime: offline prerequisites

P2E-D2 closes the 600-second received-traffic gate and exercises teardown.
[Its separate verdicts](SESSION_0202_PLAN.md#p2e-d2-consumed--600-second-gate-pass-delivery-transmitted-cleanup-pass)
do not admit another P2E boot or a second protected lifetime. The next device
item is an owner decision. This plan needs no firmware command extension,
additional sampler, kernel rebuild or device action.

Before enabling re-arm, review the existing
[key-retirement source analysis](KEY_RETIREMENT_SOURCE_REVIEW.md) and
[lifecycle design](../2026-10-07-mt6797-wifi-phase-b-join/REUSABLE_LIFECYCLE_DESIGN.md)
against the selected source and pinned mac80211 callbacks. Resolve these four
ownership questions with focused offline fixtures before preparing a candidate:

| Prerequisite | Required proof before reuse | Refusal / fixture |
| --- | --- | --- |
| Key retirement | Establish which credited removal and station-teardown boundary retires each installed key and its queued data. Command credit alone is insufficient. Keep the old lifetime closed until this barrier is supported. | Delayed/failed removal, retained debt or missing station teardown must prevent re-arm. |
| Stale completion ownership | Identify every completion by its live owner. Where firmware carries no generation, prove an old transaction cannot match a new pending operation before identifier reuse. A host generation counter alone cannot label an untagged firmware event. | Inject old TX and key completions before, during and after a proposed new installation; no stale event may publish success, return credit twice or retire a new owner. |
| PN contexts per generation | Keep PTK and GTK receive replay contexts separate and bound to the actual key identity, key index, peer and lifetime generation. Retire the old context only at the proven barrier; a new key gets a distinct context. | Old-generation RX, mixed key indices, equal/lower PN and interleaved completion/RX must fail closed. No replay floor reset merely because stage 3 returned credits. |
| Queued management ownership | Removal commands visibly release queued management-class frames: status 0 means transmitted, status 5 means flushed. Account for the reserved frame and its late status before identifier reuse. | A queued reserved management frame is not by itself a surviving-ownership risk after that release. This observation says nothing about queued data frames or their key ownership. |

The smallest implementation should keep admission closed until all applicable
barriers have evidence, preserve the existing one-lifetime behavior and refuse
ambiguity. Do not change the teardown chain or infer a generic flush guarantee
from management completions. First review the concrete source boundary; only
then decide whether a code change is justified. Reconnect, rekey, AP-off loss
validation and maintained support remain separate acceptance work.
