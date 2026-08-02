# Experiment: Gemian MT6797 A72 owner-local transition observer

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-23-gemian-a72-owner-observer` |
| Status | `inconclusive`: the bounded five-patch revision passes compiler, stack, lock, and timing review; a separate validated boot-image experiment and hardware evidence remain open |
| Subsystem | MT6797 A72 hotplug, PSCI, external buck, SPM, iDVFS, B/CCI clocks, MP2 DCM and TOPRGU |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-23 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can a fixed-function observer be placed inside the Gemian 3.18 owners of the
A72 transition resources so that one natural CPU8/CPU9 online/offline
transaction yields attributable pre-state, mutation and post-state evidence
without adding a user-controlled register, SMC, hotplug or policy interface?

This directory answers the source-preparation and compiler-review parts of
that question. The successful Buildbox compile is not a timing-safety or
hardware-behavior result.

## Provenance and environment

- Exact active Gemian boot image SHA-256:
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`.
- Android boot-image kernel field SHA-256:
  `b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`.
- Active `Image.gz` stream SHA-256:
  `14b4e079bf87b10b14df09a83673f065a342566daed509767bba08420f6c5257`.
- Correct active appended DTB SHA-256:
  `9e26929563f7682d1f7545d6007f0092c7e085a4edbd6e7be0ac8eaa5159b2f9`.
- Active ramdisk SHA-256:
  `a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4`.
- Active `/proc/config.gz` SHA-256:
  `53b53b62fa5a111cb7d6ea4f513aec1e8a6b436c8c17bfd86cb00a9bc4bf6ae1`.
- Decompressed active configuration SHA-256:
  `231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4`.
- The exact source revision that produced the active kernel remains
  unresolved. Public
  `gemian/gemini-linux-kernel-3.18@59e00a9144d782e148332009a835b99c43382467`
  is selected only because its observer-relevant hooks match the reconciled
  binary/source evidence. It must not be described as the exact active source.
- Source patch commits used to generate this series:
  `7bddafa6`, `c8475b56`, `429afb35`, `349f24b6`, and `718f297a`.
- Every source build must run only on Buildbox from an exact clean pushed
  project commit. Its toolchain input is Debian snapshot
  `20170618T000000Z`, cross-GCC package `6.3.0-18cross1` reporting GCC
  `6.3.0 20170516`, and binutils package `2.28-5` reporting GNU ld `2.28`.
  The 2019 `+deb9u1` environment and Buildbox's system GCC 12/binutils 2.40
  are not acceptable substitutes. Native VM kernel builds are prohibited
  unless the owner explicitly requests one.
- The reconciliation source is
  [`../2026-07-22-a72-firmware-power-contract/results/active-gemian-kernel-reconciliation-20260723.txt`](../2026-07-22-a72-firmware-power-contract/results/active-gemian-kernel-reconciliation-20260723.txt).

This experiment has no boot-candidate label. `AL` remains the mainline
resource-only work, while `AM` is the first mainline image that made CPU8
active. This Gemian observer series is a separate vendor-kernel diagnostic.

## Safety assessment

The exported proc ABI is root-read-only (`0400`) and fixed-function. It has no
write operation, clearing operation, register selector, address parameter,
SMC selector, CPU-hotplug control, policy control, module parameter or debug
command. Writers append typed records to a preallocated 256-entry ring; proc
open takes a point-in-time private copy.

That does **not** make the patch zero-effect or ready to boot. The owner-local
DA9214 snapshot temporarily selects page zero and restores the exact previous
page while holding the existing DA9214 mutex. When PAGE_REVERT was originally
set it deliberately omits a verify-read whose access could itself change the
selector. The B/CCI snapshot enables the existing DVFSP arbitration clock,
performs one immediate hardware-semaphore request/read with no retry or added
delay, and releases it when acquired. Mutation logging holds existing owner
locks across added readbacks. MP2 DCM
is newly serialized by a dedicated spinlock. These operations can change
serialization, latency and transition timing even when every captured value is
discarded.

