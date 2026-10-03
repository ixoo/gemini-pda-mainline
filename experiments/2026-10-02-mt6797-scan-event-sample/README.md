# Cached receive event masks: incomplete source checkpoint

Status: unfinished source diagnostic, published as a checkpoint only.
No build profile, candidate, deployment or hardware lifetime is admitted.
Parked by the [2026-10-03 Wi-Fi audit](../2026-10-03-mt6797-wifi-audit/README.md)
until the missing WMT common power-on has been tested.

The consumed [pool experiment](../2026-10-02-mt6797-scan-pool-sample/README.md)
found its selected receive pool available twice, with zero reception and no BSS.
Its [receive-event analysis](../2026-10-02-mt6797-scan-pool-sample/results/receive-event-admission-analysis.json)
identifies ordinary-RAM copies of raw pending and enable masks before the
selected bit-3 native receive dispatch. Those copies may be stale.

[Proposal 0085](../../patches/proposals/0085-wifi-mediatek-sample-scan-receive-events.patch)
retargets proposal 0084's default-off sampler to pending at `0xf007e28c` and
enable at `0xf007e2a0`. It preserves the four-query, one-outstanding-request,
100 ms response deadlines and existing scan retirement. No additional query,
MMIO access, firmware write, active probe or operational lifecycle change is
introduced. Separate samples cannot prove an atomic mask/pending state,
continuous receive activity or RF packet counts.

Cached enable clear would prioritize initialization/mask ownership; enabled
with pending clear would prioritize pending/descriptor production; pending
bit 3 observed would prioritize dispatch/lookup/scheduling. These are limited
source hypotheses, not conclusions about live hardware registers.

The [source checkpoint](results/source-checkpoint.json) pins the patch and
resulting files. Focused wire tests, lifecycle reverse normalization and strict
style checks passed. The archive has a synthetic, non-certifying author and no
DCO sign-off; it is not ready for upstream submission.

Remaining work includes classifier and fixture coverage, profile/canonical
series admission, runtime tooling, a clean pushed Buildbox compile, package and
candidate validation, guarded boot2 deployment and one owner-selected boot.
No kernel build or device test was performed for this checkpoint. Mainline
reception, association and working traffic remain unproved. Do not use this
proposal as a boot candidate or repeat consumed parent lifetimes.
