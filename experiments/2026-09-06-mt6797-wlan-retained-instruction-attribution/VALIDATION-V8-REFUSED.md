# V8 preflight refusal

## Frozen dispatch and execution

- Dispatch: `62fd1d9065f496a4577caa45dfe3f2048e68aabe`.
- Contract: [WORK_ITEM.md](WORK_ITEM.md), [Amendment 17](AMENDMENT-17.md),
  [Amendment 18](AMENDMENT-18.md), and every inherited pinned control.
- [inputs.json](inputs.json) SHA-256:
  `964f1223ac59d55fac9fa9a4d6d0c6b0fc4faf88884326ed7be0cb190ebdef10`.
  All 70 hashes passed: 52 controlling files and 18 dependencies.
- [bootstrap-v8.json](bootstrap-v8.json) SHA-256:
  `bc769538ecf3edad9361294f313bd96099cc4da1d848bc875cbd1a13b7ff6f75`.
- Embedded source SHA-256:
  `3fe4fb8bc87cd46774944c4c10a7d892122ca3dee94ee7cfa39ba0ccfb70332b`.
- Freeze: `2026-09-07 05:06:26 UTC`, before the sole execution.
- Sole no-ELF preflight: `2026-09-07T05:07:16.882715+00:00` through
  `2026-09-07T05:07:17.374539+00:00`.
- Approved RE shell; frozen source supplied on stdin to
  `/usr/bin/python3.12 -I -S -B - preflight`, with empty
  `DEBUGINFOD_URLS`, no-user-site and no-bytecode environment controls.
  No source file, analysis database or private input was created in the guest.

## Observed outcome

The child refused with `RuntimeError: nonfrozen or repeated extension load`.
The frozen extension audit raises this before allowing an unadmitted extension
load. Its receipt does not identify the attempted module or origin. Do not
infer that identity from import progress or call it an admitted dependency.

The exact resource query passed its bounded call/return gates:

- The pre-entry AST checks accepted the sole direct zero-argument
  `PAGESIZE = resource.getpagesize()` assignment at frozen source line 17,
  following the resource import at line 16.
- The separately owned reference query ran once:
  `SC_PAGE_SIZE` mapped value 30, returned integer 4096.
  Its module objects, mappings, resource counters and guarded event counters
  were unchanged.
- Resource lookup/create/exec/extension/cached request/function call/function
  return counts were each one, with zero function exceptions. The profile state
  reached `returned`; this includes the exact callable, original caller frame
  and line, live binding and event-order checks.
- The complete inventories contained 25 Capstone and 52 pyelftools sources.
  56 mapped module bodies entered and 53 completed before refusal.
- Eight recorded mapping checks preserved the exact full vDSO row. The
  pre-call file-backed dictionary and permission/offset rows matched the
  post-resource baseline.
- No engine was constructed. Method and callback were absent at all six
  recorded method-state gates. Callback invocations and private opens were zero.
  Optional-route attempts, writes, cache writes, network and process attempts
  were zero. One already admitted Capstone native request occurred.

The pyelftools import did not complete. Therefore its post-import `PAGESIZE`
global value/stability, complete module completion, post-import mapping equality,
engine construction, optional route, final component drift and success-path
restoration were **not proved**. The `page_value: null` receipt field means the
post-import value check was not reached; it does not contradict the observed
resource `c_return`. No general purity or side-effect-free claim follows.

The refusal handler restored named Python hooks/endpoints as coded, then exited.
The outer RE shell also exited. The failure path has no independent restoration
receipt; do not promote handler execution to the unrun success-path proof.

## Checks actually run

- Clean dispatch identity/status check.
- All 70 pinned control/dependency SHA-256 comparisons: passed.
- Host in-memory Python AST parse and compile-only checks before freeze: passed.
- AST checks for unique function definitions, no `assert`, and one exact
  `os.sysconf("SC_PAGE_SIZE")` reference call: passed.
- Original-caller tuple wrapper/helper and exact resource counter source review.
- Frozen JSON/embedded-source digest verification and compile-only check: passed.
- Exactly one approved RE no-ELF preflight: refused as recorded below.
- Final owned-file JSON/source syntax, local Markdown links, privacy/license
  checks and `git diff --check`: passed.

No kernel build, device probe, network acquisition, private ELF access, private
analysis, normal/optimized final-result verifier or hardware test ran.

