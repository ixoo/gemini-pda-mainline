# Negotiation session packet

State: `waiting-owner-physical-boot2`; root is the sole device custodian.

The [runtime protocol](RUNTIME_PROTOCOL.md) selects the exact validated
[candidate](results/candidate.json) and finite default/set/full negotiation.
[Deployment 1](results/deployment-1.json) records guarded installation, full
readback and clean shutdown. Capture and preservation/recovery preparation passed
against the real receipt. A fresh physical boot2 selection is now required.
Earlier default-query boot reports do not satisfy this new handoff. The consumed
default-query lifetime remains closed.

After a verified installation, the owner physically selects boot2 with console
and USB connected. Root then verifies live release and changed boot identity,
runs one admitted preparation/negotiation capture, preserves the complete sealed
log, performs the established A53 regression and reviewed native recovery, and
confirms changed-boot Gemian. Capture failure still requires preservation and
reviewed recovery; missing identity/evidence blocks dependent actions.

Success permits common-init preparation, not a working-Wi-Fi claim. Retire the
lifetime after every outcome; no identical retry is selected.
