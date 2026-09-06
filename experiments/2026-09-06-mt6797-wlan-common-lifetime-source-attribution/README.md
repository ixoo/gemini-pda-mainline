# MT6797 WLAN/common callback lifetime attribution

The pinned source does **not** supply one uniform retained-common-resource
contract around every WLAN probe. The normal queued path and late registration
must be distinguished. This is an offline source-attribution handoff, not a
driver, device protocol, runtime observation or Linux ownership/reuse approval.

## Frozen evidence and result

The [work item](WORK_ITEM.md) uses Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a` and repository parent
`a770a606ef28244d143fe270f76264ea6d0391d0`.
[Inputs](inputs.json) pin every raw URL, whole-file SHA-256, Git blob identity,
size and line count, plus the predecessor input digests.
[Search accounting](search.json) records all 26 successful requests in three
predeclared batches: 17 unique regular files, of which four are new relative to
the predecessor. The third batch exhausts the fetch budget. No source body,
archive, checkout, binary or source excerpt was retained on disk.

| Acceptance edge | Verdict | Exact boundary |
| --- | --- | --- |
| Callback object, assignment and direction | Resolved | WLAN supplies callbacks; common copies and invokes them. |
| Function-on through firmware-buffer lifetime | Unresolved | Conditional source edges joined; common build guard and actual built-in init caller not closed. |
| Common resources held across every callback | Contradicted | Late-registration path bypasses normal common-power acquisition/state promotion. |
| Failure propagation and retained/released state | Resolved | Inspected return and bookkeeping behavior only; not successful hardware effects. |
| Off/unregister/probe-failure cleanup | Unresolved | Distinct visible orders; no symmetric synchronized resource-release guarantee. |

[Verdicts](verdicts.json) contain the five independent claims, boundaries,
missing edges, next discriminators and exact file/line/symbol citations.
“Resolved” is deliberately narrower than active-image or hardware equivalence.

## Joined chronology and the counterexample

The source identities and line anchors below are named citation keys in
`verdicts.json`; the raw pinned URLs are in `inputs.json`.

1. The Wi-Fi makefiles select gen3/AHB for the MT6797 configuration and define
   built-in mode. The HIF header sets platform-device mode, and the gen3
   configuration selects WMT mode (`config`, `wlan_make`, `hif_select`,
   `hif_objects`, `wmt_mode`, `platform_mode`).
2. `initWlan` supplies `wlanProbe` and `wlanRemove` to `glRegisterBus`.
   The AHB platform probe supplies `HifAhbProbe` and `HifAhbRemove` in
   `MTK_WCN_WMT_WLAN_CB_INFO`. Common registration copies those pointer values,
   not the stack object's lifetime (`init_exit`, `bus_register`,
   `registration`, `assignment`).
3. The ordinary function-on caller enqueues an operation and waits. The WMT
   worker dispatches its operation table, checks/establishes WMT FUNC_ON, calls
   the Wi-Fi callback, and promotes Wi-Fi status only on zero return. HIF calls
   `wlanProbe`, which maps the local firmware buffer, calls
   `wlanAdapterStart`, then unmaps it after that call returns. The nearby
   `request_firmware` implementation is disabled (`queue_request`, `queue`,
   `worker`, `op_dispatch`, `func_on`, `wifi_on`, `probe`,
   `firmware_caller`, `firmware_mapping`, `firmware_disabled`).
4. When the callback is absent, common Wi-Fi-on sets a pending flag and returns
   -2. Core failure can request common power-off when all listed consumers are
   off. The system-state reset clears two subsystem bitsets, but does not clear
   that pending flag. Later registration invokes the callback directly from
   the flag without reacquiring common power or performing normal Wi-Fi state
   promotion in its body (`wifi_on`, `func_on`, `state_reset`,
   `assignment`). This is a composable source counterexample, not an observed
   runtime event or a proof of race reachability.
5. The host-awake request is put after the queue wait returns, including its
   timeout branch. It is not an enduring WLAN-provider reference. The common
   power bit is changed before the platform effect returns, and core power-off
   bookkeeping can be set despite an effect error. State values do not certify
   rails or clocks (`queue_request`, `queue`, `power_bits`, `common_off`).

Function-off calls HIF remove, which calls WLAN remove before its PALDO-off
request. Probe failure instead calls WLAN remove directly after WLAN's own
failure switch; it does not call the full HIF-remove path. Unregister calls WLAN
remove before platform-driver unregister; the platform-remove body only clears
common callbacks. The selected makefile is built-in while the remove member
uses `__exit_p`; no module-unload or platform-remove invocation guarantee is
asserted (`wifi_off`, `func_off`, `remove`, `probe_failure`,
`bus_register`, `platform_driver`, `assignment`).

The structured state `wmt_wlan_unreg_body_clears_callbacks=true` describes only
that function body's assignments. `built_in_unregister_reaches_callback_clear`
is `null`: unresolved, not a claim that built-in execution does or does not
reach those assignments. The cleanup verdict remains unresolved.

## Handoff and limits

No additional source read is admitted under this item. The unclosed common
`CFG_FUNC_WIFI_SUPPORT` definition/build/include path, actual built-in
initialization/exit caller, `__exit_p` selection, queue timeout ownership and
concurrent callback synchronization need a fresh bounded contract. Do not infer
a retained common-provider reference from the normal-path bookkeeping or from
the firmware buffer's independent local lifetime.

The two deliberate contextual whole-function rereads are recorded. Locator
output also repeated incidental surrounding lines; strict interpretation of
the reread cap is explicitly left for integration review. Initial manually
entered freeze-time labels were not measurements and have been removed.
Allowlists were patched before their corresponding requests; exact measured
request timestamps remain, with ordered rather than invented timed freeze
claims. These accounting caveats must not be hidden by verifier success.

Run `python3 verify.py` and `python3 -O verify.py` from this directory.
The [validation record](VALIDATION.md) lists checks actually run.
The verifier checks offline record consistency and refusal boundaries; it does
not refetch source, prove semantics or validate hardware. Source study does not
grant code/API reuse or firmware redistribution rights.

The first-review [independent freeze](FREEZE.md) fixes all 17 source identity
tuples and 42 exact citation anchors. It prevents coordinated edits to mutable
records from silently redefining the expected evidence; all 13 reused tuples
also match the separately pinned predecessor field-for-field.

Only this experiment directory was edited. No device, SSH, private input, VM,
Buildbox, kernel source/configuration, staging, commit or push action occurred.
The integration owner records the accepted/excluded efficiency measurement;
credits are unavailable. Shared roadmap, hardware-support and queue ownership
remain unchanged.
