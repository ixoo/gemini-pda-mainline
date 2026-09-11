# Second export session: attributable startup failure

Status: attempt consumed, with no attributed USB terminal or recovered startup
marker; see the [installation and recovery result](EXPORT_ATTEMPT_2.md).
The procedure below records the contract for
`wifi-export-container-20260911-bootstrap1`, identified by the
[validation receipt](results/bootstrap-container-1.json). Neither this image nor
the [first image](EXPORT_ATTEMPT_1.md) may be repeated unchanged.

## Hypothesis and decision-changing evidence

The [bootstrap diagnostics](BOOTSTRAP_DIAGNOSTICS.md) can identify a reached
shell/Python stage through the existing native kernel log and retained console,
including when the USB export fails. The original one-frame export remains an
independent observation. This adds a logging path before USB setup; it changes
no kernel, DT, CPU, firmware, calibration, capture or USB-control policy.

The filesystem differs in exactly `/init`, startup, the device export bridge
and the newly generated session manifest. All 723 members remain present,
and all other contents and metadata match the first filesystem. Two separate
filesystem assemblies produced identical complete five-file packages; repeated
container construction also matched. The retained-loader fields, padding,
payload ID and split capture reservations passed independent checks. The image
fits the exact 16 MiB partition. These are composition checks, not boot proof.

## Deployment and collection

The padded image SHA-256 is
`a0661c7a0a02cf690516cc026ee07209eb14e815bc3ef939f18a8de684bc95dd`.
Bind the checksum-covered private filesystem/session and generated installer
to that image and the preceding authenticated Gemian UUID. The prepared
installer expects `302aaa99-de4b-4e25-88b1-feba649c2126`; a changed boot requires
fresh inspection and rederivation before installation. The existing guarded
live-GPT boot2 procedure, stable power, predecessor check, complete readback,
private staging cleanup and clean shutdown still apply. Its new evidence
directory is `wifi-export-deployment-2`; never overwrite the first receipt.

Prepare the same [bounded export receiver](CAPTURE_EXPORT.md) with this session's
exact private digest and the preceding Gemian UUID. The host wrapper differs
only in those two identities. Keep the left-port data cable connected. Gemian
USB enumeration is not a prerequisite: its administration path is LAN SSH.
Record a fresh host inventory and arm collection when the owner is ready for
physical selection. Request one boot2 selection only after verified installation
and shutdown. A boot logo remains an ambiguous observation.

As in the [first session contract](EXPORT_SESSION.md#host-preparation-and-one-request),
require one new expected USB parent and its unambiguous ACM child before opening
a terminal. Observe enumeration for at most 180 seconds; after attribution run
one receiver with its existing 60-second exchange deadline. No wildcard terminal
probe, second request, USB reconfiguration or timeout extension is selected.
If physical selection has not occurred before the host window expires, record
that separately; an expired host watch is not evidence that a kernel failed.

## Prompt, owner-controlled recovery

Preserve host output and any received snapshot before recovery. Once the
observation ends, obtain the owner's confirmation for the reviewed
[Esc-key procedure](EXPORT_RECOVERY.md#proposed-single-check). Ask for only
Esc, release at the first restart indication, and stop after at most twelve
seconds without a retry. Do not substitute power-off or alternate buttons.
The earlier owner's powered-off return did not establish preservation of RAM
through a controlled reset; it also does not prove power-off caused the missing
startup evidence. A timeout never authorizes a restart.

After the owner reports that action, watch the known-good LAN endpoint for at
most three minutes. Require authenticated Gemian, MT6797X, Linux 3.18.41+
aarch64, Debian 9, running systemd and a changed boot UUID. Preserve
`console-ramoops` promptly, without clearing it, in one private bounded read of
at most 65,536 bytes, with the same return UUID verified before and after.
A missing, oversized, unreadable or boot-mismatched record is inconclusive.
Do not retry recovery to improve the result. Inspect retained bytes in the RE VM.

## Classification

- A valid one-frame receipt with the selected session, a changed candidate boot
  UUID and exactly 65,536 preserved bytes establishes the same bounded export
  result as before. Preserve the complete checksum-covered snapshot privately.
- Recovered `wifi-bootstrap-v1` records with one nonzero candidate boot UUID,
  different from both preceding and returned Gemian, identify reached stages.
  If USB supplied a UUID it must agree. Join the records to this sole installed
  candidate and the owner's selection/recovery chronology; markers alone are
  not cryptographic image attestation.
- A `stopped` record selects its exact failing stage for diagnosis. The next
  operation named by a progress record is not thereby proven complete. A last
  progress record without a stop is only a lower bound on execution.
- Missing markers, USB failure or a logo alone remain inconclusive. Record the
  observation and recovery outcome; do not repeat this candidate unchanged.

Successful preservation does not admit capture clearing, a WLAN cycle or a
broader hardware-support claim. Recovery, export and diagnostic observations
remain separate results even when collected from this one session.
