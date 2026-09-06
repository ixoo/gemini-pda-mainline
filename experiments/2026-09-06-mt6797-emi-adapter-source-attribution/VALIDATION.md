# Validation and handoff record

Source requests ran on 2026-09-06. The first tree request began at
`2026-09-06T15:41:55.774253+00:00`; the allowlist and batches were frozen at
`2026-09-06 15:43:18 UTC`. Batch A ran from
`2026-09-06T15:43:47.313773+00:00` to `2026-09-06T15:43:47.718629+00:00`;
batch B ran from `2026-09-06T15:44:14.602608+00:00` to
`2026-09-06T15:44:14.728354+00:00`. Exact per-request timestamps remain in
`search-attempts.json`; both inventory responses remain in `inputs.json`.

Focused checks were repeated from `2026-09-06 15:50:13 UTC` to `2026-09-06 15:50:13 UTC`:

- Normal Python verifier: PASS, 2 batches, 10 distinct files, 11 raw requests,
  2 tree requests and 22 in-memory refusal fixtures.
- Optimized Python (`-O`): the same PASS; safety checks do not depend on assertions.
- In-memory Python syntax and JSON parsing: PASS; no bytecode cache created.
- Local Markdown targets, all-file whitespace/final newlines and bounded
  sensitive-marker scan: PASS for the then-current files; final complete-file
  confirmation follows after this record is added.
- Experiment-local inventory and rights inspection: independently written facts,
  JSON/Markdown and verifier only; no vendor implementation/source-body file,
  firmware, private raw evidence or personal absolute host path.

The initial `./scripts/check-repository` returned `repository_checks=pass`,
checking five files before the README and this validation record were added.
It reported 195 manifest profiles and 37 grandfathered unresolved metadata
items. Local provenance/publication and guard/backend fixtures passed. Linux-only
artifact-provenance validation was explicitly skipped and remains mandatory in
CI; full package validation is deferred to Linux. No kernel build, checkpatch,
DT-schema or device test ran. Final integration must check the complete file set.

No shell file changed; Bash syntax/ShellCheck for this experiment are not
applicable. No source/network repair or verifier repair was needed. No staging,
commit, push, device action, Buildbox, VM, kernel build or firmware inspection was
performed by this worker. Repository checks executed hardware-free fixtures only.

Unresolved risks: source versus deployed/effective configuration, linker-wide
uniqueness and compiler behavior, current secure-firmware identity/acceptance,
raw runtime result, resource/policy ownership and recovery. All nine authority
flags remain false. Independent Sol source review, complete publication gates,
workflow measurement and integration belong to the coordinator.

Final complete-file checks: the seven-file inventory, in-memory syntax, JSON,
local Markdown targets, whitespace and sensitive-marker scan passed by
`2026-09-06 15:50:41 UTC`; `git diff --check` also passed. The second
`./scripts/check-repository` run started after the focused checks at
`2026-09-06 15:50:13 UTC`, checked all seven files and completed successfully by
`2026-09-06 15:50:46 UTC`, with the same explicit Linux-only skips and no
hardware/build access. This final receipt paragraph was added afterward; the
coordinator still owns staged/frozen publication validation.
