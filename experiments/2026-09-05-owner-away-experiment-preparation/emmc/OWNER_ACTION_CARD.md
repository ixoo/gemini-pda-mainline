# Owner action card — for coordinator delivery

This historical card is superseded by the [completed session outcome](INTEGRATED_SESSION_OUTCOME.md).
The device returned to Gemian; this card requests no new selection.

Coordinator update: the owner subsequently reported “boot2 started”. Physical
selection is confirmed; external-power continuity and readable mainline text
remain unconfirmed. The custodian has prepared the matching selection-confirmed
admission variant without consuming an identity or storage-read claim. The
wording and receipts below describe the completed preselection handoff, not a
request to select again. Fresh live timing gates still apply before execution;
elapsed waiting never supplies the missing confirmation or renews the logger.

Gemian's clean shutdown request succeeded and two bounded connection checks
observed it unreachable. The retained candidate is already installed; no new
partition write is needed. Pstore evidence was preserved privately and left
uncleared. See [PRESELECTION_SHUTDOWN.json](PRESELECTION_SHUTDOWN.json).

Prepared wording; this file does not itself request physical selection:

> Keep external power connected and use your usual physical boot2 selection.
> As soon as the screen appears, reply “boot2 started” and say whether the text
> is readable. Leave the device untouched while we perform one bounded storage
> read and preserve its log. If anything looks wrong or the device becomes
> unexpectedly hot, report it and wait for recovery instructions.

The A53 test task retains sole custody. Planned admission fields are prepared;
physical selection and power continuity remain false until the actual owner
reply. No mainline identity connection or read runs before coordinator admission.
A successful read still requires separately admitted log preservation and later
recovery review. No test or reboot follows automatically.