The patches preserve the vendor transition's mutation order and return-value
ABI. Observer failures are recorded or ignored and do not introduce a new
retry, `BUG`, warning, panic or transition return. Where the observer's SPM
mapping cannot be obtained, the exact original direct RMW path still runs.
The configured DA9214 path replaces two ineffective unsigned-return
`BUG_ON(... < 0)` expressions; the configuration-off path retains them. The
observer deliberately does not repair the vendor ordering in which DCM/iDVFS
actions can precede checking the PSCI result.

Owner serialization and timing are a separate safety gate. Before any device
boot, the final series must receive:

1. a clean source build and compiler-warning review using the pinned 2017
   toolchain environment;
2. a configuration review proving that only the intended diagnostic option
   changes;
3. line-by-line review of DA9214 selector restoration, the hardware-semaphore
   bound, added readbacks, DCM serialization and every lock context;
4. a compatible kernel `checkpatch.pl` run or an explained equivalent;
5. a named artifact identity, packaging/readback validation, recovery plan,
   exact test hypothesis and stop conditions.

The compile lane accessed only Buildbox and did not create a boot image or
access the device. Separately, the device was returned from Stage27 to Gemian
through the validated USB path and its configuration was read and hash-checked;
no observer artifact changed a partition, policy, or hardware state.

## Associated code

- [`patches/series`](patches/series): exact five-patch order.
- [`inputs/active-gemian.config`](inputs/active-gemian.config): exact
  decompressed live configuration, SHA-256
  `231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4`.
- [`inputs/stretch-cross-toolchain.tsv`](inputs/stretch-cross-toolchain.tsv):
  exact 39-package Debian snapshot manifest with package, version,
  architecture, filename, and SHA-256.
- [`patches/0001-diagnostic-add-fixed-MT6797-A72-transition-ring.patch`](patches/0001-diagnostic-add-fixed-MT6797-A72-transition-ring.patch):
  typed static ring, transaction IDs and root-read-only snapshot ABI.
- [`patches/0002-diagnostic-add-owner-local-fixed-A72-snapshots.patch`](patches/0002-diagnostic-add-owner-local-fixed-A72-snapshots.patch):
  fixed DA9214, SPM, secure-monitor and B/CCI clock snapshots.
- [`patches/0003-diagnostic-record-A72-power-mutations-under-owners.patch`](patches/0003-diagnostic-record-A72-power-mutations-under-owners.patch):
  owner-serialized SPM, buck, TOPRGU and MP2 DCM mutation records.
- [`patches/0004-diagnostic-correlate-A72-hotplug-lifecycle.patch`](patches/0004-diagnostic-correlate-A72-hotplug-lifecycle.patch):
  HPS, raw/mapped PSCI, secondary-online and offline correlation.
- [`patches/0005-diagnostic-bound-observer-timing-perturbation.patch`](patches/0005-diagnostic-bound-observer-timing-perturbation.patch):
  256-record ring, immediate-only clock semaphore attempt, and boundary-only
  broad snapshots.
- [`DESIGN.md`](DESIGN.md): event contract, fixed register allowlist and
  concurrency review.
- [`scripts/validate.py`](scripts/validate.py): experiment-local patch
  invariants.
- [`scripts/test-static.py`](scripts/test-static.py): positive and mutation
  tripwire tests for the validator.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): remote-only,
  compile-review driver invoked from an exact clean pushed project checkout.
  It cannot create a boot image or access the device.
- [`results/source-and-static-validation-20260723.txt`](results/source-and-static-validation-20260723.txt):
  exact source/static validation record.
- [`results/buildbox-toolchain-feasibility-20260802.txt`](results/buildbox-toolchain-feasibility-20260802.txt):
  Buildbox reachability, exact snapshot package resolution, and the successful
  relocatable compiler-object proof. This is not a kernel-build result.
- [`results/buildbox-compile-attempt-1-20260802.txt`](results/buildbox-compile-attempt-1-20260802.txt):
  exact first pushed-commit submission and its pre-compile configuration
  rejection. No compiler target ran in that attempt.
- [`results/buildbox-compile-attempt-2-20260802.txt`](results/buildbox-compile-attempt-2-20260802.txt):
  exact replacement submission, passed config gate, and pre-object DCT
  interpreter failure.
