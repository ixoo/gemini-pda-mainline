# Experiment: passive dynamic reserved-memory binding

This successor extends the accepted passive image-owner snapshot with a
bounded no-`reg` path for Linux's initialized `reserved_mem` record. It does
not reserve memory, prove `no-map`, claim overlap ownership, map/copy bytes,
invoke a region callback, initialize a device, or enter the active path.

The static `reg` path remains intact. Dynamic nodes require equal one- or
two-cell address/size widths, a present nonzero `size` matching the record,
optional valid `alignment`, and containment in at least one declared
`alloc-ranges` choice. Raw declaration bytes, property presence and widths are
revalidated, so a declaration mutation with an unchanged extent is stale.
The retained snapshot owns immutable declaration copies; revalidation compares
current borrowed views while the caller holds configuration stable. `ops` and
`priv` must remain NULL; references are balanced.

Inputs and pinned Linux/schema identities are in [inputs.json](inputs.json)
and [public-sources.json](public-sources.json). The generated successor delta
is [0006-wifi-mediatek-describe-dynamic-reserved-memory.patch](0006-wifi-mediatek-describe-dynamic-reserved-memory.patch).
The host suite includes the predecessor's 52 binding and 32 concurrency
regressions plus 72 dynamic/reserved checks. No device, Buildbox compile, or
hardware claim is made.

Run `python3 scripts/verify.py` from the repository root. The compile inputs
for the required real kernel object build are packaged by the patch but that
build remains pending; this experiment is review-ready as an offline,
synthetic, non-submission archive.
