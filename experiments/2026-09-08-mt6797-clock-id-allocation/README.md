# MT6797 clock provider allocation

Status: compile and focused regression passed, 2026-09-08; current upstream
submission preparation refreshed, 2026-09-12. The
[review packet](SUBMISSION.md) records current source matches, both introducing
commits, public overlap and prepared commit text. Human review and truthful
certification remain required. This is not a boot candidate.

## Problem and fix

At upstream commit `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, the
IMG, MM, VDEC and VENC bindings assign clocks starting at ID 1. The common
probe allocates one slot per registered clock, leaving the highest ID outside
its `hws` array. Registration and removal index that array directly; provider
lookup also rejects the highest valid ID. IMG, VDEC and VENC need five slots
for four gates; MM needs 43 slots for 42 gates. TOP, INFRA and APMIXED already
allocate their binding limits directly and are unaffected by this defect.

The [single patch](../../patches/upstream-4d7d9486/clock-ids/0001-clk-mediatek-size-MT6797-providers-for-one-based-IDs.patch)
adds an optional provider slot count to `mtk_clk_desc` and sets it from the
four existing binding limits. Gate counts, registration and unwind loops
stay unchanged. A descriptor without the new field retains the summed count
used by existing drivers. Slot zero remains initialized to `-ENOENT` by the
existing allocator. No binding IDs, register operations or DT nodes change.

This follows the [camera clock audit](../2026-09-07-mt6797-camera-clock-upstream-architecture/README.md)
but repairs existing upstream providers independently. Historical local CAM,
MJC and MFG patches are not selected or rewritten; their slot counts need the
same review before any future adaptation. The camera consumer, power and DMA
ownership requirements remain unresolved.

## Validation

[Source inputs](source-inputs.json) pin individual files from the validated
Buildbox prepared source at the upstream revision above. The source profile's
RTC patch does not touch these inputs. No Linux tree is vendored here.

The [regression](test-allocation.py) compiles the actual allocation statements
from `clk-mtk.c` and checks them against IDs and gate counts read from all four
provider sources and the binding header. The unchanged upstream code compiles
but fails all four bounds checks; the patch passes all four. Two additional
cases check unchanged dense and mixed-type default allocation. This fixture
tests allocation arithmetic, not real regmap access, clock operations or IRQs.

```sh
python3 experiments/2026-09-08-mt6797-clock-id-allocation/test-allocation.py \
  /path/to/prepared/linux
KERNEL_PROFILE=mt6797-clock-ids-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-clock-ids-compile ./scripts/buildbox fetch-package
```

The isolated profile selects only this patch and enables all four affected
providers. The [Buildbox receipt](compile.json) records a successful build from
project commit `b143a571`, with zero compiler warnings or errors. All four
provider objects compiled and their driver symbols are present in the final
kernel. The package was fetched with matching inventory and checksums. The
same six regression cases pass against Buildbox's exact prepared source.
All 244 inspected shared-descriptor initializers use named fields. The 199
existing profiles retain their definitions and patch order. Repository checks
passed before publication; Linux-only provenance fixtures remain deferred to
CI. Strict checkpatch passes with only `MISSING_SIGN_OFF` excluded.
No DT/schema changes require validation. No device access or boot occurred.

## Upstream boundary

The destination is the MediaTek common-clock subsystem. The
[submission review](SUBMISSION.md) records exact current refs, recipients,
bounded overlap findings, source-license review and AI attribution. The
synthetic archive author provides no DCO sign-off; truthful authorship and
certification remain required. No message was sent. Delete this local patch
once an equivalent fix reaches the selected baseline and passes regression.
