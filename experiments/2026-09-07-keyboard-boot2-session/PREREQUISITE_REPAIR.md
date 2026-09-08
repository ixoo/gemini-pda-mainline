# Keyboard prerequisite repair handoff

The current handoff is bound to Candidate R's raw image
`3290b867bc6cb2ecee42e6ca1436e1ae29613c074e7e45b3836ecb2905f3e07c`, padded
boot2 image `29f59c7f21a25b47d63d653857db9d7d0760d9a00f7193e098219699235f16f1`,
and manifest `62440fdee9267e26d6f90148609a7c2551fdb9d6a9f603da03f891638c65180d`.
Its fresh baseline admission is `d10dcd8b-d67e-4311-ab7e-3f8c3078a88e`, with
the reviewed supplemental chain `1eae36...`, `947681...`, `31206d...`,
`33367f...`, and `74c1be...`; historical old-candidate records remain
chronology only.

The new tracked `disconnect-execution-binding.json` has the exact three-key
schema and is currently `state=disabled` with `admission=null`. The generic
gate validates an enabled binding against the complete admission and returns
its binding digest for the local claim, but this edit does not enable execution.

The readiness audit's hash-only admission defect is repaired in source. The
capture path now invokes a bounded semantic verifier before any local claim or
network transport. It opens the fixed accepted duration receipt plus three
mode-0600 session receipts below the ignored private evidence root and rejects
missing, altered, failed, inconclusive or cross-session inputs.

The verifier binds the duration lifecycle to the unchanged monitor source. It
binds runtime metadata to the exact boot, candidate, event identity,
capabilities, resource ancestry, map, logger age and console state. It binds
custody to the exact session and requires stable power, owner readiness and
continuous reader exclusion. It binds the disconnect result to the candidate's
exact Dropbear and administration shell, the enabled monitor package/revision,
one retained claim, deliberate no-PTY transport loss, terminal/reaped monitor
and child, an independent complete export, and complete absence of surviving
monitor, observer, tty1 or input readers.

Mutation fixtures reject failed classifications, wrong digests and every
decision-critical disconnect boolean. The tracked execution binding is
disabled/null, so this source repair admits no device action.

An explicit `keyboard-monitor-enabled` Buildbox kind is also prepared. It
produces two byte-identical static ARM64 monitor replicas with
`production_entry=enabled-admission-v1`, plus a byte-identical harmless bounded
disconnect probe compiled from the same lifecycle engine. The probe contains a
built-in child and cannot open evdev or a VT; it is intended only to measure the
exact candidate Dropbear/session disconnect and independent preservation path.
Neither binary had been built at the initial source checkpoint. The subsequent
[enabled Buildbox result](results/enabled-build/RESULT.md) froze both binaries
without changing the monitor engine.

The remaining blocker is final session admission: create a future
boot-specific enabled binding, run and independently review one exact
Candidate R disconnect proof, and obtain final Astra acceptance of the exact
enabled hash. Fresh runtime and custody receipts remain required before
capture. The baseline kernel/DT/config and the 20-case/25-keycode protocol are
unchanged; no kernel build is justified and execution remains NO-GO.

Focused host validation passed:

- three prerequisite-verifier mutation tests;
- six capture/refusal tests;
- six Buildbox routing tests covering the new explicit kind;
- twelve monitor lifecycle tests and native enabled/probe compilation;
- 26 packet/classifier tests, three delivery tests and thirteen duration-proof
  tests;
- protocol rendering, Python compilation, shell syntax, ShellCheck and
  whitespace checks.

This is an offline source handoff only. It is not a disconnect result, a
keyboard observation, a device admission or authorization to enable the
binding.

## Specialist rejection and bounded repair

The first Astra session-safety review rejected the initial verifier because its
positive fixture allowed every preserved disconnect member to be null and the
code trusted terminal/reap/reader summary booleans. The corrected verifier now
requires seven mode-0600 raw evidence files, binds every digest, requires all
four retained monitor members, parses the monitor lifecycle and outer exit, and
parses the deliberate-disconnect, independent-export and bounded reader-scan
process records. Rehashed contradictory evidence is rejected rather than merely
detecting an unchanged receipt digest.

After a second timing-order counterexample and repair, Astra accepted the frozen
offline lifecycle-verifier contract. That acceptance does not change physical
session admission. The original rejection, both repair rounds and exact accepted
source hashes remain preserved in
[`ASTRA_SESSION_REVIEW.md`](ASTRA_SESSION_REVIEW.md).
