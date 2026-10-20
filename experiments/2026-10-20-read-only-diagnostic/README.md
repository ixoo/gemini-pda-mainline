# Separate read-only diagnostic

Status: awaiting owner boot2 selection.

This experiment prepares one sanitized private read-only diagnostic on its own
candidate and boot. It is separate from the
[Wi-Fi lifetime tests](../2026-10-13-mt6797-wifi-native-delivery-probe/RESUME_CHECKPOINT.md).
Mechanism, inputs and collected data remain private.

The question is whether the admitted diagnostic completes its bounded collection.
A complete result, a partial result with an exact stop point, a diagnostic refusal
and a host or retention failure are distinct outcomes. There is no retry within
the boot. This test does not measure Wi-Fi connectivity.

The gates are a validated Buildbox package, focused host and actual-source
fixtures, guarded inactive-boot2 installation with full-partition readback, fresh
boot identity, bounded capture, sealed evidence and the reviewed return path.
Physical boot2 selection remains the owner's action.

Preparation passed: the private candidate was built and validated on Buildbox;
focused Linux process and decoder tests and the actual-source log bridge passed.
The guarded boot2 write completed with matching full-partition readback and clean
shutdown. Host preparation passed against the real deployment receipt. No
diagnostic boot or runtime result has occurred. The next action is physical
boot2 selection with USB connected to the test host.
