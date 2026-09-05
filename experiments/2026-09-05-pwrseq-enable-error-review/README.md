# Experiment: pwrseq enable-error propagation and existing upstream fix

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-05-pwrseq-enable-error-review` |
| Status | completed source and host-fixture review; upstream proposal pending |
| Subsystem | power sequencing core |
| Device variant | none; generic source control flow only |
| Date | 2026-09-05 |
| Investigator | project AI-assisted source review; no DCO certification |
| Tracking | [existing upstream series](https://lore.kernel.org/all/20260903-pwrseq-kunit-v1-0-1f893d2cabc2@oss.qualcomm.com/) |

## Question and provenance

Does a failed `pwrseq_unit_enable()` still reach `post_enable`, whose return
can hide the original failure? The earlier [provider-ownership review](https://github.com/ixoo/gemini-pda-mainline/blob/52b5e3288a932957b1afb1671dd8cddecfa7d252/experiments/2026-09-05-mt6797-wifi-contract/PROVIDER_OWNERSHIP.md)
identified this at project upstream and stable pins. This investigation checks
current public snapshots before proposing any duplicate implementation.

The source pins and digests are in [host results](results.json) and
[verify.py](verify.py). Each full source is fetched with a finite response limit,
hash-verified, and inspected in memory. No Linux source tree is retained.

| Public input | Exact observed commit | Finding |
| --- | --- | --- |
| Project upstream | `4d7d9486c04d917265f64c55bd23b2cc4fe7749c` | error path present |
| Torvalds GitHub `master` snapshot | `0d9ff90a5422cc7509258aaaba1e7481df4d332a` | error path present |
| brgl `pwrseq/for-current` snapshot | `3b54dbd119805361695cb50ca6a875f4c7518b74` | error path present |
| brgl `pwrseq/for-next` snapshot | `3b04e9b8056e868c3e9a04cc74168c7c9a18746a` | error path present |
| Project stable v7.1.3 | `199c9959d3a9b53f346c221757fc7ac507fbac50` | same path under `pwrseq_power_on` name |

The first four full files share SHA-256
`86fe4cb3e77f1eeece1bd065ba7378bb5892499f344fb9de8af1761e449eda78`.
Stable has SHA-256
`22550b6d006a42afc61c8f69e89ff6d0a2a3e545366dc317b8e2eff8f79f74f2`.
The extracted functions are byte-identical after normalizing only the stable
function name. Ref observations are snapshots, not claims about future tips.

Torvalds Gitiles exposed an older August 25 `master` snapshot
`45c13f3f9e3bb15fd89ff2864c6f627a3b4b4229`; the newer September 5 GitHub
commit above was checked explicitly. A Gitiles lookup of the project upstream
pin returned 404, so its exact GitHub source was used. These differences are
not evidence of a source fix. The five most recent core-file commits at the
newer mainline snapshot contain no matching error-propagation fix; the most
recent is the API rename `d51fc9d4cd6eb18ac82913d83ecf7bd8c85f71ee`.

## Existing upstream proposal; no duplicate patch

Bartosz Golaszewski posted the precise two-line early return on September 3:
[patch 1/2](https://lore.kernel.org/all/20260903-pwrseq-kunit-v1-1-1f893d2cabc2@oss.qualcomm.com/),
message ID `20260903-pwrseq-kunit-v1-1-1f893d2cabc2@oss.qualcomm.com`.
The [public archive of the author's message](https://lkml.iu.edu/hypermail/linux/kernel/2609.0/08042.html)
provided the readable patch and exact message identity; direct Lore/raw and
patch.msgid.link access returned HTTP 403 during this review.

Its subject is “power: sequencing: don't call .post_enable() if
pwrseq_unit_enable() failed”. It adds `if (ret) return ret;` immediately after
the scoped unit-enable lock block, before the post-enable callback. The patch
names introducing commit `249ebf3f65f8` in its Fixes metadata. It is paired with
[a submitted KUnit suite](https://lore.kernel.org/all/20260903-pwrseq-kunit-v1-2-1f893d2cabc2@oss.qualcomm.com/).

**Posted, not observed merged:** no fixing commit was established. The inspected
current source pins remain unfixed. This record identifies the existing proposal
and its applicability instead of creating a duplicate patch or claiming authorship.
No submitted patch, sign-off or certification is copied into the local series.
The project has not submitted or selected this change. Kernel manifest, canonical
series, configuration and existing proposals remain unchanged.

## Safety and associated code

[verify.py](verify.py) performs public source reads and a local host C fixture
only. [fault-fixture.c](fault-fixture.c) contains purpose-written stand-ins for
unit operations, registration and locks; the enable function is extracted from
the pinned public source at run time. No device, Buildbox, VM, partition,
firmware or credential access is performed. No kernel build is claimed.

Temporary generated C and executables live in a unique context-managed directory
under ignored `artifacts/pwrseq-enable-error-review/` and are removed on success
or failure. Each trusted compiler/fixture command has a 15-second limit, its own
process group cleaned on exit, no core dumps, and a 1 MiB per-file write limit.
Captured streams larger than 64 KiB refuse; source responses are limited to
128 KiB with a 15-second socket timeout per request. There are five source reads, one compiler
version command, three fixture compilations and three fixture executions.

## Procedure and observations

Run `python3 -B experiments/2026-09-05-pwrseq-enable-error-review/verify.py`.
The helper requires all five hashes, identical extracted control flow and exactly
one applicable posted hunk. It compares three variants against ten explicit
cases, retaining every case result:

- Original: the two unit-error cases with a post callback fail. A successful
  callback hides the unit error; a failing callback replaces it and wrongly
  attempts disable. The other eight cases pass.
- Posted fix: all ten cases pass. Unit failure returns the original error,
  does not call post-enable or disable, and leaves the descriptor off.
- Wrong-success-return mutation: all three unit-failure cases fail. Returning
  success instead of the original error cannot pass the fixture.

The ten cases cover null/already-on descriptors, unregistered provider,
unit failure with/without both post callback results, ordinary success with/without
post callback, post failure, and post plus rollback failure. Call counts,
returned errors, descriptor state and modeled lock release are checked.

## Analysis and limits

The existing upstream hunk applies to both observed subsystem tips and mainline.
Stable requires the older function name in surrounding patch context, while the
same two-line change applies to its identical function body. This is source
applicability, not a selected stable backport or a full-tree patch replay.

The host tests execute the actual extracted enable function. They do not execute
real unit dependency operations, kernel locks, device registration, concurrency,
or the submitted upstream KUnit suite. In particular, the pre-existing behavior
on failed post-enable rollback is preserved: the rollback error is ignored and
the descriptor is cleared. That preserved behavior is a limitation, not safe
resource-release evidence. Nothing here selects pwrseq for CONN or resolves the
provider lifetime and teardown concerns in the owning Wi-Fi review.

## Conclusion and handoff

Confirmed at the five exact source pins: the error-propagation defect remains,
and the existing submitted fix addresses this narrow control-flow path in the
host fixture. A duplicate implementation is unnecessary. Root can track the
existing upstream series and refresh its merge status before any future adoption.
No third schema execution, kernel build, device action, hardware-support
promotion or new ordered roadmap item is admitted by this review.

One validation invocation stopped on a public-source read timeout before producing
a result. It was not treated as a fixture pass; the completed invocation is
recorded separately in the result file.

The common repository checker passed with four changed files, 190 manifest
profiles and unchanged grandfathered metadata debt (37). Python syntax and diff
checks passed. Checkpatch, full kernel compilation, DT schemas, upstream KUnit
execution and hardware tests were not run for this source/host-only packet.

## Coordinator integration review

The coordinator reviewed the fixture and verifier, then independently reran the
exact five-source verification and all three function variants. Source hashes
matched; the original failed the two recorded callback cases, the posted fix
passed all ten, and the incorrect success-return mutation failed all three
unit-error cases. Managed temporary generated sources and executables were
removed. The original worker receipt is retained unchanged.

Accept this as evidence for tracking the existing upstream fix, with merge
status refreshed before adoption. No duplicate local patch, provider selection,
backend build or hardware-support claim is introduced.
