# Pre-admission live refusal — 2026-09-06

## Observation

At 2026-09-06 18:16 UTC the integration custodian invoked the independently
accepted one-SSH runner against a new ignored attempt directory and the private
admission for the previously confirmed Gemian boot. The runner returned its
fixed `identity or authenticated SSH refusal` classification before the remote
`admission_ready=yes` barrier.

The mode-0700 attempt directory exists and contains no files: there is no
`consumed` marker, raw stream, digest token or result record. Therefore no
container mount or selected-file read was admitted and the one-read observation
budget was not consumed. The collector made no retry.

## Classification and next discriminator

This is an unconsumed pre-admission refusal, not a Wi-Fi identity result. It
does not distinguish endpoint reachability, authentication refusal, changed
release/architecture/boot identity or failure before the remote barrier,
because the privacy boundary intentionally does not retain or print the raw
pre-admission stream.

Do not retry automatically. First re-establish the live known-good OS and the
appropriate transport with the owner, then create and review a fresh admission
if the boot identity changed. A future admitted run retains the same narrow
identity-only conclusions and grants no radio, firmware, reboot or boot2
authority.

## Effects

- One bounded SSH process was attempted.
- No remote mount/file read was admitted.
- No sudo, namespace entry, radio action, write, service action, reboot or
  partition access occurred.
- No private value or device identifier is recorded here.