## Escalation and handoff

The one v8 preflight budget is consumed. No repair or second run is admitted.
The single private analysis remains unused. No `method.json`, analysis result,
edge inventory, final verifier or support claim was produced.

Unresolved question: which extension event was attempted after the accepted
resource return, and what exact frozen source/import request led to it?

The next discriminating check requires a prospective, separately frozen,
bounded no-ELF diagnostic that captures the **first refused** extension event's
sanitized module/origin and exact frozen-caller join before terminating without
loading it. Such a diagnostic is a proposal, not an action authorized or
performed here. Do not enlarge the extension allowlist or reuse this consumed
preflight.

## Complete sanitized child receipt

This is the child JSON receipt, reformatted without changing its values. The
shell prompt and host-private working path are excluded. No instruction bytes,
disassembly, private ELF path, device identifier or proprietary material is
included.

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
  "completed_modules": 53,
  "completed_utc": "2026-09-07T05:07:17.374539+00:00",
  "decoder_modules_executed": 56,
  "engine_count": 0,
  "entered_modules": 56,
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
      "nonexecuting_pseudo_rows": 14,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "post-capstone",
      "vdso_full_row_equal": true
    },
    {
      "nonexecuting_pseudo_rows": 14,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "pre-stdlib-resource",
      "vdso_full_row_equal": true
    },
    {
      "nonexecuting_pseudo_rows": 14,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "post-stdlib-resource",
      "vdso_full_row_equal": true
    },
    {
      "nonexecuting_pseudo_rows": 14,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "pre-page-reference",
      "vdso_full_row_equal": true
    },
    {
      "nonexecuting_pseudo_rows": 14,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "post-page-reference",
      "vdso_full_row_equal": true
    },
    {
      "nonexecuting_pseudo_rows": 14,
      "nonexecuting_rows_equal_to_baseline": false,
      "stage": "resource-c-call",
      "vdso_full_row_equal": true
    }
  ],
  "method_state_checks": [
    {
      "callback_count": 0,
      "callback_present": false,
      "callback_state": "absent",
      "method_present": false,
      "mode": "preflight",
      "pipe_opens": 0,
      "private_opens": 0,
      "stage": "post-method-input"
    },
    {
      "callback_count": 0,
      "callback_present": false,
      "callback_state": "absent",
      "method_present": false,
      "mode": "preflight",
      "pipe_opens": 0,
      "private_opens": 0,
      "stage": "pre-resource-preload"
    },
    {
      "callback_count": 0,
      "callback_present": false,
      "callback_state": "absent",
      "method_present": false,
      "mode": "preflight",
      "pipe_opens": 0,
      "private_opens": 0,
      "stage": "post-resource-preload"
    },
    {
      "callback_count": 0,
      "callback_present": false,
      "callback_state": "absent",
      "method_present": false,
      "mode": "preflight",
      "pipe_opens": 0,
      "private_opens": 0,
      "stage": "pre-page-reference"
    },
    {
      "callback_count": 0,
      "callback_present": false,
      "callback_state": "absent",
      "method_present": false,
      "mode": "preflight",
      "pipe_opens": 0,
      "private_opens": 0,
      "stage": "post-page-reference"
    },
    {
      "callback_count": 0,
      "callback_present": false,
      "callback_state": "absent",
      "method_present": false,
      "mode": "preflight",
      "pipe_opens": 0,
      "private_opens": 0,
      "stage": "resource-c-call"
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
  "page_reference": {
    "count": 1,
    "guard_events_unchanged": true,
    "mapped_value": 30,
    "mapping_unchanged": true,
    "module_objects_unchanged": true,
    "name": "SC_PAGE_SIZE",
    "owner": "stdlib-page-size-reference",
    "resource_events_unchanged": true,
    "value": 4096
  },
  "page_value": null,
  "private_reads": 0,
  "reason": "nonfrozen or repeated extension load",
  "resource_counters": {
    "cached_requests": 1,
    "create_module": 1,
    "exec_module": 1,
    "extension_audit": 1,
    "find_spec": 1,
    "function_attempts": 1,
    "function_exceptions": 0,
    "function_returns": 1
  },
  "resource_state": "returned",
  "started_utc": "2026-09-07T05:07:16.882715+00:00",
  "status": "refused",
  "type": "RuntimeError"
}
```
