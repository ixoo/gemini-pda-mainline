# Second schema window: complete collection for review

The sole second window completed as **COLLECTED_REVIEW_REQUIRED** from exact
clean, published revision `f4ff1028e883c63e980c61f6bb076d99b97454ac`.
All thirteen fixtures first passed on Linux. The normal nonblocking Buildbox
lock, exact tool identities and source/build preconditions passed before work.
This is complete schema evidence for integrator review, not an automatic
submission-readiness or hardware-support claim.

The window reused source/build revision
`4ec63076aeb6388ba24b33ee20afcf19ced541e1`. No source repair, extraction,
package replacement, kernel rebuild, guest run or device access occurred.
The [original attempts](VALIDATION_ATTEMPT_1.md) remain refused and immutable.
The separately reviewed [protocol correction](SCHEMA_EXECUTION.md) distinguished
128 MiB generated regular files from hard-capped 16 MiB stdout/stderr streams.
No other time, workload or input limit changed, and there was no automatic retry.

## Complete result

| Command | Elapsed seconds | Ceiling seconds | Result |
| --- | ---: | ---: | --- |
| Full source integrity before | 14.933608 | 180 | unchanged |
| `dt_binding_check` | 209.372430 | 300 | exit 0, stderr empty |
| `dtbs_check` | 184.082707 | 300 | exit 0, stderr empty |
| Explicit MT6797 EVB validation | 1.245552 | 30 | exit 0, exact DTB attribution |
| Explicit MT6797 X20-dev validation | 1.248358 | 30 | exit 0, exact DTB attribution |
| Full source integrity after | 14.840226 | 180 | unchanged |

All six commands had no stop reason, no surviving process group and no TERM/KILL
cleanup. Every stderr file is empty. Both full-tree checks returned
`90923e5fb4d9bf2db35049abb6011437bc334aeedc528f099591f6198e9fc7aa`.
All eleven protected source files and nine protected build files matched before
and after, including configuration, release, Image.gz, production/test objects
and both MT6797 DTBs.

The binding stdout records actual filtered document validation, Yamllint, style,
example extraction, example compilation and validation recipes. The complete
202483-byte DTB stdout records the admitted normal `dtbs_check` traversal, 105
DTC recipe markers and 118 filtered validation invocations, including both
MT6797 boards. Build metadata synchronization also ran; it did not change the
protected configuration or release. Diagnostics were reviewed separately from
exit status because several recipes use `|| true`.

Each explicit validator emitted exactly its expected `Check:  <DTB>` line and
no stderr. Both independently inspected DTBs contain one matching MT6797
infracfg node, `syscon@10001000`, with exactly one reset argument cell. The
processed schema contains the selected binding ID and MT6797 compatible.

The processed schema is 28551455 bytes, SHA-256
`a3265d87a3617c19c3463fb3a728df2120b8932ee0be686dcd8c4f69fac82b38`.
Its size explains why the former 16 MiB inherited regular-file limit prevented
collection. It fits the reviewed 128 MiB allowance; that allowance was not
increased during this window. No generated schema was copied to the host.
The managed attempt scratch directory was removed; only logs and receipts remain.

## Evidence and review boundary

[The inventory](results/schema-attempt-2-f4ff1028/inventory.json) pins all fetched
logs, the original collector receipt, Linux fixture output and a separate
review summary. All embedded collector log digests were verified after fetch.
The [original receipt](results/schema-attempt-2-f4ff1028/result.json) retains its
`COLLECTED_REVIEW_REQUIRED` outcome. The
[review summary](results/schema-attempt-2-f4ff1028/review.json) explicitly leaves
integrator review pending; nothing rewrites the prior schema or QEMU refusals.

These checks concern the focused infracfg binding and exact retained upstream
inputs. They do not validate every schema in the source, establish new hardware
support, settle upstream authorship/sign-off, or authorize another execution.
Ordered follow-up belongs to the [roadmap](../../docs/ROADMAP.md#upstream-delivery-gate).
