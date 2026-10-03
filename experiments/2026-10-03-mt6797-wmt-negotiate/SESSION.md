# Negotiation session packet

State: `offline-prepared-deployment-pending`; root is the sole device custodian.

The [runtime protocol](RUNTIME_PROTOCOL.md) selects the exact validated
[candidate](results/candidate.json) and finite default/set/full negotiation.
No new physical boot is requested until guarded installation, full readback and
clean shutdown are recorded. Earlier default-query boot reports do not satisfy
this new handoff. Its consumed lifetime remains closed.

After a verified installation, the owner physically selects boot2 with console
and USB connected. Root then verifies live release and changed boot identity,
runs one admitted preparation/negotiation capture, preserves the complete sealed
log, performs the established A53 regression and reviewed native recovery, and
confirms changed-boot Gemian. Capture failure still requires preservation and
reviewed recovery; missing identity/evidence blocks dependent actions.

Success permits common-init preparation, not a working-Wi-Fi claim. Retire the
lifetime after every outcome; no identical retry is selected.