- [`results/buildbox-compile-attempt-3-20260802.txt`](results/buildbox-compile-attempt-3-20260802.txt):
  exact Python-enabled submission and its fail-closed discovery of the DCT
  wall-clock comment.
- [`results/buildbox-compile-attempt-4-20260802.txt`](results/buildbox-compile-attempt-4-20260802.txt):
  exact deterministic-DCT submission and its legacy host-DTC link failure.
- [`results/buildbox-compile-attempt-5-20260802.txt`](results/buildbox-compile-attempt-5-20260802.txt):
  exact host-compatibility submission and its Make variable-precedence
  failure before observer compilation.
- [`results/buildbox-compile-attempt-6-20260802.txt`](results/buildbox-compile-attempt-6-20260802.txt):
  first complete source compile and link, exact output hashes, configuration
  delta, symbol evidence, and the remaining baseline/stack review boundary.
- [`results/buildbox-compile-attempt-7-20260802.txt`](results/buildbox-compile-attempt-7-20260802.txt):
  exact observer/baseline compile and identical-diagnostic proof, followed by
  the fail-closed host fetch rejection of four case-colliding filename pairs.
- [`results/buildbox-compile-attempt-8-20260802.txt`](results/buildbox-compile-attempt-8-20260802.txt):
  successful replacement dual build, case-preserving stack bundle, and exact
  local fetch validation.
- [`results/compiler-and-timing-review-20260802.txt`](results/compiler-and-timing-review-20260802.txt):
  function-level stack and lock review, compatible checkpatch findings, timing
  rejection, and the bounded next revision.
- [`results/bounded-source-validation-20260802.txt`](results/bounded-source-validation-20260802.txt):
  exact fifth-patch source construction, safety tripwires, and compatible
  checkpatch review before the replacement build.
- [`results/buildbox-compile-attempt-9-20260802.txt`](results/buildbox-compile-attempt-9-20260802.txt):
  successful exact five-patch/baseline build, case-safe evidence fetch, and
  compiled ring-bound proof.
- [`results/bounded-compiler-and-timing-review-20260802.txt`](results/bounded-compiler-and-timing-review-20260802.txt):
  replacement stack, owner-lock, and bounded timing decision.

The local validation invocation is:

```sh
python3 experiments/2026-07-23-gemian-a72-owner-observer/scripts/validate.py
python3 experiments/2026-07-23-gemian-a72-owner-observer/scripts/test-static.py
```

Neither command needs privilege, network, VM or device access.

## Procedure

### Completed source preparation

1. Reconcile the exact active image components and active configuration.
2. Select public commit `59e00a…` only as a hook-equivalent source baseline.
3. Keep the recorder, owner snapshots, owner mutations and lifecycle
   correlation as four original logical `git format-patch` changes, followed
   by one timing-bound refinement.
4. Apply all five patches in order to a detached `59e00a…` worktree.
5. Run whitespace checks, the experiment validator and its negative tripwire
   tests. Record tool limitations rather than treating a skipped tool as a
   pass.

### Required compiler review before any boot

1. Use the dedicated Git-based Buildbox lane, which fetches the exact clean
   pushed project commit, public source `59e00a…`, and the immutable
   `20170618T000000Z` Debian snapshot inputs. It verifies all 39 package hashes,
   proves the relocated compiler reports GCC `6.3.0 20170516`, ld `2.28`, and
   Python `2.7.13`, and stops on the 2019 `+deb9u1` environment or Buildbox's
   system GCC 12/binutils 2.40/Python 3.
2. Start from a clean `59e00a…` checkout on Buildbox, apply [`patches/series`](patches/series)
   in order, and import the exact active plain configuration identified above.
3. Enable `CONFIG_MTK_A72_TRANSITION_OBSERVER=y`, retain the complete resulting
   config and diff, and build the full source tree with warnings preserved.
   The only accepted serialized deltas are the observer from absent to `y` and
   `CONFIG_ANBOX` from absent to explicit `n`. The latter remains disabled and
   records a Kconfig symbol present only in the hook-equivalent public source;
   every other delta is rejected.
4. Build the exact unpatched baseline under the same normalized configuration,
   toolchain and diagnostic flags. Require its extracted warning/error set to
   be byte-identical to the observer build and retain both build logs, configs,
   diagnostics, symbol maps and output hashes.
