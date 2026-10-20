# Separate read-only diagnostic

Status: inconclusive; one bounded attempt consumed.

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
shutdown. Host preparation passed against the real deployment receipt. The
single diagnostic boot is recorded below.

The diagnostic refused its first acquisition gate, accepting no data. Evidence
was completely sealed and read back before the one reviewed restart request.
The SSH disconnect was not confirmed before the host bound; a separate bounded
read-only check confirmed a changed known-good Gemian boot. No restart or
collection retry was issued. Mechanism and raw observations remain private.
This result adds no demonstrated Wi-Fi capability.

| Run | Boot ID | Collection | Preservation | Return |
| --- | --- | --- | --- | --- |
| R1 | `71d4e5d2-c69f-40e5-90fb-9df865fdc263` | Initial gate refusal; zero accepted data | Complete sealed log, verified readback | Changed-ID Gemian confirmed; request transport unconfirmed |

The [sanitized scalars](r1-scalars.json) separate the diagnostic refusal, evidence
retention and return verdicts. No new collection candidate is selected.
