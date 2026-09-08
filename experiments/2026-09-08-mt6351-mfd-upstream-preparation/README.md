# MT6351 MFD upstream preparation

Status: incomplete upstream-preparation checkpoint, 2026-09-08. A named
compile-only topic has passed build and schema checks; it is not a device
candidate or upstream submission. Existing profiles are unchanged. [Initial source receipts and
check results](source-review.json) pin the individual public files inspected;
Linux sources are not vendored here.

## Scope and result

The existing Gemini MT6351 core patch combines a four-bank extension with a
correction to an already supported chip. Separate that correction before
adapting the MT6351 topic. The unsigned [MT6328 draft](patches/0001-mfd-mt6397-size-MT6328-interrupt-domain.patch)
adds a terminal interrupt count and selects it for MT6328 alone. It does not
add Gemini support and is not a prerequisite for unrelated board progress.

At Torvalds commit `5acbae5f7eb3d5275120abfe698c394b7325dcec`, MT6328's
header names interrupts through 46, and `mt6397-irq.c` handles three banks,
but initialization creates a 32-source domain. MFD-next commit
`b07adc1a304c7ca9ac25a01051561538757363c9` has identical relevant MFD
files and MT6328 header. Its IRQ-domain implementation sets `hwirq_max` to
the requested size and rejects `hwirq >= hwirq_max` before mapping.
Consequently the existing domain cannot map named sources 32–46.
The draft uses 47, covering the named range without assigning an undocumented
source to bit 47. Other chips retain their existing domain size.

The local patch 0010 instead uses bank count times 16 for every chip, thereby
quietly changing MT6328's domain to 48 while adding MT6351. Its successful
application to current source does not establish that the combined change is
the appropriate upstream topic.

## Initial MT6351 dependency split

| Topic | Evidence and next action |
| --- | --- |
| PMIC wrapper | Current upstream already has MT6797 wrapper and MT6351 PMIC entries in `mtk-pmic-wrap.c`; no replacement wrapper is indicated. |
| MFD binding | Parent/core support remains absent in the inspected upstream files. Local 0008 fails application at the changed PMIC-keys schema. Adapt the parent binding separately and check current child schema dependencies. |
| Core and IRQ | Extract MT6351 chip identity, four-bank storage and IRQ handling from local 0010 after separating the existing-chip correction. Preserve mask, suspend and handler behavior for existing chips; review error handling and registration ordering. |
| Regulators | Local regulator support underlies demonstrated storage supplies. A new MFD parent must be paired with the corresponding reviewed regulator driver/binding; the inspected upstream regulator Makefile has no MT6351 entry. |
| RTC and keys | The inspected MFD-next drivers have no MT6351 match. Do not equate creating these child devices with working RTC, keys or wakeup. |
| Audio | The upstream MT6351 codec exists, but its component initialization writes PMIC registers, including protection settings. Keep codec/card enablement out of this topic until analog routes and resource ownership are established. |

The earlier corrected-reset storage evidence establishes bounded VEMC/VIO18
use through the local stack. It does not establish all 64 MT6351 interrupts,
other regulators, RTC, key wakeup or audio. The
[support matrix](../../docs/HARDWARE_SUPPORT.md) retains those runtime limits.

## Validation and submission boundary

The draft applies cleanly to both pinned source snapshots. The pinned MFD-next
`checkpatch.pl --no-tree` reports **one error: missing Signed-off-by**, with
zero warnings; this is deliberately an unsigned draft, not a passing
submission check. This standalone draft was not compiled or hardware-tested.
The extracted topic and its later compile result are recorded below; neither
result establishes hardware IRQ mapping behavior.

