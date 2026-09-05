# Keyboard monitor Buildbox measurement

The single build at `75636670d933b9231f36fddf2ce876801568f64e` completed
and its validated package was fetched. The full retained ARM64 engine is
66,672 bytes, below the 131,072-byte delivery ceiling. Both separately linked
outputs were byte-identical. All 11 scaled Linux QEMU lifecycle methods passed
in 2.262 seconds; the full production binary returned its exact disabled-entry
refusal under QEMU. These are build/lifecycle results, not keyboard behavior.

[Acceptance](results/build-75636670/ACCEPTANCE.json) pins the package, binary
and private build log. The unchanged [manifest](results/build-75636670/manifest.json),
[tool identities](results/build-75636670/tool-inputs.txt) and
[fixture output](results/build-75636670/fixture-tests.txt) retain provenance.
Project Planning independently verified every fetched package-member hash and
all four repository source hashes. Compiler/linker and musl pins passed in the
build; additional resolved tool and library identities remain explicit in the
package. No stronger advance pinning claim is made for those captured inputs.

A separate bounded post-check reacquired both userspace locks, found the managed
staging directory absent and the Git-fetched exact source checkout clean.
The build/fetch window is released. No failure, retry, kernel build, source-tree
copy, delivery, device test or candidate change occurred. The retained package
includes the original link map and all required notices; executable bytes stay
private under ignored build artifacts.

This resolves full-engine size and scaled Linux lifecycle uncertainty. The
remaining full-duration, delivery, admission and actual input obligations stay
in [the monitor contract](MONITOR.md). Physical eMMC testing is independent.

## Independent tooling review limitation

The independent upstream-preparation worker reviewed the exact executed source
after the successful run. Its timeout values are termination targets, not hard
remote descendant-cleanup guarantees: default TERM may be ignored and the local
SSH timeout does not establish remote process cessation. The completed result
and subsequent lock/staging checks remain valid; no failed-run cleanup claim
is inferred from them. The documented second remote published-HEAD check is
also absent: code rechecks local HEAD/cleanliness only. Root kept main frozen
through this run and fetch. A focused host-only correction is assigned before
reusing the path; neither finding calls for repeating this measurement.