5. Retain GCC `-fstack-usage` reports for all observer objects, review every
   affected owner function, and compare generated symbol/reference placement
   with the source-level hook table in [`DESIGN.md`](DESIGN.md).
6. Stop before boot-image packaging or device access. A separate reviewed
   experiment must define the exact boot artifact and transition test.

The Buildbox lane must not copy a source tree or toolchain from the development
host or recovery VM. If the pinned snapshot packages cannot be made runnable
inside a managed Buildbox root, defer the build; do not use the native VM.

The compile-review invocation is:

```sh
./scripts/buildbox build-gemian-observer
./scripts/buildbox fetch-gemian-observer
```

Both commands require the exact clean pushed `HEAD`. The result is explicitly
not a boot candidate.

## Observations

All four patches applied in order to the selected public baseline and the
result passed `git diff --check`. The experiment validator and its deliberate
corruption tests pass. The vendor tree's old `scripts/checkpatch.pl` cannot run
under the host's modern Perl because its own regular expressions are rejected;
this is recorded as a tooling limitation, not as a clean checkpatch result.

Buildbox can reach the public source and immutable Debian snapshot. Snapshot
metadata resolves cross-GCC `6.3.0-18cross1` and binutils `2.28-5`, and one
disposable probe downloaded their 25-package dependency closure. A persistent
session then extracted that exact closure, invoked the relocated compiler and
linker, and produced a valid AArch64 relocatable object. The tree was removed
on success. No vendor source build was performed by the probe. After returning
the development device from Stage27 to
Gemian through the validated USB reboot path, the live `/proc/config.gz`
matched the previously recorded compressed and decompressed hashes exactly.
The non-sensitive decompressed configuration is now a tracked Buildbox input.
No observer-kernel execution or A72 hardware transition has occurred.

Compile attempt 2 passed the exact normalized configuration gate, then exposed
the selected source's tracked DCT generator as Python 2 syntax with an
`/usr/bin/python` shebang. Buildbox intentionally has only system Python 3. A
separate pinned Stretch Python 2.7 probe generated `cust.dtsi` successfully;
two consecutive outputs differed only at the generated wall-clock comment on
line 3. The lane requires that exact timestamp syntax, normalizes only that
line to `1970-01-01 00:00:00`, and pins normalized SHA-256
`7a7eb416499346afff30c15f967ccb9cf79323c076204b6a953515db74811632`.
The 14 direct Python runtime packages and this normalized output oracle are
now part of the fail-closed lane. No proprietary or later-source DCT
conversion was used.

Compile attempt 4 passed every input, configuration, interpreter, and DCT gate
and entered target preparation. The Buildbox system GCC then linked the
tree's legacy host DTC with modern `-fno-common` semantics and rejected its two
tentative `yylloc` definitions. The pinned tree exposes `HOST_EXTRACFLAGS`;
the replacement adds only `-fcommon`, which restores GCC 6's historical host
default without changing target compiler flags or vendor source. Provenance
records both the host compiler and this compatibility flag.

Compile attempt 5 proved that `-fcommon` fixes DTC, but passing
`HOST_EXTRACFLAGS` on the Make command line overrode the SELinux host-tool
subdirectories' required include-path additions. Both reported missing
`classmap.h` even though the file is present and tracked. The correction exports
`HOST_EXTRACFLAGS=-fcommon` in the environment instead; sub-Makefiles can append
their local flags while target compilation remains unchanged.

Compile attempt 6 passed all input, configuration, DCT, host-tool and target
gates. The exact four-patch source produced `vmlinux`, `System.map`, and
`Image.gz-dtb` with pinned GCC 6.3/binutils 2.28. The config diff contains only
the accepted disabled `CONFIG_ANBOX` serialization and observer enablement.
The symbol map contains the expected observer owners and a fixed ring span of
212992 bytes, exactly 2048 records times 104 bytes. Its sole extracted
diagnostic is the vendor tree's summary of 69 section mismatches; because that
attempt did not build the exact unpatched baseline, inheritance is not yet
proved. A replacement compile will compare both builds byte-for-byte and
retain GCC stack-usage reports. The complete attempt identity and output hashes
are recorded in the associated result.

