# MT6797 HIF kernel compilation boundary

## Record and hypothesis

| Field | Value |
| --- | --- |
| ID | `2026-09-05-mt6797-wifi-kernel-compile` |
| Status | Planned; source proposal only, backend admission pending |
| Subsystem | Wi-Fi gen3 AHB HIF |
| Variant | Gemini PDA MT6797; no device used |
| Integration base | `789fc975` (ordinary-section integration over `d6cc1cd0`) |
| Protocol input | `2d9983c7cf31189cf7e1aa3752e696092ffb8d86` |
| Upstream | Linux `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, 7.3-rc1 |
| Tracking | [Wi-Fi issue 25](https://github.com/ixoo/gemini-pda-mainline/issues/25) |
| Investigator | CPU 8-9 task; interface reviewed with Wi-Fi owner |

Can the actual bounded PIO, INIT and ordinary-section implementation compile
and link with Linux's kernel types and an ordered `readl`/`writel` adapter?
The existing host tests cannot answer this: their `__KERNEL__` branch is absent.
Success establishes this compilation boundary only. Failure requires correcting
the attributable kernel compatibility issue before any driver integration.

## Exact source and licensing

[inputs.json](inputs.json) pins seven GPL-2.0-only project headers at the exact
protocol commit, four original adapter/Kbuild files, and two upstream build
integration text files by SHA-256. All seven protocol bytes also match the
integrated base. They are copied byte-for-byte into the generated patch; no
vendor implementation or firmware is copied. Header API ownership stays with
the [Wi-Fi experiment](../2026-09-05-mt6797-wifi-contract/README.md).
Its public Planet gen3 source pin is
`c5b0be85017ad0c599725e8273842efdbecdd88a`, used as protocol evidence.

The new [adapter](src/kernel_adapter.c) and its [interface](src/kernel_adapter.h)
are original GPL-2.0-only experimental code. Codex/LLM assistance produced the
adapter, integration glue, generator and documentation. The generated mail has
a synthetic, explicitly non-certifying experiment identity and `Assisted-by`;
it has no DCO or testing/review attribution trailer. Actual human authorship,
review, licensing certification and appropriate subsystem placement must be
resolved before any upstream submission. This is not submission-ready code.

## Honest kernel boundary and runtime policy

The patch builds `lib/mt6797-hif-compile/kernel_adapter.o` through actual Kbuild.
Its default-off boolean requires ARM64 and COMPILE_TEST. Non-static typed entry
points cause the connected inline implementation to be compiled, including
CONFIG/ACK, ordinary-section PDA, START accounting/readiness and direct PIO.
This is a library compilation target, not a simulated cfg80211 driver.

The MMIO callbacks use ordinary ordered Linux accessors. Setup writes accept
offset zero; FIFO writes and reads use fixed offset `0x1000`. A non-null aligned
mapping spanning at least `0x1004` bytes is required. Bounds checks do not prove
power or bus accessibility. The absent caller must hold the mapping, power,
exclusive ownership, session lifetime and setup/data serialization. Buffer
packing remains in the existing protocol code; accessors consume scalar values,
with no second byte swap or raw/relaxed accessor. Callback success only means
the accessor returned: synchronous bus faults are not recoverable callback
errors and writes are not firmware acknowledgements. No speculative readback
is added to a potentially consuming register to flush posted writes.

There is no initcall, module entry point, export, platform driver, match table,
DT node, resource acquisition, mapping operation, IRQ handler or runtime caller.
The new object cannot probe or power CONN at boot. No Wi-Fi node is enabled and
no boot candidate is constructed. Existing unrelated kernel code is not covered
by this no-probe claim, and the resulting package is never a device admission.
No live mapping or fake successful transport is provided for the compilation.

Caller-side image validation, destination admission, immutable distinct buffers,
independent CONFIG TC4/START TC0 credits, shared sequence history, deadlines and
whole-image/EMI ownership remain prerequisites. START wrappers do not compose a
firmware image loader or permit START after only one ordinary section. PIO
submission, CONFIG success, section submission and firmware readiness remain
separate outcomes. See the owning
[ordinary-section contract](../2026-09-05-mt6797-wifi-contract/ORDINARY_SECTION.md).

## Reproducible proposal generation

Run from a project checkout containing the pinned protocol Git object:

```sh
python3 experiments/2026-09-05-mt6797-wifi-kernel-compile/scripts/generate-patch.py
```

The [generator](scripts/generate-patch.py) reads two small upstream text files
from the pinned commit by HTTPS, verifies every input hash, constructs one
`git format-patch`, and verifies exact tree replay. It emits mail on stdout.
Its temporary tree contains only those two text files and eleven additions,
not Linux sources or build output. Temporary Git metadata stays below ignored
`artifacts/wifi-kernel-compile/` and is removed on normal/error/TERM exits.
A local advisory lock prevents concurrent generators. On the next run, marked
symlink-free `patch-*` scratch left by a forced kill is removed under that lock;
unmarked or unexpected state refuses for review. Never remove the artifacts
tree to bypass that refusal. No backend command,
Git push, canonical edit or kernel build occurs in this generator.

[The review patch](0001-lib-mt6797-hif-compile.patch) is the generated output.
The integrated Linux patch touches only the two Kbuild/Kconfig include points
and adds this isolated library directory. Its fixture parent is not a Linux
commit; the authoritative Linux base and full archive identity are pinned in
[the integration proposal](integration-proposal.json).

## Coordinator integration and smallest meaningful build

Only Orchestrator edits canonical series, manifest and configs. The proposed
profile is `mt6797-hif-compile`, based on allnoconfig with the
[compile fragment](compile.fragment). ARCH_MEDIATEK permits the existing package
validator's required MediaTek DTB outputs; it is not board-node enablement.
Networking, modules, KUnit and power-management experiments are disabled.

To avoid another Linux source copy, append the one default-off library patch to
the existing `series-mt6797-provider-compile` and select that same series from
the new profile. Preserve its existing two provider patches and their bytes.
The exact [provider impact record](provider-impact.json) identifies every
selector: only `mt6797-provider-compile` exists at this base; the new
`mt6797-hif-compile` becomes the second. Append the canonical entry immediately
after `proposals/0001-pmdomain-mediatek-defer-initial-activation.patch`
(line 543 at the pinned base), and as the provider series' third entry.
Both existing entries remain in their original order. A memory-only audit of
the proposed 193 profiles passes; the unchanged checkout has 192.

This changes the existing provider profile's patch/source provenance: historical
receipts stay immutable and cannot be called validation of the extended series.
The new library symbol remains default-off there. Root must explicitly accept
this shared-series impact before integration.

The normal builder keys prepared source by series name. Reuse the existing
managed provider source location and archive cache, with a separate Wi-Fi output
directory. Adding the patch invalidates the prior source-state match; the normal
managed preparation must replace that state once under its existing lock. Never
edit its marker or privately patch retained sources. This is source-change
preparation, not an independent reproducibility extraction. Afterward both
profiles reuse the same matching source. No source copy/synchronization or
experiment-specific Linux checkout is requested. The previous provider source
audit at `7029b1368134eef359dc43997bad84b73f426578`, source state
`5b6edbcdec8f50df55991d6703b7a42060b0308e51eae992fe73047382a1e16d`
and integrity
`6985809664221074c150469d7f539995c62baf2a90f854f62d8ad90c995ca6a4`,
becomes historical for that mutable source location. Its package and receipts
remain valid for their original inputs. To reconstruct it later, select the
exact published `7029b136` project commit and original provider profile under
a separately admitted normal Buildbox run; its pinned archive and two patches
reconstruct the source in the same managed slot. Never restore a marker alone.
The active device candidates, full/default selection and reset-topic source
`linux-7.3-rc1-series-mt6797-infracfg-upstream-kunit-source` and their series
are outside this proposal and must remain untouched. If preserving the old source
is still required by another lane, root must resolve custody before this build.

Before build admission, root reviews patch/style and header hashes, stages the
exact patch/series/profile/fragment delta, audits every profile's canonical
subsequence, runs common checks, excludes artifacts and sensitive material,
verifies the exact authorized origin, commits without signing if necessary and
pushes the exact clean revision. Root checks available backend storage and
acquires the existing managed build window. The sole kernel build command is:

```sh
KERNEL_PROFILE=mt6797-hif-compile ./scripts/build-kernel --backend buildbox
```

The smallest supported package build covers the arm64 object, vmlinux link,
Image and required DTBs. Do not bypass package provenance with an ad hoc host
compile or invoke the VM. Fetch only the validated package with the same
profile after success. No schema/QEMU/device run is needed for this claim.

Acceptance requires resolved CONFIG_MT6797_HIF_COMPILE_TEST=y and COMPILE_TEST=y,
actual compilation of kernel_adapter.o in the build log, successful link, exact
package provenance and input hashes, and a bounded `nm`/`objdump` inspection of
the backend object to establish the wrapper/accessor code was emitted rather
than merely accepting an ignored Kconfig value. Record the eight wrapper
symbols, the two callback bodies, and absence of any initcall section, runtime
registration or exported symbol from this object. Disassembly establishes code
generation, not hardware ordering on this device. Preserve warning output and
report kernel/style failures without treating existing host tests as a substitute.
A failed build stops at source diagnosis; it never grants hardware admission.

## Observations and conclusion

Host preparation results belong in [validation.json](validation.json).
Two generations match byte-for-byte and exact patch replay passes. Pinned
strict checkpatch **fails** with 85 errors, 12 warnings and 20 checks in
789 checked lines: unchanged protocol-header style and mail metadata, including
the intentionally absent DCO. New adapter/Kbuild files have no remaining
findings. [The full output](checkpatch.json) is retained; source-style cleanup
belongs with the header owner and is not silently applied by this generator.
No kernel, sparse, backend, QEMU or device test has run for this proposal.
Compilation and hardware compatibility remain inconclusive. The next ordered
project work remains owned by [the roadmap](../../docs/ROADMAP.md).

This isolated compilation scaffold should be removed when a reviewed genuine
kernel HIF/resource-owner implementation incorporates these contracts and is
compiled through its real Kbuild target. It is not an upstream library ABI or
a permanent driver framework.
