# Clock allocation submission preparation

Technical review refreshed on 2026-09-12. The patch and its Buildbox inputs
remain unchanged. This packet is ready for human review, not submission:
the archive has a synthetic author and no DCO certification. No mail was sent.

## Current source and target

The destination is the common-clock tree, with MediaTek review. The following
refs were resolved from the official mainline and clock Git repositories:

| Tree/ref | Inspected commit |
| --- | --- |
| Mainline master | `cba2348ab114391f5b1a00fa65c5b739f13f0563` |
| Clock clk-fixes | `59e0cc31cc5c43586c6eaada62c2c863bfbcbfb5` |
| Clock clk-next | `276741aac3b56ba50bef59715ba18ba3f0b953a2` |

All seven allocation inputs in [source-inputs.json](source-inputs.json) are
byte-identical at these three refs and the original build base: `clk-mtk.c`,
`clk-mtk.h`, the four affected provider sources and `mt6797-clk.h`. Compare the
[mainline sources](https://github.com/torvalds/linux/tree/cba2348ab114391f5b1a00fa65c5b739f13f0563/drivers/clk/mediatek)
and [clock fixes sources](https://kernel.googlesource.com/pub/scm/linux/kernel/git/clk/linux/+/59e0cc31cc5c43586c6eaada62c2c863bfbcbfb5/drivers/clk/mediatek/).
`clk-fixes` is the proposed bug-fix target; maintainers choose integration.
These refs are observations, not changes to the project's pinned kernel.

The unchanged [patch](../../patches/upstream-4d7d9486/clock-ids/0001-clk-mediatek-size-MT6797-providers-for-one-based-IDs.patch),
SHA-256 `fceb581a0b5a1d8cdfa8a03b719aabf2eafe915ea2022485c897b9ef634fe594`,
passes `git apply --check` against the selected clk-next files. Its applied
sources pass all six cases in [test-allocation.py](test-allocation.py).
Unpatched sources compile but fail all four provider bounds checks:

| Provider | Gate count | Unpatched slots | Patched / required slots |
| --- | --- | --- | --- |
| IMG | 4 | 4 | 5 |
| MM | 42 | 42 | 43 |
| VDEC | 4 | 4 | 5 |
| VENC | 4 | 4 | 5 |

The two dense/mixed default-allocation cases also pass. This compiles the
actual allocation statements with host `cc -Wall -Wextra -Werror`; it does
not execute a kernel probe. The [existing Buildbox receipt](compile.json)
remains the full-kernel compile evidence, on its original base only. There
was no full build of the three newly inspected refs and no device test.

## Origins and overlap

Two conversions introduced the defect independently:

- [a481c6c73bff](https://github.com/torvalds/linux/commit/a481c6c73bffc2e4ac3ffba8871d67ce2438c4b2)
  replaced explicit binding-limit allocation in IMG, VDEC and VENC with
  common-probe gate counts. Its helper allocates `mcd->num_clks` slots.
- [65c10c50c9c7](https://github.com/torvalds/linux/commit/65c10c50c9c7619637f064bbdb4d4f37556ee498)
  converted MM separately, replacing `CLK_MM_NR` allocation with the common
  summed descriptor count. The binding IDs were already one-based at both
  introducing commits. No first-affected release or stable backport was tested.

The August and September 2026 MediaTek archive thread indexes and the relevant
messages in the [common-probe conversion series](https://lists.infradead.org/pipermail/linux-mediatek/2026-August/111247.html)
were inspected. [Patch 09/32](https://lists.infradead.org/pipermail/linux-mediatek/2026-August/111256.html)
adds cpumux counts and [10/32](https://lists.infradead.org/pipermail/linux-mediatek/2026-August/111257.html)
adds PLL counts to the same allocation block. Neither supplies an explicit
provider-ID capacity. [18/32](https://lists.infradead.org/pipermail/linux-mediatek/2026-August/111265.html)
converts TOP, INFRA and APMIXED; it does not modify these four provider files.

No equivalent fix was found in that bounded review. The public series was
not replayed, and its other providers were not certified by this check.
If it lands first, preserve the added default count terms when adapting the
override and rerun the allocation regression and relevant compile checks.
This ordinary helper-context overlap does not create a dependency on the
separate infracfg reset topic's provider-ordering decision.

## Recipients

Both inspected clock refs' `get_maintainer.pl --no-tree --no-git
--no-git-fallback` runs identify the same recipients for the patch:

- Stephen Boyd <sboyd@kernel.org>
- Brian Masney <bmasney+clk@redhat.com>
- Jerome Brunet <jbrunet+clk@baylibre.com>
- Matthias Brugger <matthias.bgg@gmail.com>
- AngeloGioacchino Del Regno <angelogioacchino.delregno@collabora.com>
- linux-clk@vger.kernel.org
- linux-kernel@vger.kernel.org
- linux-arm-kernel@lists.infradead.org
- linux-mediatek@lists.infradead.org

The script SHA-256 remains the one in [source-inputs.json](source-inputs.json).
The clk-fixes `MAINTAINERS` SHA-256 is
`1b6bd8418b8bbdcbce595c4648c10afaf23370e3de243a282dbc992798de3a84`;
clk-next is `c9f85d60dcab471dc311a71529702d0efac74c145fbb0dc7518e0ed6c61ef9b5`.
Refresh recipients and the selected base when the human-reviewed patch is
exported. No recipient has supplied a review, test or certification trailer.

## Prepared commit message

Use this text with the existing nine-line implementation after actual
authorship is established. It deliberately contains no sign-off:

```text
clk: mediatek: size MT6797 providers for one-based clock IDs

The MT6797 IMG, MM, VDEC and VENC bindings start at one. Their common
probe allocates one slot per gate, leaving the largest clock ID outside
the hws array. IMG, VDEC and VENC have four gates but need five slots;
MM has 42 gates but needs 43 slots. Registration and removal index hws
by clock ID, and the OF provider rejects the highest valid ID.

The IMG/VDEC/VENC and MM conversions to common probing replaced the
providers' explicit binding-limit allocations with gate counts.

Allow descriptors to specify their provider slot count separately from
the gate count, and use the existing binding limits for these providers.
Descriptors without an explicit slot count retain the existing summed
allocation. Keep registration and unwind loop bounds unchanged, and
leave the unused slot zero initialized to -ENOENT.

Fixes: a481c6c73bff ("clk: mediatek: mt6797: use mtk_clk_simple_probe to simplify driver")
Fixes: 65c10c50c9c7 ("clk: mediatek: Migrate to mtk_clk_pdev_probe() for multimedia clocks")
Assisted-by: LLM
```

The accompanying submission comments should state that Codex/LLM assistance
covered source analysis, the fix, the focused regression and preparation of
this text during the request to deliver the Gemini roadmap. Include the
original-base Buildbox result and current-source regression limits above.
Do not describe the host fixture as a hardware or KASAN result.

The prepared message plus unchanged diff was checked with the pinned strict
checkpatch, excluding the intentionally absent `MISSING_SIGN_OFF`. It reports
zero errors and two `UNKNOWN_COMMIT_ID` warnings because this small repository
has no Linux Git history. Both full introducing commits and exact titles were
verified independently from the linked upstream commit records. The final
export should be checked in its actual kernel checkout.

## Human handoff and limits

All six modified source files carry `GPL-2.0-only`. Their existing MediaTek
copyright and author notices remain intact; this fix adds no retained firmware
or vendor implementation. Those facts do not certify a new contributor.
The repository's synthetic archive identity is not an upstream author.
The [kernel's AI contribution guidance](https://github.com/torvalds/linux/blob/cba2348ab114391f5b1a00fa65c5b739f13f0563/Documentation/process/coding-assistants.rst)
requires AI attribution and leaves DCO certification to a human who reviews
and takes responsibility for the contribution. A human must establish the
proper author, add their own truthful certification and review the final
export; neither a repository commit author nor standing publication approval
provides that certification.

Source inspection confirms direct out-of-bounds indexing during ordinary
provider registration/removal and rejection of the highest ID during OF
lookup. No unprivileged or remote trigger, privilege-boundary crossing, crash
trace or exploit was demonstrated. The proposed disposition under the
[kernel threat model](https://github.com/torvalds/linux/blob/cba2348ab114391f5b1a00fa65c5b739f13f0563/Documentation/process/threat-model.rst)
is a regular driver bug, for the human reporter to review. The relevant
[gate indexing](https://github.com/torvalds/linux/blob/cba2348ab114391f5b1a00fa65c5b739f13f0563/drivers/clk/mediatek/clk-gate.c#L279)
and [OF bounds check](https://github.com/torvalds/linux/blob/cba2348ab114391f5b1a00fa65c5b739f13f0563/drivers/clk/clk.c#L5063)
are the source basis, not runtime evidence.

Keep the original patch and compile receipt reproducible until a certified
revision replaces them through a reviewed update. Final export must carry the
actual public base and pass patch/style checks; changed code or source context
requires the relevant fresh compile evidence. Delete the local fix after an
equivalent upstream change reaches the selected baseline and passes regression.
