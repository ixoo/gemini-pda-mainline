# Bootstrap v6 refusal — pyelftools mapping delta

Clean dispatch: `68ecad404195959b95bda2a8844144ec8f8b5173`. All twenty-three
controlling-contract and eighteen dependency hashes passed. Earlier evidence
remains unchanged.

[bootstrap-v6.json](bootstrap-v6.json) was frozen at
`2026-09-07T03:21:06Z`, before its first execution:

- File SHA-256:
  `94b876a01eef5d781499f0462b04a947f0ddd7742df8a6880e667a4745c390c4`.
- Embedded source SHA-256:
  `a7488e0285284e73b2916008d0fce1dc33e5eaf669f654ef4439512636fb9db4`.
- Source digest and host syntax-only compilation passed.

Exactly one fresh `/usr/bin/python3.12 -I -S -B - preflight` process ran via
the approved RE-VM shell. The audit hook preceded metadata discovery and
remained active until child exit. Its exact sanitized receipt was:

```json
{"asset_opens_by_phase":{"final-drift":0,"initial-inventory":28,"pre-analysis-drift":0,"pre-import-drift":28},"callback_count":0,"callback_state":"absent","completed_modules":73,"completed_utc":"2026-09-07T03:21:28.557636+00:00","decoder_modules_executed":73,"entered_modules":73,"events":{"cache_write_attempts":0,"native_requests":1,"network_attempts":0,"optional_requests":0,"process_attempts":0,"write_attempts":0},"mapping_checks":[{"nonexecuting_pseudo_rows":11,"nonexecuting_rows_equal_to_baseline":true,"stage":"stdlib-baseline","vdso_full_row_equal":true},{"nonexecuting_pseudo_rows":11,"nonexecuting_rows_equal_to_baseline":false,"stage":"pre-import","vdso_full_row_equal":true},{"nonexecuting_pseudo_rows":12,"nonexecuting_rows_equal_to_baseline":false,"stage":"post-capstone","vdso_full_row_equal":true},{"nonexecuting_pseudo_rows":12,"nonexecuting_rows_equal_to_baseline":false,"stage":"post-pyelftools","vdso_full_row_equal":true}],"mode":"preflight","package_inventory_counts":{"capstone":{"entries":67,"inert":14,"regular_files":64,"sources":25,"stat_only_bytecode":25},"elftools":{"entries":117,"inert":0,"regular_files":104,"sources":52,"stat_only_bytecode":52}},"private_reads":0,"reason":"pyelftools mapping delta","started_utc":"2026-09-07T03:21:28.327139+00:00","status":"refused","type":"RuntimeError"}
```

The complete inventory-derived map contained 77 sources. Of these, 73 unique
module bodies were entered and all 73 completed; the earlier execution-cap
problem did not recur. Both package inventories and pre-import drift passed.
The exact pre-existing vDSO full row remained unchanged through stdlib
baseline, pre-import, post-Capstone and post-pyelftools snapshots.

The file-backed mapping identity dictionary after pyelftools import differed
from the post-Capstone dictionary. The bootstrap refused at that comparison,
before engine construction, optional-module lookup, final native-closure
acceptance, restoration or callback. Its receipt does not retain the changed
path/identity or distinguish added, removed and identity-changed components.
Do not infer a specific library, extension, dependency or benign cause.
One counted Capstone native request occurred; no optional lookup occurred.

No repair, second preflight, extra mapping inspection, analysis-mode child or
private opening followed. The callback remained absent and the single private
analysis is unused. The RE shell was closed, and no private capture files were
created. No network, acquisition, device, build, commit or push occurred.

Checks actually run: forty-one frozen hashes, bootstrap source digest and
syntax, and one isolated no-ELF preflight. `git diff --check` passed. Only
`bootstrap-v6.json` and this refusal record are the worker delta. No successful
method freeze, instruction result or normal/optimized mutation verifier exists.
The analysis-mode callback/pipe/final-drift branch remains unexecuted.

The next discriminating check requires a prospective diagnostic retaining the
bounded exact file-backed identity delta around pyelftools import, including
which module-import event introduced any component. That evidence can separate
a missing standard-library baseline dependency from a package native load or
identity drift. This refusal does not authorize a native-route exception,
preloading an unverified component, or a changed bootstrap retry.
