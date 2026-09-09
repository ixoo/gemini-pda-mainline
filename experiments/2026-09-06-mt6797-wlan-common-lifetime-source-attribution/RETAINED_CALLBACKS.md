# Retained callback and late-registration follow-up

The 2026-09-09 binary audit confirms the earlier source counterexample in the
retained kernel: late registration is not a reliable cleanup or error boundary.
This narrows the [VCN33 wrapper investigation](../2026-09-08-mt6351-mfd-upstream-preparation/VCN33.md#retained-hif-wrapper-follow-up).
It does not prove a rail leak, a reached race, or current-device execution.

The [receipt](retained-callbacks.json) pins the retained Image, reconstructed
ELF, four analyzed regions and decoded offsets. The entire ELF kernel section
matches the Image. Private disassembly remains in the RE VM. The three source
files read from Gemian commit `8cfe6596a503612e3332d9c26e292a19525a7f07`
match the original Planet-source audit's whole-file hashes exactly. This is a
later, separately scoped audit; the original frozen inputs and verdicts remain
unchanged. Matching source files do not attest the whole source build.

## Compiled control flow

- `HifAhbPltmProbe` constructs the actual HIF probe/remove callback values and
  passes them to common registration. The registration body copies the values
  into its global object; it does not retain the stack object's address.
- The common object's probe and remove slots are at offsets 48 and 56. Its
  pending flag is at offset 80. The SoC branch of `wmt_func_wifi_on` sets that
  flag and returns -2 when the probe callback is absent. A callback error on
  its ordinary path instead returns -1 without invoking remove in this body.
- System-state reset requests two 24-byte zero fills at offsets 0 and 24.
  Neither fill includes the callback slots or the pending flag. Those requests
  cannot serve as a reset of the pending callback request.
- When registration sees a pending request, it invokes the copied probe.
  Success clears the pending flag. Failure returns -2 without clearing it or
  calling a second callback or common-power operation in the decoded body.
- After registration returns, `HifAhbPltmProbe` explicitly sets its own return
  value to zero. A platform-probe success is therefore not evidence that the
  pending WLAN probe succeeded or that its power request was balanced.

Together with the earlier HIF wrapper result, the late caller supplies no
local compensating PALDO disable. The callback's internals, higher-level caller
unwind and actual power effects remain outside this audit. No live PMIC or
radio operation was performed, and no current boot was inferred from the image.

## Integration consequence

Do not use platform registration success or cleared subsystem state as a
WLAN-ready or common-resource-ownership witness. A mainline provider must own
its enable/disable and failure paths explicitly; the retained callback scheme
cannot supply that guarantee. The first hardware integration still needs the
shared CONSYS/EMI/AP-DMA contract and an attributable recovery protocol. The
original cleanup verdict remains unresolved at that full-system scope.

Validation checked the Image/ELF identities, symbol entry addresses, bounded
instruction ranges, key call/store encodings and source-file digests. The
original experiment verifier still checks only its frozen source audit, not
this new binary control-flow interpretation. No kernel build was required.
