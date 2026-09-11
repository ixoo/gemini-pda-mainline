# Export recovery: physical-key prerequisite

The export filesystem parks PID1 after success or refusal. USB cannot therefore
be its only recovery transport: a failure before enumeration would leave no
command channel. The prerequisite is one owner-controlled Esc-key restart
on known-good Gemian, before deploying the export image, with confirmation
under [safety policy](../../docs/SAFETY.md). The owner-reported check and
subsequent authenticated return are recorded below; the proposed procedure
remains for provenance, not a request to repeat it.

## Evidence and limits

Planet's [Gemini user guide](https://support.planetcom.co.uk/download/GeminiPDAUserGuide.pdf#page=226),
printed page 225, describes holding Esc (power) for ten seconds to restart
unresponsive Android or Linux. The separate two-button fallback is not part of
this proposed check. The [boot configuration guide](https://support.planetcom.co.uk/index.php/Configuration)
also explains that held buttons select a boot target when the screen turns on;
release Esc at the first restart indication to avoid selecting recovery mode.

The selected kernel's [binary/source receipt](results/export-key-recovery.json)
confirms the same one-key policy as the
[retained Gemian audit](../2026-09-08-mt6351-keys-preparation/RESET_BINARY.md):
normal/other modes request power-reset enable 1, home-reset enable 0 and duration
selector 1. The source timing table describes selector 1 as eleven seconds;
neither that table nor the manufacturer's approximate duration is a measurement
on this device. Factory modes disable both reset enables.

The actual linked keypad probe calls this helper after successful IRQ setup.
The helper ignores PMIC setter failures, so its presence does not prove successful
configuration. The PMIC power-key handler does not call the keypad AEE handler;
the latter's inspected input selection accepts volume-up/down keys. No volume,
side-button, debug-register or key-injection operation is selected.

A successful check on current Gemian would establish a physical recovery
prerequisite on that boot, not prove the new kernel's probe or reset state.
The eventual export session must still demonstrate its own changed-boot return.

## Proposed single check

1. Obtain owner confirmation for one forced restart and ask them to save open
   work. Preserve outstanding experiment evidence. Recheck authenticated Gemian
   identity, boot UUID and ordinary system state; stop on a mismatch.
2. With the owner present, flush pending filesystem writes once and record the
   pre-restart UUID. This reduces pending-write exposure; it does not turn a
   forced reset into an orderly shutdown. Start bounded observation of the
   known-good LAN endpoint; do not change USB, services or boot partitions.
3. Ask the owner to hold only Esc until the first vibration/restart indication,
   then release immediately. Limit this single hold to twelve seconds. If no
   response occurs, release and stop: no longer hold, alternate buttons or retry.
4. Record the owner's observed response. Wait up to three minutes for Gemian
   and require an authenticated changed UUID, expected OS/model/kernel and
   normal userspace before recording a successful return. Loss of SSH alone is
   not evidence of reset. A timeout ends observation, not permission for another
   restart; preserve available evidence and ask the owner about the screen.

No response rejects this recovery prerequisite. A restart without attributable
Gemian return is inconclusive and blocks export deployment. A pass permits
preparation of the export session's physical recovery procedure, while its
own boot, USB preservation and failure-recovery results remain outstanding.
This packet authorizes no automatic restart, deployment, radio operation or
capture clearing.

## Attended result

The owner reported using Esc to force a restart and clarified that it occurred
before the Gemian startup subsequently verified over authenticated LAN SSH.
The returned boot was `9ed3b455-0e52-45e1-9812-c8895dbb1b95`, different from
the preceding `f2b923f9-f952-4cdb-80e0-72142282cc4f`, with the expected
MT6797X model, Linux 3.18.41+ aarch64, Debian 9 and running systemd.
This is an owner-observed physical action plus an authenticated return, not an
instrumented reset-timing measurement.

Chronology matters: the owner first requested a clean shutdown, which was sent
on the preceding boot. The later three-minute monitor began after the returned
boot had already been authenticated; it saw that same healthy boot throughout.
The owner clarified the Esc action preceded that startup, so the later monitor
is not a second reset result. No hold duration or specific vibration timing was
reported. No repeat was requested after that clarification.

This satisfies the physical-key prerequisite for preparing the export session.
It does not prove the candidate kernel's keypad initialization, recovery after
export failure, or boot2 installation. Those remain separate checks.
