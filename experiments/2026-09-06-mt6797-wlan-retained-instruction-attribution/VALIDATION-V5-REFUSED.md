# Bootstrap v5 refusal — executed-module cap

Clean dispatch: `ce50845c309169ee769f87f2b51a97de82e190ce`. All nineteen
controlling-contract and eighteen dependency hashes passed before preflight.
Earlier evidence remains unchanged.

[bootstrap-v5.json](bootstrap-v5.json) was frozen at
`2026-09-07T03:03:26Z`, before its first execution:

- File SHA-256:
  `8098ad2af4fd320f1526bd8b975da29d686ec169f048e3d2b098338fc8de8656`.
- Embedded source SHA-256:
  `dbb2cbc45490343f23e62fc4d286306bf695cd04c755d8ad857315d9e0a98a0e`.
- Source digest and syntax-only compilation passed.

Exactly one fresh `/usr/bin/python3.12 -I -S -B` no-ELF preflight ran via the
approved RE-VM shell. The audit hook preceded metadata discovery and remained
active through child exit. Its exact sanitized receipt was:

```json
{"asset_opens_by_phase":{"final-drift":0,"initial-inventory":28,"pre-import-drift":28},"decoder_modules_executed":64,"events":{"cache_write_attempts":0,"native_requests":1,"network_attempts":0,"optional_requests":0,"process_attempts":0,"write_attempts":0},"mapping_checks":[{"nonexecuting_pseudo_rows":12,"nonexecuting_rows_equal_to_baseline":true,"stage":"stdlib-baseline","vdso_full_row_equal":true},{"nonexecuting_pseudo_rows":12,"nonexecuting_rows_equal_to_baseline":false,"stage":"pre-import","vdso_full_row_equal":true},{"nonexecuting_pseudo_rows":13,"nonexecuting_rows_equal_to_baseline":false,"stage":"post-capstone","vdso_full_row_equal":true}],"package_inventory_counts":{"capstone":{"entries":67,"inert":14,"regular_files":64,"sources":25,"stat_only_bytecode":25},"elftools":{"entries":117,"inert":0,"regular_files":104,"sources":52,"stat_only_bytecode":52}},"private_reads":0,"reason":"module map or cap","status":"refused","type":"RuntimeError"}
```

The terminal source loader reached 64 entered package-source executions and refused
the next load under its combined map/cap predicate. This happened during
pyelftools import, after the post-Capstone snapshot and before a completed
post-pyelftools snapshot. The preceding terminal finder admits only names in
the explicit source map, so the recorded count identifies the exhausted
64-module gate; the attempted module name was not retained. No additional
source execution or broader import search followed the refusal.
The counter is incremented before module execution; it does not prove all 64
module bodies completed successfully. The refusal receipt did not retain
execution start/end timestamps, so no exact run-duration claim is made.

Both complete package inventories and pre-import drift passed. The exact
pre-existing `[vdso]` full row remained equal in the stdlib baseline,
pre-import and post-Capstone snapshots. Nonexecuting anonymous/pseudo rows
changed as recorded; they were not admitted as native components. This is not
a complete five-stage mapping or native-closure result. One Capstone native
request occurred; optional lookup, completed pyelftools import, final drift
and named restoration were not reached. There is no successful preflight or
accepted native decoder closure.

The single private-analysis execution remains unused. No ELF was opened or
instruction decoded. No repair or repeated preflight was attempted. The RE
shell was closed, and no private capture files were created. No network,
device, acquisition, build, commit or push operation occurred.

Checks actually run: thirty-seven frozen hash comparisons, source digest and
syntax checks, and one isolated no-ELF preflight. `git diff --check` passed.
Only `bootstrap-v5.json` and this refusal record are the worker delta. No
method freeze, result JSON, normal/optimized verifier or mutation suite exists.

The next discriminating check requires a prospective bounded import-budget
decision: permit enough source-only executions for the already enumerated
complete maps, or a separate bounded module-demand diagnostic. Do not suppress
imports, invent a smaller dependency closure, or silently raise the cap.
