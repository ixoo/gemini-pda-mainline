# Design: restore READY for the P30E production configuration

## Hypothesis

The first P30E device attempt did not enter the admission core because the
MT6797 production profile still embedded config-input identity `5968c24f...`,
while the package-exact provenance record supplied `1e7f3047...` after the
P30E wire option joined the selected configuration. Updating only that static
production identity will allow the otherwise unchanged arm64 plan to publish
READY and permit the existing one-shot CPU8 path to reach P30E.

## Unique evidence

The consumed attempt booted exact padded candidate `a4ad4915...` and reported
verified runtime provenance, but the same-boot kernel log recorded profile
proof mask `0x40000`. Its one trigger returned `-EAGAIN` with core consumption,
CPU requests, and every P30E field still zero. The controller source has only
one such pre-consumption `-EAGAIN`: an absent READY token.

## Change and safety boundary

Patch `0456` changes only the production `mt6797_a72_config_input_identity`
constant to the package-derived `config-inputs-sha256` value. The fixture
identity and all admission, power, CPU request, retry, CPU_OFF, storage, and
device-action code remain unchanged. The successor retains exactly one CPU8
trigger and the CPU9 veto.

## Decision

- READY published: continue with one exact P30E CPU8 attempt.
- Any profile blocker: stop before the trigger and repair the attributable
  identity or plan failure.
- ARMED/EMPTY, CLAIMED, or PUBLISHED after the request: use the existing P30E
  decision map; do not repeat an identical candidate.