Compile attempt 7 built both the observer and exact unpatched baseline under
identical inputs with `-fstack-usage`. Both linked, the baseline contains no
observer symbols, and their extracted diagnostics are byte-identical. This
attributes the 69-section-mismatch summary to the vendor baseline. Buildbox
captured 2484 stack reports and validated its package, but the host fetch
correctly rejected four distinct uppercase/lowercase netfilter filename pairs
that collide on its case-insensitive filesystem. No local destination was
accepted. The replacement stores that Linux tree inside one checksum-covered
tar archive with exact member manifests.

Compile attempt 8 repeated the two clean full builds and all diagnostic/symbol
gates, created and source-compared a 2484-member case-preserving stack archive,
and fetched the 243 MiB bundle with a clean outer checksum. This closes the
compiler, baseline-warning attribution, and evidence-transfer gates for exact
commit `10884b2c1895163c5bfe3d795f0b699d452b7d11`.

The ensuing timing review rejected that exact patchset for boot. A complete
online/offline cycle invokes eight broad snapshots. Their combined theoretical
effect includes up to 16 ms of IRQ-disabled hardware-semaphore waiting, 104
secure calls, at least 24 DA9214 I2C transactions, and a 212992-byte proc-copy
critical section. Two snapshots also extend the vendor's 240-microsecond
SRAM-LDO intervals. Stack use itself passes: observer frames are at most 128
bytes and the largest changed hotplug caller frame is 688 bytes. No device or
boot image was accessed.

The fifth patch responds directly to that rejection. It shrinks the
ring to 256 records, removes four intermediate broad snapshots, and replaces
the bounded semaphore loop with one immediate request/read. Static tripwires
pin those bounds.

Compile attempt 9 built that exact five-patch revision and the exact unpatched
baseline. Both linked, their diagnostics are byte-identical, the baseline has
no observer symbol, all 2484 case-preserved stack reports validated, and the
host fetch passed. The ring's compiled symbol span is exactly 26624 bytes. The
replacement review passes stack, lock, and bounded timing gates: no snapshot
remains in a 240-microsecond SRAM-LDO interval, the semaphore loop and its
theoretical 16 ms full-cycle IRQ-disabled wait are gone, and the clock frame
drops from 96 to 80 bytes. The four remaining boundary snapshots still add 52
secure reads and 12 to 24 I2C transactions over a complete cycle, so this is
accepted only for one defined diagnostic capture, not production use.

## Analysis

The source layout supplies the requested observation points and confines
device-specific snapshots to the corresponding owner files. It can correlate
HPS `cpu_up`/`cpu_down` return values, raw PSCI firmware status, Linux-mapped
PSCI status, secondary-online publication, each affinity-info retry, iDVFS,
DCM, buck and final offline state under per-A72 transaction IDs. A ring
overwrite counter exposes loss without adding a control to clear state.

The complete Buildbox compile proves that the pinned compiler accepts the
constructs and that the tree links. It does not prove that the additional
owner-lock duration is safe, that fixed SMC reads are benign at
each hook, or that the hook-equivalent public source exactly represents the
running binary. Those unresolved questions are decision-changing.

## Conclusion

`inconclusive` for hardware behavior. The exact compiled four-patch revision is
rejected for boot. The bounded five-patch revision closes its source, compiler,
baseline-attribution, stack, owner-lock, and timing gates for one diagnostic
capture. No current output is a boot image or installable candidate. The
mandatory next result is a separate experiment that constructs and validates
an exact recoverable Gemian boot container and defines the single natural
online/offline observation before any deployment.

## Follow-up

Create the separate boot-image experiment around exact kernel field SHA-256
`5864c083a156fcb023e62a5e8dd3fd4c75d68fb119c82492ed4653065ca39a18`.
Reuse the exact active Gemian ramdisk and boot-container parameters, validate
every checksum and size, and define one natural online/offline capture,
retrieval of `/proc/mt6797_a72_transition`, exact expected event ordering, stop
conditions, recovery, and how each possible result changes the mainline A72
implementation. Do not deploy the compile-review package itself.
