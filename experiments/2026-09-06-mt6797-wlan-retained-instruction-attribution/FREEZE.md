# V10 source-first construction freeze

Status: frozen for independent review; **not execution-admitted**. The construction
dispatch at `342438085bef1feb081b62961b3d4e8e1c7fb2fa` was verified clean and
equal to `origin/main`. It authorizes only these source inputs, this record and
minimal work-item/input state. [Amendment 26](AMENDMENT-26.md) controls the future
one-run protocol. No VM session, package entry, private open/read, parser or
decoder execution, fixture, device access, build, commit or push occurred.

## Immutable order and identities

| Input | Frozen UTC | Container SHA-256 | Embedded source SHA-256 |
| --- | --- | --- | --- |
| [bootstrap-v10.json](bootstrap-v10.json) | 2026-09-07T09:07:05.938401Z | 4e599c07d3fad2aabc6982383dbbc92dc9796136f388263045e59593cfcc4d8c | bd42ce6c91e1733f2fd0e849fae43d090849453c89c4a6f302c714f04d1dd633 |
| [method.json](method.json) | 2026-09-07T09:10:03.722181Z | f85e00a2a2d0b64b9af7369be1ef6d564d5b28aa2dbd5d791f53f0dbd656ffe1 | d461847e4195f8f2aa5613d1f5345c8fffe74accffb92ee5f07c732cd24518eb |

The bootstrap was created and hashed before method construction was finalized.
The method binds both bootstrap hashes; this external record binds both complete
containers, avoiding circular source/container hashes. No execution followed
either freeze. The construction-time inputs SHA-256 is
`c4f1f32781a6c0012a84fdbc01a331f5963c65a8de3d31d581530922199e4c91`; its exact UTF-8 content is embedded
in the bootstrap and remains recoverable at the dispatch commit. Current
[inputs.json](inputs.json) adds the finished freeze pins and current
[WORK_ITEM.md](WORK_ITEM.md) state; it does not retroactively replace the
construction inputs. All 98 construction dependency/control pins passed before
construction. Existing V9 source/result/validation remain unchanged.

Both inputs bind the accepted V9 tool identity, canonical SHA-256
`4baaa1020f2d895a688c6675b5091aed77d63d3a9ad9103316c4dbb6e830b639`.
The method contains the complete literal identity, including losslessly
preserved integer fields, and accepted v3 interval metadata. The bootstrap
embeds the same identity and input constants in its source. No private path,
ELF content, disassembly or historical excluded raw result is embedded.

## Closed V9 delta and analysis surface

The full source-only checker and its 106 named checks are embedded as
`construction_source_check_program` and `construction_checks` in the
bootstrap. It compares complete AST function bodies, helper-import order,
lifecycle stages, exact module set, stat/content budgets, and direct data flow.
It never imports or executes either candidate source.

The only removed V9 function is `preflight_stable`, replaced by explicit
analysis-state gates. The closed changed-function set is:
`SourceLoader`, `audit`, `fail`, `main`, `no_late_drift`, `page_size_reference`, `queue_audit`, `queue_fstat`, `queue_identity`, `queue_lstat`, `queue_preload`, `resource_profile`, `snapshot`.
The closed added-function set is:
`analysis_args`, `analysis_identity_stable`, `analysis_require`, `analysis_state`, `analysis_success_counters`, `canonical_sha`, `close_method_pipe`, `close_private_descriptor`, `load_method`, `method_audit`, `post_analysis_integrity`, `private_cleanup_one`, `private_read_once`, `release_private_buffer`, `schema_check`, `unique_method_pairs`, `validate_analysis_result`.
All other top-level function ASTs remain equal to V9. The checker further
requires exact inherited bodies modulo each named small delta for the queue,
resource and snapshot helpers. New audit routes are phase-specific, not general
filesystem or evaluator permission.

The seven A26 stages enter only after `post-engine`, before restoration;
all 20 inherited outer stages and 12 queue stages retain order. There are 15
map gates, four tree/asset phases, 25 queue content/audit/descriptor reads,
54 queue lstats and 50 queue fstats on success. The accepted 73 package bodies
remain the complete entered-module set; no late parser import or compilation
is admitted. Method/private counters remain zero through `post-engine`.
There is one existing engine and one future method compile/exec/callback.
The exact argument schema, compiler policy, result schema, operation caps,
collector requirements, parser routes and refusal classes are in the two
containers, not inferred from any future observation.

The private route is one read-only/no-follow open, three descriptor stat checks
and one high-level bounded read (64 MiB plus a sentinel), followed by buffer
hash verification. The cap is a prospective bound, not an observed ELF size;
one high-level read is not a promise of one underlying syscall. All parser
reads use one counted in-memory reader over one BytesIO and one ELFFile.
Final integrity hashes that same buffer and stats the same descriptor without
a file reread. Cleanup attempts close both descriptors and the in-memory stream
while retaining the first refusal; no accepted partial semantics survive refusal.

The method independently validates raw ELF header/program/section/symbol records
against the enumerated pyelftools APIs; direct API/helper spellings and their
construction counts are frozen in `method_api`. It performs 392 one-word
Capstone/raw control decodes, four bounded traversals, one 5,003,312-word raw BL
scan, one relocation scan and one aligned allocated-address scan. Each candidate
class caps at eight. Relocation interpretation admits only AArch64 NONE and
RELA ABS64 `S+A` with defined, bounded targets; every other encountered
relocation route refuses. No supplementary ELF, decompression, alternative
symbol table, new module route, indirect dispatch or additional caller body is
admitted. Decode disagreement, unsupported parser/layout/relocation state and
budget overflow terminate globally. Classified indirect control flow remains
bounded unresolved, not evidence of a missing edge or safe teardown.

## Checks actually run and remaining handoff

Host source-only checker passed under normal Python and `python3 -O`, each
covering compile modes 0, 1 and 2, 106 AST/data-flow/budget/schema/privacy checks
and no assert-dependent gates. Embedded source whitespace, SPDX license,
no-private-path/content review, lossless identity/hash bindings, dependency pins,
local Markdown links and `git diff --check` are the final handoff checks.
No shell or kernel files changed, so ShellCheck, shell syntax and kernel builds
are not applicable. No synthetic ELF/decoder fixture or behavioral test ran.

Independent Sol review and publication/integration are still required.
The future execution custodian must be separately named and dispatched; its
one-run budget is unconsumed. The result verifier and execution collector are
future owned work, not produced here. Runtime import/API compatibility,
first-refusal/restoration behavior, actual private layout and decoder agreement
remain untested. A source compile cannot establish hardware support, binary
attribution success or a general Python security boundary. No source changes
after this freeze are admitted without a new reviewed identity.
