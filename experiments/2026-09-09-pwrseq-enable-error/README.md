# Power-sequencing enable error: existing upstream fix

The error-masking defect recorded in the [provider ownership review](../2026-09-05-mt6797-wifi-contract/PROVIDER_OWNERSHIP.md)
already has an upstream fix proposal by the subsystem maintainer. Follow that
series; no independent project kernel patch or new build profile is needed.
This removes duplicate upstream-preparation work, not the CONN ownership gate.

Bartosz Golaszewski posted [patch 1/2](https://lore.kernel.org/all/20260903-pwrseq-kunit-v1-1-1f893d2cabc2@oss.qualcomm.com/)
on 2026-09-03. Its two-line change returns a failed unit-enable result before
calling the target's post-enable callback. The [readable message mirror](https://lkml.iu.edu/2609.0/08042.html)
provided the inspected diff; direct Lore retrieval returned HTTP 403 during
this audit. Preserve the original author's actual metadata when acquiring the
series for integration; do not reconstruct a sign-off from obfuscated email.

The [companion KUnit proposal](https://lkml.iu.edu/2609.0/08170.html)
contains `pwrseq_enable_enable_error`: a failing dependency must return `-EIO`,
leave the target unenabled, and never invoke post-enable. Its
`pwrseq_enable_post_enable` test covers successful enable and post-enable
failure rollback. These tests were inspected, not executed in this audit.

## Source and focused validation

The defect remains in the inspected upstream master snapshot
`893e11787f78e43b534e252249ac3fff4d1333f8`. Its
[`drivers/power/sequencing/core.c`](https://github.com/torvalds/linux/blob/893e11787f78e43b534e252249ac3fff4d1333f8/drivers/power/sequencing/core.c)
has SHA-256 `da3430b177c2d2a73f5c5e4ff4949535e233dcef1960f14fe8b716c8d460d681`.
A posted patch is not evidence of merge or release. This snapshot is an
inspection input only; the kernel manifest remains unchanged.

The existing Buildbox source at pinned upstream
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c` has core-file SHA-256
`86fe4cb3e77f1eeece1bd065ba7378bb5892499f344fb9de8af1761e449eda78`.
The upstream diff applies cleanly to that file. The resulting file is
`9aaf179284012912717502adb895b50793c9b55138cbd88bfb9f33f54072b346`.
The HTML-decoded diff, from `diff --git` through the final context line with
one trailing newline and without the mail signature, hashes to
`99858e2053802748792c5859025ab38e6b573df6855dea20b0ec3b7d88d06826`.

[The focused check](test-enable.py) compiles the actual `pwrseq_enable` body
with injected unit/post callbacks. Nine cases cover a null descriptor,
already-on and unregistered paths, unit failure with absent/successful/failing
post callback, and successful unit enable with those three callback outcomes.
The unpatched source fails exactly the two unit-error cases with a callback;
the upstream diff passes all nine. The check substitutes lexical no-op guards:
it proves the tested sequential result/callback behavior, not mutex, rwsem,
dependency unwinding, provider lifetime or concurrent consumer correctness.

```sh
python3 experiments/2026-09-09-pwrseq-enable-error/test-enable.py /path/to/unpatched/linux --expect-bug
python3 experiments/2026-09-09-pwrseq-enable-error/test-enable.py /path/to/upstream-patched/linux
```

Both checks ran on Buildbox with warnings treated as errors. Temporary copies
were confined to one core file and removed afterward; no prepared tree was
modified. There was no kernel build, KUnit run, device access or hardware action.

## Remaining boundary

The fix preserves the primary enable error. It does not fix ignored dependency
rollback errors, ignored disable errors in descriptor release, or the permanent
provider/resource retention required after uncertain CONN transitions. It does
not make a consumer-owned sequencer an adequate CONN power owner. Recheck the
upstream series and selected baseline before any future pwrseq adoption; do not
start another implementation of this exact fix. No upstream message was sent.
