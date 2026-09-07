# V10 single-run refusal and public-result validation

## Outcome and authority

The separately dispatched V10 process at published clean parent
`f1fef5e6bb83d2a2e85b33f9a97e9256b8b11a55` **refused at
`initial-inventory`** with closed class `validation-failure`. Startup passed;
the remaining 25 outer stages and all 12 queue stages were not evaluated.
The one-run budget is consumed. No retry, repair, second input read, separately
dispatched package probe or follow-up diagnostic was performed after refusal.

The sole RE-VM custodian was `/root/runtime_identity_specialist` (Astra Medium).
The child exited with status 2, the outer collector completed, and the approved
RE shell exited before result construction. Custody is released.
No device, build, network/acquisition, firmware, radio, commit or push action
occurred. Independent review and integration remain with Sol Medium and
`/root`; no hardware/support or roadmap file changed.

## Frozen inputs and chronology

All 101 current control/dependency pins and the exact
[bootstrap](bootstrap-v10.json), [method](method.json), and
[source freeze](FREEZE.md) hashes passed before RE access. HEAD and
`origin/main` both equaled the exact dispatch commit, with a clean worktree.
Dispatch-time inputs SHA-256:
`56efd71170f662acdcef0be79ad1fd39c7cc9159a929976535c3684aec35d842`.
The source/container chronology and older construction-input digest remain
immutable in [FREEZE.md](FREEZE.md); state updates do not redefine that snapshot.

| Event | UTC |
| --- | --- |
| Bootstrap source freeze | 2026-09-07T09:07:05.938401Z |
| Method freeze | 2026-09-07T09:10:03.722181Z |
| Published-parent/pin check | 2026-09-07T09:28:44.818203Z |
| Collector start | 2026-09-07T09:31:06.385620Z |
| Child launch | 2026-09-07T09:31:06.385718Z |
| Child receipt start | 2026-09-07T09:31:06.434831Z |
| Child receipt completion | 2026-09-07T09:31:06.466116Z |
| Child exit observed | 2026-09-07T09:31:06.473461Z |
| Collector cleanup complete | 2026-09-07T09:31:06.475379Z |
| Shared result-freeze marker recorded | 2026-09-07T09:32:39.040881+00:00 |
| Last of the three result files written (host mtime) | 2026-09-07T09:33:03.027003Z |
| Verifier first created (host birth time) | 2026-09-07T09:35:41.282602Z |

The shared `results_frozen_utc` field marks the start of result recording, not
the final file write. All three completed files were hashed before verifier
construction; their exact hashes below, not mutable filesystem timestamps,
bind the retained result identities.

The child invocation used the unchanged frozen source through stdin and
`/usr/bin/python3.12 -I -S -B - analysis`, with the exact frozen hash/descriptor
argument schema. The private path remained private. One read-only method pipe
was provided; the writer supplied 65,536 bytes before the refused child closed
its inherited descriptor, causing a caught broken pipe. The child never opened
or read the method pipe. No method file or copied ELF was staged in the VM.

The collector disabled debuginfod/download and Python cache behavior; inherited
Python/library override variables were removed. It set umask 077, checked
space below the existing managed RE work root, created one fresh mode-0700
child, and retained only the two named mode-0600 stdout/stderr captures.
Cleanup handling was installed immediately, descriptors were closed and the
writer joined. A 180-second collector timeout was not reached. The child
performed no guarded write/network/process attempt. This guard is not a claim
of a general Python security boundary or OS network sandbox.

## Exact partial evidence

[bootstrap-v10-result.json](bootstrap-v10-result.json) preserves the complete
sanitized receipt. Its canonical receipt SHA-256 is
`0513ca82fe476206cf29463038bb706e288f2029f9490f2d19bc5eff9e953747`.

- Package bodies entered/completed: `0/0`; module budget not yet established.
- Asset opens in every named phase: zero.
- Engine, method JSON/compile/exec/construction/callback, private open/read,
  ELF/BytesIO, decoder, traversal and scan counters: all zero.
- One baseline maps open/read; its vDSO equality and nonexecuting-baseline
  equality fields are true, with 14 nonexecuting pseudo rows. Those relational
  fields do not prove equality to the accepted V9 complete tool identity.
