# MT6797 WLAN drv-init lifecycle attribution

The selected wrappers establish a conditional direct initialization chain and
its arithmetic return aggregation. The outer producer/registration and gen3
exit invocation remain unresolved.

| Predicate | Verdict | Source boundary |
| --- | --- | --- |
| Makefile-selected objects | Resolved | Connection, common and WLAN are selected built-in; gen3 macro selected. |
| Gen3 initialization producer/caller | Unresolved | Direct wrappers joined; outer connectivity caller/registration absent from corpus. |
| Established init return handling | Resolved | Results added into aggregates, not preserved as separate errors. |
| Gen3 exit producer/caller | Unresolved | No exit reference or teardown registration in selected sources. |
| Explicit cross-component order | Resolved | Conditional direct-call order only; no exit ordering established. |

## Evidence

The frozen [contract](WORK_ITEM.md) uses repository parent
`30d414811724c25ebd4183c00f06cd8d27aebb0b` and Planet source
`c5b0be85017ad0c599725e8273842efdbecdd88a`.
[Inputs](inputs.json) pin ten full source identities, six inherited and four
new. [Search](search.json) preserves all four successful receipts and four
bounded no-hit records. [Verdicts](verdicts.json) provide exact source/line/symbol
anchors, conditions, missing edges and next discriminators.

The complete drv_init/Makefile was fetched alone first, and its identity/object
selection frozen before the second batch selected conn_drv_init.c,
common_drv_init.c and wlan_drv_init.c. The separate literal ANT assignment is
recorded without inferring conventional ANT object selection. No unrelated
component source body was fetched or audited.

For the ordinary WLAN implementation, the shown chain is
do_connectivity_driver_init → do_wlan_drv_init → mtk_wcn_wlan_gen3_init.
It requires the configured Wi-Fi/gen3 guards, chip argument 0x6797 and zero
common aggregate. An ordinary WLAN definition and a __weak connection fallback
are both present; final linkage and actual arguments were not tested.

The inherited gen3 export returns initWlan status. WLAN adds that result to
character-device initialization status and returns the sum. Connection adds
the WLAN aggregate to component results. Common itself sums four initializer
results. Only a nonzero common aggregate stops the connection sequence; later
errors are logged and added without stopping subsequent component calls.
A zero aggregate does not prove that every addend succeeded.

The explicit connection call order is common, Bluetooth, GPS, FM, WLAN, ANT.
Common calls chip-type setting, HIF-SDIO, common, STP-UART, STP-SDIO in order;
WLAN calls character-device initialization before gen3. This is source
sequencing, not effect completion, resource lifetime or Makefile link order.

## Limits and handoff

Neither an outer caller of do_connectivity_driver_init nor a gen3 exit call or
direct initcall/module registration appears in the three complete selected
sources. That is a bounded source absence, not a repository-wide absence or a
claim about included header behavior. No exit invocation or reverse exit order
is inferred. The predecessor's accepted lifecycle verdicts remain untouched.

Both request batches are consumed; only four of eight possible new-file slots
were used. No further request is admitted. A new bounded producer audit must
establish the exact external caller, its build selection/registration, and
handling of the final aggregate; an actual teardown reference is independently
needed. No whole-tree search or device operation is authorized by this handoff.

The [freeze](FREEZE.md) independently pins source tuples, 18 exact anchors and
the complete request-evidence object before verifier construction. Run
`python3 verify.py` and `python3 -O verify.py`; the
[validation record](VALIDATION.md) lists actual checks. The verifier protects
evidence integrity but does not establish semantics independently of review.

Only this experiment's new evidence files were edited; WORK_ITEM.md remains
unchanged. No source body, archive, private input, device/SSH, VM, Buildbox,
build, shared-file, staging, commit or push action occurred. Public source
notices were inspected for study only; no vendor implementation or excerpts
were retained and no reuse/firmware/radio authority is claimed. The coordinator
owns acceptance and the workflow measurement; credits are unavailable.
