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
sign-off exclusion. The [six-patch compile](results/irq-mask-compile.json) from
project commit `267c94ecdf53dd1e65890644d4c5771dd5ec3a66` passed without
compiler warnings or errors, and its validated package was fetched. Its IRQ
source matches the tested after-file and its object contains the new error
reporting call. The upstream source tuple, configuration and original five
patches match the parent package exactly. No schema check was repeated for
this C-only change; the five-patch schema receipt remains applicable to the
unchanged bindings. Neither build establishes hardware behavior.

Other IRQ lifetime issues remain separate: the legacy initializer does not
unregister its PM notifier, and the MFD child-add failure path removes the
domain before the managed parent IRQ is released. Review cleanup ordering and
concurrent IRQ/notifier use before promoting the topic. The mask-error change
does not repair or validate those later lifetime paths.

The pinned kernel already provides `devm_irq_domain_instantiate`, which returns
an error pointer on failure. This offers a standard path for the cleanup fix:
allocate the managed domain before requesting the managed parent IRQ, and
manage PM-notifier removal as well. Both `mt6397_irq_init` and
`mt6358_irq_init` must adopt consistent domain ownership before removing the
MFD core's manual child-add-error cleanup. Retain the distinction between this
API's error pointer and the old linear wrapper's NULL result.
Relevant unchanged upstream files are `include/linux/irqdomain.h`
(`1bb4044856a5ef47c95eb09e366a1a9f147ff80a8a44a4486db584204338a6df`),
`kernel/irq/devres.c`
(`6d14378297fa53ea932184bf6b575c67c11b813ce559b2f706fbdc3df31e2f80`)
and `drivers/mfd/mt6358-irq.c`
(`eb2a0304a58b57354db017611265e70d798268a8f602e34ab3b8c04062f0d005`).
The implementation follow-up is recorded below.


## IRQ lifetime follow-up

The isolated compile series adds two unsigned patches:
[managed domains](../../patches/upstream-4d7d9486/mt6351/0007-mfd-mt6397-manage-IRQ-domain-lifetime.patch)
and [managed PM notifier](../../patches/upstream-4d7d9486/mt6351/0008-mfd-mt6397-manage-PM-notifier-lifetime.patch).
Both IRQ initializers now allocate their managed domain before requesting
the managed parent IRQ. The shared probe no longer removes the domain ahead
of that handler on child-add failure. The domain exit callback disposes its
linear child mappings, which the MFD core creates but does not dispose.
The legacy notifier registration now propagates errors and installs a managed
unregister action after parent IRQ registration.

The intended release order is child devices, PM notifier (legacy family),
parent IRQ, child mappings, domain, and earlier managed allocations. The pinned
kernel's reverse devres release order supplies this ordering; `free_irq()`
drains the handler before returning. Domain removal invokes `domain->exit`
before removing the domain itself. Notifier unregistration uses the blocking
notifier chain's write lock to exclude active callbacks. These are source
contracts, not measured device concurrency.

The [focused test](test-irq-lifetime.py), with its
[userspace fixture](test-irq-lifetime.c), compiles the actual two initializers
and release helpers from a supplied prepared Linux tree. Its eight-patch
version passed 56 cases:
ten chip selections with domain/request failures, successful detach and
partial child-add failure; legacy notifier/action failures; and all four
MT6351 mask-bank failures. It checks first, middle and last mapped IRQ disposal,
error propagation, and release order. Register addresses, modern-family bank
layouts, allocation, child creation and kernel synchronization are modeled.
This is not a KUnit or live-kernel concurrency test. Run:

```sh
python3 experiments/2026-09-08-mt6351-mfd-upstream-preparation/test-irq-lifetime.py PREPARED_LINUX
```

The earlier mask-error test remains tied to its recorded five/six-patch inputs.
The lifetime test covers the successor's four MT6351 mask failures. The
MT6358-family wake-enable reference, ignored mask-write errors, and global
mutable IRQ data remain separate inherited review gaps; these patches do not
claim complete teardown or multi-device correctness.

The [eight-patch Buildbox compile](results/irq-lifetime-compile.json) passed
without compiler warnings or errors from project commit `3fc732c6` and its
validated package was fetched. The prepared sources match the replayed/tested
files; both IRQ objects contain the new managed-domain calls, and the legacy
object contains mapping disposal and notifier cleanup. The exact same test
also passed on Buildbox's prepared source. Two deliberate omissions (mapping
disposal and notifier removal) were rejected at runtime locally. Strict
checkpatch passed with the unsigned-archive sign-off exclusion. The source
baseline, configuration, toolchain and first six patches match the parent
package; unchanged bindings did not need another schema check. No device
action is admitted.


## MT6358-family wake-reference follow-up

The [ninth patch](../../patches/upstream-4d7d9486/mt6351/0009-mfd-mt6358-balance-IRQ-wake-reference.patch)
balances the MT6358 initializer's successful `enable_irq_wake()` with a managed
disable action. The pinned `irq_set_irq_wake()` contract requires balanced
references, independently of handler removal. Cleanup runs before parent IRQ
release. An action-allocation failure disables wake immediately; an unsuccessful
wake enable remains nonfatal and installs no disable action, preserving the
existing probe behavior without decrementing an unacquired reference.

The focused lifetime fixture now models this reference and passes 64 cases.
The eight additional cases cover wake-enable and action-allocation failure for
all four chip IDs using this initializer. Existing success and partial-child
failure cases now also require wake to be disabled before handler/domain
release. This is shared-family cleanup, not a new MT6351 wake implementation.
Physical wake-disable failure is not modeled or repaired; ignored mask writes
and the modern initializer's shared mutable IRQ data remain separate gaps.
The earlier receipt retains the exact eight-patch test hashes and results.
The nine-patch compile is pending; no device candidate is created.
