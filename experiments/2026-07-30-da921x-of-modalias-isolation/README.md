# DA921x OF-modalias isolation

| Field | Value |
| --- | --- |
| ID | `2026-07-30-da921x-of-modalias-isolation` |
| Device | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Does the real `dlg,da9214-legacy` OF modalias uevent cause the
pre-serviceability reset?

The candidate preserves the exact real-compatible OF child, its resources,
the module-free initramfs, and the no-A72 serviceability baseline. One
experiment-only I2C-core branch omits only the OF modalias contribution for
that compatible and falls through to the already-exonerated I2C modalias.

## Decision

- Serviceability with the real OF node and I2C-only modalias implicates OF
  modalias generation or emission.
- Another reset after the suppression marker places the failure earlier in
  the real-compatible OF-node instantiation path.
- Absence of the exact config, binary branch, real OF child, or module-free
  initramfs invalidates the candidate.

## Safety

The option adds no driver or transfer path. The DA921x driver remains
module-only and its module and loader are absent from the initramfs. CPUs 8
and 9 remain offline. Runtime acceptance requires an unbound `0x68` client,
the real OF node, the I2C-only modalias, zero I2C/oracle counters, and the
complete existing serviceability baseline. No device partition is accessed
by the candidate.

## Status

Kernel patch, focused profile, candidate construction, and offline validation
are in progress. No device boot is authorized until the exact artifact,
hypothesis, unique evidence, and decision branches are pinned.

The experiment patch has actual author metadata but no DCO sign-off. It is an
experiment-only diagnostic and is not submission-ready.