The archive identity is non-certifying. Historical patch author/sign-off lines
are not evidence of current authorship certification. Resolve actual authorship
and truthful DCO certification before submission. The inspected `MAINTAINERS`
entry identifies Lee Jones, `mfd@lists.linux.dev`, and the
[MFD tree](https://git.kernel.org/pub/scm/linux/kernel/git/lee/mfd.git/).
Re-run maintainer discovery against the final series before contacting anyone;
no mail or issue comment was sent during this review.

To reproduce application checks, retrieve the paths and commits in the receipt
into a disposable source checkout, verify their SHA-256 values, and run
`git apply --check` on the linked draft. Run the recorded checkpatch version
with its adjacent spelling and constant-structure files. Receipt entries refer
to source inspection, not a complete checkout or a kernel build.

## Extracted regulator topic

The [five-patch compile series](../../patches/series-mt6351-regulator-compile)
now separates the MT6328 correction, regulator binding, MFD parent binding,
MT6351 core/IRQ extension and regulator driver. The MFD creates only the
regulator child. RTC, key and sound cells and their binding extensions remain
outside this topic. No SoC or board DTS is added.

The compile baseline is the already cached upstream commit
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c` (Linux 7.3-rc1), selected by
the complete source tuple in the new `mt6351-regulator-compile` profile.
Its five inspected MFD/header/binding inputs are byte-identical to the newer
snapshot reviewed above. [Series receipts](series-review.json) pin the seven
base files, five patches and pre-build checks. Exact replay and comparison of
all nine buck and 30 LDO descriptors and voltage tables passed.

The extracted regulator driver fixes one concrete lifetime bug in local 0015:
its probe mutated the shared descriptor array when a buck control bit was set,
but never restored the default selector register when a later probe read that
bit clear. The draft keeps an immutable template and allocates a private copy
for each device before selection and registration. The
[helper regression](test-buck-reprobe.py), run with Python 3 and a host C
compiler, reproduces the old stale selection, checks fresh-instance selection
and isolation, and checks propagation of a selector-register read failure.
It exercises extracted helper bodies with an injected regmap; it does not
exercise regulator-core registration or hardware. All rail tables and the E2
revision restriction remain unchanged.

Strict checkpatch passes with three explicitly recorded exclusions: missing
sign-off for the unsigned archive, new-file maintainer reminders, and two
initializer-macro argument-reuse notices. The latter pass only static arrays
to descriptor pointers and `ARRAY_SIZE`, so no side-effecting expression is
evaluated twice. The initial unrestricted check also caught a continuation
alignment error, which was corrected before this result. Existing copyright,
module-author and proposed binding-maintainer text is retained from the
historical inputs; it is not new certification or proof of maintainer agreement.

The build from project commit
`d1f54dbc97fc86c0d2e2443c0c5f82306c840209` passed without compiler warnings
or errors. The [compile receipt](results/compile.json) records the validated
and fetched package, exact source/object hashes, configuration and toolchain.
The linked Image contains the MFD initialization and suspend notifier, and the
regulator object has calls to the descriptor-copy and registration functions.
The compiled source hashes match the reviewed draft. Reproduce the build from
a clean pushed checkout with:

```sh
KERNEL_PROFILE=mt6351-regulator-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6351-regulator-compile ./scripts/buildbox fetch-package
```

Focused `dt_binding_check` passed for `mediatek,mt6397.yaml` and
`mediatek,mt6351-regulator.yaml` using the existing pinned dtschema 2026.6
environment. All schema/lint/style completion markers were present. Direct
validation of the normal examples and the [combined MT6351 fixture](results/joint-example.dts)
produced empty diagnostics; an unknown rail name was rejected. The
[schema receipt](results/schema.json) and [portable log](results/schema-validation.txt)
record those checks, verified source integrity and the fetched inventory.
The first combined fixture incorrectly included `#address-cells` on the PMIC,
which the parent schema disallows. Only that fixture was corrected. Its DTC
check suppresses the corresponding interrupt-provider warning; no board DTS
or schema constraint was changed to make the fixture pass.

For schema reproduction, use the same prepared source with a separate output
directory and `ARCH=arm64`, and set
`DT_SCHEMA_FILES=mediatek,mt6397.yaml:mediatek,mt6351-regulator.yaml` when
running `make dt_binding_check`. Compile the linked fixture with that output's
`scripts/dtc/dtc -Wno-interrupt_provider`, then use `dt-validate` with the
generated `processed-schema.json`, separately selecting `mediatek,mt6397` and
`mediatek,mt6351-regulator`. Replacing `ldo-vemc` with `ldo-invalid` must produce
the rejection in the log. These are schema checks, not hardware tests.

The profile enables suspend so the legacy IRQ notifier path is compiled. It
does not select a Gemini DTB, storage, networking or audio. No resulting image
is admitted for device installation. Before a production regulator topic,
resolve shared VCN33 voltage ownership: the BT and Wi-Fi descriptors have
distinct enables but the same voltage-selector field. Independent voltage
requests must not silently override another consumer's constraints. Wider rail
behavior and PMIC interrupt error handling also remain review/runtime gaps.
The inherited binding's physical-output wording is provisional: 39 is the
descriptor count, not proof of 39 distinct output pins.

For comparison, the same upstream baseline's `mt6358-regulator.c`
(`ed08d4146908e19fdd6192f16cf8288c21ded3146a7c901adff82e77df8e7acf`)
documents one VCN33 output pin with two enable bits and consolidates those
controls during probe. `mt6359-regulator.c`
(`8d69fe4466dfdbe848dedde99db964b71ded2c83b000838369011b6e748c861d`)
also synchronizes enable controls and supplies legacy BT/Wi-Fi aliases from a
common regulator. These are useful ownership precedents, not proof that
MT6351 has the same output-pin topology or that copying their probe writes
is appropriate. Resolve that distinction before revising the shared-rail model.

The [MT6351-specific VCN33 follow-up](VCN33.md) confirms the common selector
and separate software/on-control/source-clock fields. The vendor's common
BT/Wi-Fi helper is in a disabled branch, so it cannot justify consolidating
the controls. The physical topology remains unresolved.

## IRQ mask-write failure follow-up

The compile series now adds [one mask-error correction](../../patches/upstream-4d7d9486/mt6351/0006-mfd-mt6397-stop-on-interrupt-mask-failure.patch).
Initialization previously ignored failed writes while masking the interrupt
banks, then created the IRQ domain and registered the parent handler. The
correction returns the bus error at the first failed bank before either
registration step. Earlier banks may already be masked; it performs no retry
or restoration of unknown hardware state.

The [focused regression](test-irq-mask-failure.py) compiles the actual before
and after initialization bodies with injected register-write results. It
reproduced the old behavior and rejected all 15 per-bank failures across the
six supported chip IDs, while preserving their successful bank/domain setup.
The test uses fake register addresses and registration callbacks; it proves
control flow, not register semantics or a running kernel's IRQ behavior.
Pass the five-patch and six-patch versions of `drivers/mfd/mt6397-irq.c` as
its two arguments. Strict checkpatch passed with only the unsigned-archive
sign-off exclusion. The new compile result is pending at this input checkpoint;
the five-patch build receipt above remains historical evidence for its own input.

Other IRQ lifetime issues remain separate: the legacy initializer does not
unregister its PM notifier, and the MFD child-add failure path removes the
domain before the managed parent IRQ is released. Review cleanup ordering and
concurrent IRQ/notifier use before promoting the topic. The mask-error change
does not repair or validate those later lifetime paths.
