# Common-clock cleanup generation result

The single assigned Git-only Buildbox run passed at exact project revision
`ebc146fa14da2120d1ba109626955879ba3b38c1`, freshly advertised by
`refs/heads/codex/infracfg-validation-results` on the authorized origin.
The [unsigned patch](../../../patches/proposals/0001-clk-mediatek-remove-provider-on-reset-registration-error.patch)
changes only reset-registration failure cleanup in `clk-mtk.c`: three added
lines and one removed line. It remains outside every selected series/profile.

The [execution receipt](results/generation-ebc146fa/execution.json) records exit
zero in 47.085 seconds under a 600-second outer timeout plus five-second forced
termination grace. No retry occurred. [Generation](results/generation-ebc146fa/generation.json)
records upstream `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, generated commit
`9493a56d44ee06a3cbbc253a827f99b0a07d072a` and exact replay tree
`422847a3f1a1328b85dc77b36024379641f041ad`. The complete corrected source SHA-256
matches the prepared derivation:
`01f33c475e9bbe6ffef504d8247acd618bd53cc563de42abef4ada96b8344646`.

[Strict checkpatch](results/generation-ebc146fa/checkpatch.txt) reports zero
errors, warnings and checks across 16 checked lines. Only the intentionally
missing DCO was exempted. Its stock “ready for submission” text is not project
approval: the author remains synthetic/non-certifying and actual attribution,
DCO, merge base, Fixes/stable routing and kernel validation remain unresolved.

The exact four-file remote package totals 2829 bytes. Each member was required
to be a regular file below 64 KiB; unexpected members refused. The remote
inventory was checked before transfer, then all local bytes, hashes and receipt
pins were checked. The [fetch record](results/generation-ebc146fa/fetch-validation.json)
pins all four original members, including the inventory itself. The patch is
1419 bytes, SHA-256
`eabc1a33c23b4511a285bb2660376585f4e8332f2bca124ffab606e308ee9a62`.
The original [SHA256SUMS](results/generation-ebc146fa/SHA256SUMS) is retained
unchanged: its patch basename maps to the linked proposal path; the other two
listed members remain beside the inventory. It is not a root-relative inventory.

[Post-run observations](results/generation-ebc146fa/post-run.json) record host
and backend free-space checks, absent source scratch and partial output, retained
recognized ownership marker, clean exact project checkout and successful normal
lock reacquisition/release. The bounded sparse Git checkout materialized one
driver source and three checker inputs, with parent-tree metadata for replay.
It was removed after generation; no Linux source was fetched to the host. Only
the small review package was fetched. The managed project Git checkout remains.

This is patch-generation, replay and style evidence. The six actual-C host
control-flow cases remain the previously reviewed [host result](host-fixtures.json),
not an in-kernel test. No compilation, schema test, QEMU run, device contact,
managed kernel source/build/package mutation or external submission occurred.
The coordinator reviews this handoff before selecting any next action.