- Queue, resource and profile operation counters: zero.
- Import, finder, path and profile restoration attempts succeeded. Native and
  resource-loader restorations were not applicable. Releasing the empty private
  buffer reference succeeded; unopened private/method handles were not applicable.
  The child/shell exit closed any remaining inherited descriptors.
- No accepted tool identity, mapping, decode, traversal, edge or candidate result.

[analysis.json](analysis.json) and [edges.json](edges.json) therefore explicitly
record `not-evaluated-after-bootstrap-refusal`. Null ranges, edges and candidate
counts mean **unobserved**, not empty scans or evidence of absence. No init-chain
edge, exit callee, teardown join, registration, runtime invocation or safe
resource release was proved.

Raw evidence remains privately retained; its location is recorded privately.

| Capture | Bytes | SHA-256 |
| --- | --- | --- |
| stdout.json | 7,761 | 7a3dabd9de0ae38c86b60ca2d8842b1a7a7139a02e51e06b06cf409b00ab515e |
| stderr.log | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

No private path, raw bytes, raw log attachment, disassembly, map bases or object
pointers were published. Public records contain only the closed sanitized
receipt, source identities, hashes and bounded counters. No proprietary source
or binary content was copied; the verifier is independently written MIT tooling.

## Result freeze and tests actually run

| Frozen result | SHA-256 |
| --- | --- |
| bootstrap-v10-result.json | 3e0caa5234b3bd1842e70cab0626929ea0ed044b59960fc03da84411c13fb193 |
| analysis.json | 7851369cee4966e0302ede5123da07c4e28f9e91b7bf14893984ed1d38293ff3 |
| edges.json | d9df19be8b727d623f29edbef6fbddca13a15e03a49a7175eb47162e48868d45 |

These three files were written and hashed before [verify-result.py](verify-result.py)
was constructed. Verifier SHA-256:
`74ed48cf5a2214b3f4cd34dda11c4f603d0149dfa9ed85ac74c2fc0c5933864c`.

Both commands passed:

```sh
python3 experiments/2026-09-06-mt6797-wlan-retained-instruction-attribution/verify-result.py
python3 -O experiments/2026-09-06-mt6797-wlan-retained-instruction-attribution/verify-result.py
```

Each run rejected all **514** cases across the predeclared families:

| Mutation family | Rejections per mode |
| --- | ---: |
| authority | 33 |
| candidate-count-class-completion | 16 |
| chronology | 11 |
| cleanup | 40 |
| decoder-agreement | 3 |
| edge-target-reachability | 7 |
| identities-links | 66 |
| map-queue-resource-budgets | 107 |
| parser-engine-callback-private-counters | 83 |
| ranges-hashes | 7 |
| traversal-refusal-boundary | 141 |

The verifier checks exact file/source identities and closed refusal schemas,
chronology, operation budgets, no-semantic-result fields, cross-record links,
cleanup and false authority predicates. Every scalar and dict-field addition
is mutated. Receipt mutations rebind the canonical receipt and raw-output hash
so a generic digest mismatch cannot be their sole rejection. Mutation family
classification uses timestamp-field suffixes, not incidental text in
`stage_outcomes`.

This is a refusal-specific public verifier. It does not independently recompute
private-byte truth or exercise successful mapping/decoder/scan behavior.
No synthetic ELF, parser or decoder fixture ran. Source-only syntax/AST,
assert-free, links, privacy, license, exact pins and whitespace checks accompany
the handoff; no shell/kernel changes require ShellCheck or a kernel build.

## Escalation packet and stop

Evidence: the frozen receipt supplies only `validation-failure` and
`initial-inventory`, not the failed predicate or observed identity difference.
That stage includes baseline mapped-file checks, the accepted interpreter/
stdlib/native comparison and initial legacy-discovery predicates. Zero package
entry and zero asset opens do not establish zero discovery activity.

Attempts: one admitted process; zero runtime repair attempts or retries.
Unresolved question: which exact initial-inventory predicate differed from the
published expectation, and whether it is identity drift or a bootstrap
observation mismatch.
Next discriminating check: a separately designed and reviewed, prospective
payload-free predicate/identity diagnostic before any private analysis, retaining
the current refusal and exact V9/V10 sources. This is a handoff suggestion, not
authorization to run it or alter this consumed freeze.

Work stops here for independent review. Workflow measurement belongs to the
integrator; credits are unavailable. Private analysis did not begin, but the
admitted V10 process budget is consumed and cannot be reused.
