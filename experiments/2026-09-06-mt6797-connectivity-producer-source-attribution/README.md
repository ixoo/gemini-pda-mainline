# MT6797 connectivity outer producer source attribution

## Result

At Planet commit `c5b0be85017ad0c599725e8273842efdbecdd88a`, the selected
detector's `wmt_detect_unlocked_ioctl` is a direct producer of
`do_connectivity_driver_init`. It passes the external ioctl argument, not an
intrinsically configured chip identity, and returns the final integer aggregate.
Detector boot-time registration does **not** itself invoke connectivity init.
Four predicates resolve within source conditions; actual chip-value provenance
and a gen3 teardown join remain unresolved.

The [contract](WORK_ITEM.md) freezes parent
`45b57d265252e8b9068038b84e53b68624f3bab1`. The
[accepted direct predecessor](../2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/README.md)
owns the inner common/WLAN sequencing and aggregation audit. This experiment
does not establish runtime execution, final linkage, resource ownership,
firmware success, safe radio actions or hardware support.

## Exact source boundary

[inputs.json](inputs.json) contains 19 full identity tuples: ten from the direct
predecessor, three additional independently pinned ancestor tuples, and six new
regular files. The inherited detector Makefile and configuration were checked
field-for-field before new body selection. Under `CONFIG_MTK_COMBO=y`, the
Makefile explicitly selects detector/stub objects; `CONSYS_6797` selects the SoC
macro, not external-combo support. The connectivity Makefile's nonempty
`KERNELRELEASE` branch defines `MTK_WCN_REMOVE_KERNEL_MODULE`; the detector
header maps that definition to `MTK_WCN_REMOVE_KO=1`.

Batch 1 fetched the complete selected detector and stub bodies. Batch 2 followed
only their direct guard/declaration, SDIO-cleanup and registration-header edges.
The module header did not define the registration macros; independently pinned
ancestor `init.h` supplies them. No extra network reread was made. The small
stub declaration region elided by tool presentation is recorded honestly:
there is no whole-stub absence claim. The visible chip-cache functions and
complete detector handler suffice for the established producer edge.

## Six independent predicates

Exact line/symbol citations, conditions, missing edges and discriminators are
in [verdicts.json](verdicts.json).

| Predicate | Result | Boundary |
| --- | --- | --- |
| Selected producer corpus | Resolved | Built-in detector/stub selection and direct batch-2 edges; not all selected bodies or a final link test. |
| Direct producer | Resolved | Detector ioctl handler, command `COMBO_IOCTL_DO_MODULE_INIT`, enabled removal-of-module guard. |
| Chip provenance | Unresolved | External unsigned-long argument converts to int; no handler validation or proven actual `0x6797` value. |
| Final aggregate consumer | Resolved | Integer retval returned as long; compat forwards unchanged; no handler retry or once-only guard. |
| Registration/order | Resolved | Detector level-6 built-in initcall registers its interface before SDIO detection; connectivity init needs a later ioctl. |
| Gen3 teardown join | Unresolved | Cleanup ioctl unregisters the SDIO detector; no explicit gen3 exit join in the bounded corpus. |

The ioctl command's encoding does not imply pointer-copy semantics: this handler
passes the scalar argument directly. Chip cache get/set and SoC query are
separate command branches, not a demonstrated source of the init argument.
The configured string therefore cannot prove selection of the WLAN `0x6797`
case. The inherited common aggregate gate and intended ordinary WLAN linkage
also remain conditions of reaching gen3 initialization.

The successful detector registration sequence is region registration, cdev
initialization/addition, class/device creation, then SDIO detector init. Early
character-interface errors return before SDIO init. SDIO init logs its driver
registration return but itself returns zero; its caller ignores that return.
This registration result is distinct from the later connectivity aggregate.
Neither zero aggregate proves that every summed component succeeded.

The cleanup command reaches `sdio_detect_exit`, which clears its local function
pointer and unregisters its SDIO client driver. The detector exit body's SDIO
call is excluded under the selected guard, and its external-combo unregister
branch is also excluded. A built-in `module_exit` declaration is not automatic
unload or proof of a gen3 exit call. Core unregister callbacks are not promoted
to an unestablished transitive join.

## Evidence and handoff

[search.json](search.json) freezes both predeclarations, all six successful
receipts, four bounded no-hits, presentation limits and the closed budget.
Both batches are consumed: six of seven new files, zero inventories and zero
network contextual rereads. No retrieval failures or source repairs occurred.
[FREEZE.md](FREEZE.md) records literal independent source, citation, complete
request and complete verdict freezes declared before [verify.py](verify.py).
[VALIDATION.md](VALIDATION.md) records tests actually run and exclusions.

The escalation is bounded: the immediate kernel producer and return path are
known; the external issuer's actual chip value, ordering and return/retry policy
are not. Any future discriminator needs a separately scoped, pinned userspace
producer/consumer or actual teardown edge. No extra source batch, whole-tree
search, device operation or automatic initialization probe is permitted here.

Only source-study metadata and independently authored prose/verifier code are
retained. Vendor notices were inspected without inferring reuse rights; no
source body, excerpt, private input or device data is included. Astra Medium
owned this hard uncertainty. Sol Medium independently accepted the complete
experiment and shared integration on first review at 19:06:42 UTC. Start was
observed at 18:51:59 UTC and the review-ready handoff at 19:02:46 UTC; credits
are unavailable. The accepted pilot-03 measurement is in the workflow ledger.
No adjacent work was started by the handoff.
