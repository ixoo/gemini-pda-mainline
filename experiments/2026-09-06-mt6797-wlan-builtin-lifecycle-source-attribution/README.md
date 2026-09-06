# MT6797 WLAN built-in lifecycle source attribution

Three bounded source results are established; the outer initialization and exit
callers remain unresolved. This does not change the predecessor's lifetime or
cleanup verdicts and does not establish running Gemian equivalence.

| Predicate | Result | Boundary |
| --- | --- | --- |
| Wi-Fi guard and WMT operations table | Resolved | Literal guard value 1 selects the Wi-Fi operations address. |
| Selected built-in initialization caller | Unresolved | Gen3 export calls initWlan and returns its status; outer caller uninspected. |
| Selected built-in exit caller | Unresolved | Gen3 export calls exitWlan; outer caller and actual invocation unknown. |
| Built-in __exit_p and platform remove | Resolved | Non-MODULE expansion yields NULL. |
| Unregister dispatch to callback clearing | Resolved | Selected static dispatch has no bus or driver remove callback reaching the clearing body. |

## Evidence and exact conditions

The [work item](WORK_ITEM.md) pins Planet source
`c5b0be85017ad0c599725e8273842efdbecdd88a` and repository parent
`05e3e04afd0f00a6a2ed1fdb9a263af8c0fd1d0d`.
[Inputs](inputs.json) record 22 complete source tuples: ten inherited from the
accepted predecessor and twelve newly fetched regular files.
[Verdicts](verdicts.json) give exact source/line/symbol citations, conditions,
missing edges and next discriminators for all five predicates.
The [independent freeze](FREEZE.md) fixes all tuples and 36 citation anchors
before verifier construction.

The selected kernel-build Makefiles descend through common_main/core and select
the WMT core/function objects for CONFIG_MTK_COMBO=y. The actual function header
is under core/include, and its Wi-Fi definition is controlled by literal
`#if 1`; the nearby CONFIG_MTK_COMBO_WIFI text is only a comment. The core
includes that header before initializing its Wi-Fi operations-table entry
(`common_builtin`, `core_objects`, `core_include`, `wifi_guard`,
`wifi_table` citation keys).

For the selected CONFIG_MTK_COMBO_WIFI=y gen3 path, the WLAN Makefile defines
MTK_WCN_BUILT_IN_DRIVER. The source exports a gen3 initialization wrapper that
returns initWlan's status; initWlan observes the bus-registration return and
maps it to zero or -EIO. It also exports a wrapper calling exitWlan. Those
exports do not prove their outer callers. The alternate module_init/module_exit
branch is not the selected producer (`wlan_make`, `gen3_object_mode`,
`hif_macro`, `init_exit`).

In the built-in non-MODULE case, init.h expands `__exit_p` to NULL, so
MtkPltmAhbDriver.remove is NULL. Its nested generic driver remove member is
zero-initialized. Platform registration installs the generic remove wrapper
only when the platform remove member is nonnull; the platform bus initializer
also supplies no remove callback. Unregister reaches driver_unregister,
bus_remove_driver, driver_detach and conditional device-release dispatch; neither
selected remove slot can call HifAhbPltmRemove and its callback-clearing body
(`exit_macro`, `platform_driver`, `platform_registration`,
`platform_bus`, `platform_unregister`, `driver_unregister`, `bus_remove`,
`driver_detach`, `device_release`, `registration`, `assignment`).

This is a static conditional dispatch result, not a claim that exit was invoked
or that callbacks were observed uncleared. MODULE differs from CONFIG_MODULES;
general module support does not make this built-in object a loadable module.
No dynamic pointer mutation, alternate build, concurrency, queue synchronization,
power effect or runtime behavior is inferred.

## Bounded handoff

[Search accounting](search.json) records all 18 network requests across three
predeclared batches: thirteen successful raw reads (one repeated platform.c
identity), two explicit 404s at initially guessed header paths, and three
immediate-directory inventories. A successful header read did not contain the
target guard; the next declared batch found it in wmt_func.h. No contextual
function-body reread was used. Previously fetched include/table and initializer
data were reused without new requests. No whole-tree inventory or source body
was retained on disk.

The file and batch budgets are exhausted. A new bounded audit must first inspect
common_detect/drv_init/Makefile, then select only lifecycle producer/caller
sources demonstrated by that build selection and subsequent direct edges. The
directory inventory also includes common_drv_init.c, alongside wlan_drv_init.c
and conn_drv_init.c; filenames alone cannot select or exclude a caller. Their
metadata is not evidence of source bodies or invocation. This item does not
perform that sequential follow-up.

Run `python3 verify.py` and `python3 -O verify.py` in this directory.
The [validation record](VALIDATION.md) reports checks actually run. The verifier
resists coordinated evidence edits but does not execute vendor code or prove
source semantics independently of review.

The first-review freeze extension also fixes the complete immutable request
evidence, including directory URLs, response hashes/sizes, entries and no-hits.

Only this experiment was edited. No private input, SSH, device, VM, Buildbox,
kernel, shared-document, staging, commit or push action occurred. Source study
does not grant vendor code/API reuse or firmware redistribution. The integration
owner owns acceptance and the workflow-ledger measurement; credits are
unavailable.
