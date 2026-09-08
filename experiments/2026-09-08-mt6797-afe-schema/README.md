# MT6797 AFE schema conversion draft

Implements the binding-only first topic from the
[upstream architecture review](../2026-09-07-mt6797-audio-upstream-architecture/README.md).
This is an unsigned experiment draft, not an upstream submission or a selected
kernel patch. The two proposed maintainer entries are inherited unchanged from
local patch 0064; their agreement is not established. Actual authorship, DCO
certification and maintainer willingness must be resolved before submission.
No sign-off is generated. The original text binding was introduced by Kai Chieh
Chuang in upstream commit `22d9f80904b4510296c133db15f8d3291292023b`.

The input schema preserves the legacy compatible, register aperture, interrupt,
AUDIO power domain and all eight ordered clocks. The example retains the public
text binding's resources, with one-cell address/size syntax in the schema's
example parent. Generation removes only `mt6797-afe-pcm.txt`; the separate
machine-card text binding, drivers, DTS, canonical series and profiles are
unchanged. There is no audio enablement or device operation.

## Reproduction

`validate-on-buildbox` runs from a clean, pushed project checkout on Buildbox.
It creates a disposable sparse checkout of upstream commit
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, already pinned by the manifest's
MT6797 upstream profiles. The legacy binding has the same SHA-256 as the
September 7 architecture review's newer source pin. This is validation against
the stated baseline, not a claim to have checked today's upstream HEAD.

The script uses the existing pinned `schema-2026.6` tool environment (see the
[tool lock](../2026-09-05-mt6797-infracfg-upstream-preparation/schema-tools-requirements.lock)).
It generates a normal one-change format-patch with a synthetic, non-certifying
experiment identity, checks exact replay against its real upstream parent,
checks clock names against the legacy binding, example, AFE array and ADDA DAPM
supply, runs strict checkpatch and focused `dt_binding_check`, including the
compiled example. Checkpatch excludes missing sign-off, file addition/deletion
notice and commit-message line length for this unsigned draft; no code/style
warnings are excluded.

Only the patch and validation evidence are returned from Buildbox. Temporary
upstream files are removed on exit. No kernel image or ASoC object build is
needed for this binding-only change. Hardware audio support remains untested.

The first validation attempt passed the eight-clock assertions and exact patch
replay, then stopped at checkpatch: the checker could not resolve the historical
commit named in the message. The message now credits the original
author and year, with the exact historical reference above. Replay uses
`write-tree --missing-ok` to avoid fetching unrelated sparse-tree blobs.
The second attempt passed checkpatch and compiled the example, but the log
reported a missing `jobserver` module during schema style checking despite
`make` returning zero. Its generated PASS text is superseded by this review;
that attempt is incomplete. The sparse checkout now includes upstream's
`tools/lib/python/`, and all three schema/lint/style completion markers are
required. A direct focused example validation must also produce no diagnostics.
Full schema validation is pending.
