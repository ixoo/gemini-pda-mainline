# V7 preflight refusal: resource function attempt

The single [v7 bootstrap](bootstrap-v7.json) preflight refused a Python
`c_call` event whose callable reported module `resource`. This is the
[Amendment 12](AMENDMENT-12.md) function-invocation stop, after the exact
resource preload and cached resource reuse within the pyelftools import had
passed. No successful preflight receipt exists; no method or private analysis
was admitted.

## Freeze and chronology

- Dispatch: `b86d76d623c6ea5c0b9346ec98f99317cb982222`; Astra Medium.
- All 39 controlling and 18 explicit dependency-path SHA-256 pins passed.
- [Amendment 13](AMENDMENT-13.md) resolved the inventory ordering before any
  v7 construction: both complete inventories precede all package source entry.
- Bootstrap frozen `2026-09-07 04:17:29 UTC`, file SHA-256
  `d17ffd1ce29afa0be12c9a5feef209a9062032ab2170b344b2edb313d6ce76fa`;
  source SHA-256
  `db91247181114d2632ea2790887d26b141e3269c06fc95957b1e3d8d62c3d48e`.
- Exactly one fresh `/usr/bin/python3.12 -I -S -B` preflight through the
  approved RE-VM shell, from `2026-09-07T04:18:03.461590+00:00` to
  `2026-09-07T04:18:03.700995+00:00`.
- The RE shell was closed immediately after refusal. No second run, repair,
  additional source inspection or device/build action followed.

## Sanitized receipt

```json
{
  "asset_opens_by_phase": {
    "final-drift": 0,
    "initial-inventory": 28,
    "pre-analysis-drift": 0,
    "pre-import-drift": 28
  },
  "callback_count": 0,
  "callback_state": "absent",
  "completed_modules": 27,
  "completed_utc": "2026-09-07T04:18:03.700995+00:00",
  "decoder_modules_executed": 28,
  "entered_modules": 28,
  "events": {
    "cache_write_attempts": 0,
    "native_requests": 1,
    "network_attempts": 0,
    "optional_requests": 0,
    "process_attempts": 0,
    "write_attempts": 0
  },
  "mapping_checks": [
    {
      "nonexecuting_pseudo_rows": 13,
      "nonexecuting_rows_equal_to_baseline": true,
      "stage": "stdlib-baseline",
      "vdso_full_row_equal": true
    },
    {
      "nonexecuting_pseudo_rows": 13,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "pre-import",
      "vdso_full_row_equal": true
    },
    {
      "nonexecuting_pseudo_rows": 13,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "post-capstone",
      "vdso_full_row_equal": true
    },
    {
      "nonexecuting_pseudo_rows": 13,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "pre-stdlib-resource",
      "vdso_full_row_equal": true
    },
    {
      "nonexecuting_pseudo_rows": 13,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "post-stdlib-resource",
      "vdso_full_row_equal": true
    }
  ],
  "mode": "preflight",
  "package_inventory_counts": {
    "capstone": {
      "entries": 67,
      "inert": 14,
      "regular_files": 64,
      "sources": 25,
      "stat_only_bytecode": 25
    },
    "elftools": {
      "entries": 117,
      "inert": 0,
      "regular_files": 104,
      "sources": 52,
      "stat_only_bytecode": 52
    }
  },
  "private_reads": 0,
  "reason": "resource function invocation refused",
  "resource_counters": {
    "cached_requests": 1,
    "create_module": 1,
    "exec_module": 1,
    "extension_audit": 1,
    "find_spec": 1,
    "function_attempts": 1
  },
  "started_utc": "2026-09-07T04:18:03.461590+00:00",
  "status": "refused",
  "type": "RuntimeError"
}
```

## What passed and what remains unknown

Both package inventories and pre-import drift completed at the exact 25 + 52
source-map cardinality. Capstone's import/native closure completed before the
resource phase. The exact resource spec, extension suffix, frozen file
identity, ELF64/little-endian/AArch64/ET_DYN format, bounded existing-baseline
`DT_NEEDED` closure, and sole four-row added mapping passed before pyelftools
source execution continued.

The resource counters show one spec lookup through the terminal finder, one
extension-load audit event, one loader creation, one execution, and one
identical cached reuse. The profiler then raised on the first attempted
resource-function call. It records only the callable's module-class match and
aggregate attempt count, not its function name, caller or return value. No
specific function, callsite, effect, successful function completion, benign
page-size query or resource-limit operation is established by this receipt.

There were 28 entered and 27 completed mapped modules. Post-pyelftools mapping,
engine construction, optional-route exercise, final package/component drift,
and the successful named-restoration receipt were not reached. The refusal
handler attempts hook/path restoration, but this receipt does not independently
certify those restoration predicates; process exit is the cleanup boundary.
The five completed mapping stages retained exact in-process vDSO row equality.
Nonexecuting pseudo rows changed and were not promoted to native components.

The one native request was Capstone's; optional requests and filesystem/cache,
network, process and private-read counters were zero. Callback count was zero
and state absent. The private-analysis budget is still unused. No engine,
method, instruction decoding, private file, raw mapping capture or database was
created. No hardware support or resource-extension usability is claimed.

## Checks and escalation

Tests actually run: 57 dependency hashes; frozen-source SHA-256 and Python syntax
compilation before execution; the one guarded no-ELF preflight; host refusal
receipt/source-identity predicates; relative Markdown links; and
`git diff --check`. No hardware test, kernel build, second preflight or private
analysis was run.

Evidence: exact preload and cached reuse succeeded; the prohibited-function
guard then recorded one attempt and refused. Attempts: one v7 preflight, no
repair. Unresolved question: which exact resource callable and frozen source
join caused that attempt, and whether its precise semantics can be admitted.
Next discriminating check requires a prospective bounded static/callsite
diagnostic identifying that function without executing it or weakening the
blanket refusal. Do not infer or whitelist a guessed function.

Only `bootstrap-v7.json` and this refusal record are new. Every predecessor is
unchanged. The v7 source also corrects a private-stream stat comparison inherited
from v6; that private branch was not exercised and has no runtime validation.
