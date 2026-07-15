# Review action plan for the 74-patch series

This is the current-series delta over the [72-patch review plan](review-action-plan-current-72-20260714.md).
It is a submission checklist, not a functional or hardware-support claim.

## Current evidence

- Checkpatch: [current 74 result](checkpatch-current-74-20260714.txt), 10
  errors, 60 warnings, and 11 checks; the output is byte-identical on a
  second VM run.
- Metadata: [current 74 provenance result](patch-provenance-current-74-20260714.txt),
  with 18 placeholder-author patches, 8 placeholder object IDs, and 10
  patches without a Signed-off-by footer.
- Static source compile: [current 74 W=1/sparse result](series-static-compile-current-74-20260714.txt),
  all 23 targets pass, including `drivers/spi`, after a warm rerun.

## New blockers introduced by patches 0072–0073

1. `0072-spi-mediatek-add-MT6797-compatible-alias.patch` has no truthful
   `Signed-off-by:` footer and combines a binding-related change with driver
   data. Split the binding portion before submission and obtain the actual
   author's DCO sign-off.
2. `0073-arm64-dts-mediatek-mt6797-add-disabled-SPI-controllers.patch` has no
   truthful `Signed-off-by:` footer. Obtain it from the actual author; do not
   add a maintainer's signature on another person's behalf.

The prior 32 provenance-blocking patches remain unchanged. No source or
hardware behavior is promoted by this audit.

## Exit criteria

Re-export all affected patches from real authoring commits, split bindings from
implementation where required, rerun checkpatch/provenance/schema/W=1/sparse,
and keep runtime support claims tied to named-device evidence.
