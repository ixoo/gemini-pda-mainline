# Coherent topic routing and resource review

## Routing result

The pinned upstream maintainer tool ran on all six exact review patches in two
modes. [The complete result](results/maintainer-routing.json) retains tool/input
hashes, patch identities, options, public maintainer roles and candidate trees.
Generation used project revision `8b3a62d3`; no mail or submission was sent.

| Patch | Path-based routing | Additional keyword routing |
| --- | --- | --- |
| 1: generic bounds | Common clock framework | MediaTek SoC maintainers and lists |
| 2: generic tests | Common clock framework | MediaTek SoC maintainers and lists |
| 3: binding | Clock, Devicetree, reset-controller and MediaTek maintainers | Same set |
| 4: MT6797 provider | Clock and MediaTek maintainers | Same set |
| 5: MT6797 tests | Clock and MediaTek maintainers | Same set |
| 6: SoC DTS | Devicetree and MediaTek maintainers | Same set |

The path-only run would omit MediaTek reviewers for the two generic patches.
Use the keyword-inclusive result as a review input for those patches. The tool
reports the common-clock tree for driver changes and both Devicetree and reset
trees for the binding. Its generic top-level Linux match does not mean sending
the topic directly to Linus. No unambiguous MediaTek merge branch was selected
by this audit; that remains a maintainer-routing question.

The proposed submission structure is a clock/reset series with binding review,
plus the dependent SoC DTS change through the agreed MediaTek/DT route. This is
an integration proposal, not a maintainer agreement. Keep the shared binding
header available in the DTS base or an agreed immutable dependency. Recheck
current maintainers and public overlap immediately before submission. The
historical patch authorship audit and genuine certification remain open.

The auditor deliberately excludes Git-history recipients, file-address
harvesting, mailmap and Fixes-derived contacts, and disables account-specific
configuration. It does not search mailing-list archives. These limitations are
part of the result, not evidence that other reviewers or overlapping work do
not exist.

## Binding compatibility review

The two-entry public reset namespace is new to the pinned upstream provider.
Historical local IDs never became an upstream ABI through this repository.
The binding patch requires one reset cell for MT6797 in the shared infracfg
schema, and the final DTS patch supplies it on the existing node. No new node,
address range, clock specifier or consumer phandle is introduced.

Requiring the property means an older MT6797 DT source without it will no longer
validate against the new schema. That needs explicit binding review. It does
not by itself prove that an older DTB stops booting: the reviewed registration
path below does not require a DT `#reset-cells` property before registering the
clock driver's reset controller, and older upstream DTs have no reset consumers
for this provider. Backward runtime compatibility still needs appropriate
validation; schema reasoning is not a hardware regression result.

The header keeps only thermal and PMIC-wrapper IDs. TOPRGU and the unproved RST1
bank remain outside the topic. The generic private bounds helper does not change
the public reset-controller API or the existing valid compact-map translations.
Sparse maps in other SoC descriptors retain their existing semantics; this topic
does not claim to fix every unmapped-hole policy in all MediaTek providers.

## Provider ordering and resource ownership

At upstream `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, additional primary inputs
reviewed in memory were:

| Source | SHA-256 | Bytes |
| --- | --- | ---: |
| `drivers/mfd/syscon.c` | `2d93e488b42bd7ed6ee2f6d0ec3fabbe201f8f98caae2d226564b64870164aec` | 8957 |
| `drivers/reset/core.c` | `bb8683f8973883979481512a4f6e21deac741776dfb3370591bc611988c49762` | 41159 |

They are available from the pinned
[syscon source](https://raw.githubusercontent.com/torvalds/linux/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/mfd/syscon.c)
and [reset core](https://raw.githubusercontent.com/torvalds/linux/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/reset/core.c).
The already pinned `drivers/clk/mediatek/reset.c` supplies the call site.

The MediaTek registration function uses `device_node_to_regmap()`. At this
revision that delegates with resource checking disabled. Syscon's optional
clock acquisition and reset deassertion are guarded by the resource-check flag;
this call does not take that path. It obtains or creates a shared MMIO regmap.
This supports using the existing infracfg resource without introducing a reset
operation or a clock-resource dependency through this registration call.

`devm_reset_controller_register()` allocates managed registration state and calls
`reset_controller_register()`. The latter validates firmware-node metadata,
sets up translation and list/lock state, and publishes the controller. These
functions do not invoke the provider's assert/deassert/reset callbacks. Later
consumer operations remain separate and must use the proved map and bank bounds.

The new provider call precedes platform clock allocation. A registration failure
returns before this invocation adds platform clock state. The early clock
provider, if already present, is untouched by that failure branch. Successful
reset registration is managed by the platform device if later probe work fails;
the shared syscon regmap has its own lifetime. This is a source-level ownership
review, not a fault-injection or retry/unbind test. Existing clock-registration
error handling and consumer interactions still need final validation.

## Remaining evidence boundary

This review resolves the initial recipient omission and documents the schema
compatibility question and registration call chain. It does not replace focused
build, KUnit execution, binding/DT checks, failure-path tests, author certification
or maintainer feedback. Exact upstream build support remains the separately
owned [source-selection integration](SOURCE_INTEGRATION.md). No device action
is required by this routing or source review.
