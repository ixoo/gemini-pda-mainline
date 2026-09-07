# Retained WLAN instruction attribution — preflight refusal

No private ELF analysis has run. The single analysis execution remains unused.
No binary linkage, teardown, runtime or hardware conclusion is established.

## Dependency-path clarification

The integrator clarified the six `source_dependencies` paths at dispatch
`53d45455d76258c7d8fb06aa2cf619f88ace0ac3`:

- `lifecycle_inputs`, `lifecycle_verdicts`, and `lifecycle_freeze` name
  `inputs.json`, `verdicts.json`, and `FREEZE.md` respectively under
  `../2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/`.
- `producer_inputs`, `producer_verdicts`, and `producer_freeze` name those
  same three filenames under
  `../2026-09-06-mt6797-connectivity-producer-source-attribution/`.

All eighteen dependency hashes in [inputs.json](inputs.json) passed after this
clarification. The earlier guessed lifecycle path was not the intended
dependency; its mismatch does not show drift of a frozen dependency.
The integrator also confirmed that the sixteen-call cap includes every
reachable `BL` callsite across all four traversals, without selecting a subset.

## Mandatory tool-preflight stop

Read-only installed-tool introspection through `./scripts/dev-vm re-shell`
reported Python 3.12.3, pyelftools 0.30, Capstone binding 4.0.2 and native
Capstone version tuple `(4, 0, 1024)`. No instruction was decoded and no ELF
was opened. The native library version query was tool introspection only.

The installed Capstone binding loads a bare `libcapstone.so.4` and optionally
imports `ccapstone`. During metadata preflight, a process-local loader wrapper
selected the exact installed library path and a `sys.modules` sentinel disabled
the optional module. Installed source files were not changed.

The loaded-file inventory then refused the selected symlink
`/usr/lib/python3.12/sitecustomize.py`. The contract requires nonsymlink
component identities and stopping on a symlink. Enumeration stopped there;
there is no complete frozen component manifest, collector or method. The RE
shell was closed. No private evidence files were created or modified.

## Escalation and tests actually run

- Exact dispatch HEAD and initially clean worktree verified.
- Eighteen dependency SHA-256 comparisons passed.
- Accepted v3 intervals inspected; no earlier excluded raw output accessed.
- Installed-tool origin, version, hash and size inventory attempted; refused
  the symlink above before completing the inventory.
- No repair attempt, private-content access, instruction analysis, verifier
  execution, device operation, network research, build, commit or push.

The unresolved question is whether an explicitly site-disabled interpreter
startup is admitted, with only exact installed package paths and a new complete
pre-content tool inventory. The next discriminating check is a separately
authorized `-I -S -B` startup origin inventory demonstrating that the symlinked
startup hook was neither loaded nor selected. Do not resume private analysis
under this refusal or treat that proposed check as an accepted method.
