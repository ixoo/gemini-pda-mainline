# Kernel-style header revision

This separate revision replaces the proposed patch payload for compile admission.
The seven reference headers and every file in the historical `7af83151` proposal
remain byte-for-byte unchanged. No canonical series, manifest, configuration or
Wi-Fi-owner file is changed by this packet.

## Exact source mapping

[mapping.json](mapping.json) records each reference and transformed SHA-256,
the formatter/configuration identity and revised patch hash. The reference is
`2d9983c7cf31189cf7e1aa3752e696092ffb8d86`; those seven header bytes also match
the integrated `789fc975` base. The reference and revised headers have identical
sequences of all **3,363 C tokens**, including both conditional compilation
branches, and identical preprocessor directive lines. Identifiers, types,
constants, operators, member order, control flow and function signatures are
unchanged. No brace insertion/removal or declaration movement occurs.

[The header-only diff](header-style.patch) shows the transformation separately
from [the complete revised compile patch](0001-lib-mt6797-hif-compile.patch).
The changes expand same-line statements, correct whitespace/alignment and add
blank lines after declarations. Formatting uses the pinned clang-format version
and [small configuration](clang-format.yaml), followed by explicit whitespace
corrections for Linux's declaration separators and two formatter line breaks.
The complete token comparison guards these corrections. Token comparison is not
a kernel compile result; it complements the actual protocol fixtures below.

The headers retain GPL-2.0-only licensing and their original source provenance.
This is an original formatting revision assisted by Codex/LLM, not a vendor-code
import. The new complete patch retains the same synthetic, non-certifying
experiment identity and explicitly asserts no DCO. No author or certification
is inferred from the repository commit identity. Actual human authorship,
certification and maintainer review still precede upstream submission.

## Reproduce and verify

From the project root:

```sh
python3 experiments/2026-09-05-mt6797-wifi-kernel-compile/styled/scripts/prepare.py
python3 experiments/2026-09-05-mt6797-wifi-kernel-compile/styled/scripts/verify.py
```

Preparation defaults to comparing all generated files with this reviewed
revision. `--write` explicitly regenerates only this revision's seven headers,
header diff, complete patch and mapping. It never rewrites the historical
proposal. It uses hash-pinned small upstream Kbuild text inputs and a disposable
text-only Git fixture, then proves exact patch replay. No Linux tree is cloned,
copied or built. Managed temporary state is locked and removed on success/error/
TERM; marked, symlink-free stale state is cleaned on the next run, unknown state
refuses. The verifier follows the same policy for temporary host binaries.

The [test-input ledger](test-inputs.json) pins the **eight unmodified fixtures**
from the integrated `789fc975` commit, including its extra sequence test. Each
fixture is compiled and run twice: once beside the original seven headers and
once beside the transformed seven headers. The fixture's quoted include therefore
selects that variant, not the repository reference header. Both variants use
strict C11, `-Wall -Wextra -Werror -pedantic`, ASan and UBSan, with sanitizers set
to stop on errors. Compilation and runtime must succeed and outputs must match.

[validation.json](validation.json) records all 16 successful compile/run outcomes:
transfer-size and encoder boundaries; ordered PIO/endian/padding/partial failures;
INIT debit exhaustion and all 16-bit response lengths; CONFIG transaction poison
and no-refund behavior; independent TC4/TC0 pools and shared sequence/readiness;
connected CONFIG/ACK access failures; and the ordinary two-chunk flow with all
660 individual I/O failures. The oracle additionally refuses changed numeric
and combined-operator tokens. No fixture was weakened or restyled to pass.

Pinned strict checkpatch ran against the entire revised compile patch **without
exclusions**. It reports **zero source-file errors, warnings or checks**. Its
unfiltered overall result remains **1 error, 1 warning, 0 checks, 878 lines**:
missing Signed-off-by and the generic new-files MAINTAINERS reminder. The complete
output is retained in validation.json. These submission metadata matters remain
visible; no fabricated sign-off, pretend maintainer or blanket exclusion is used.
The historical 85-error result is preserved in the original proposal.

The common repository gate passes on proposal parent `7af83151`: 192 profiles,
unchanged grandfathered metadata debt of 37. Linux package-provenance fixtures
are skipped locally and remain mandatory in CI. Python/JSON syntax, links,
diff checks and sensitive/artifact exclusions were reviewed for this revision.

## Exact integration handoff

The revised complete patch SHA-256 is
`2c2b243b862044dff6253602d1b3d283ceb4e836dfdb8350c392319250d3e22a`.
Root should copy **this** complete patch to the previously proposed canonical
`proposals/0001-lib-mt6797-hif-compile.patch` destination, rather than appending
the header-only style diff or using the historical payload. The adapter,
Kconfig, Makefile, profile fragment, planned canonical position, shared provider
series and source-refresh impact are unchanged from the
[original integration proposal](../integration-proposal.json) and
[provider impact record](../provider-impact.json). Root has accepted that shared
source refresh approach in principle; exact integration/build admission remains
its action. Do not silently reuse the historical patch checksum.

The next meaningful validation is the actual isolated arm64 kernel build through
the existing explicit Buildbox workflow in the [build plan](../README.md).
This packet runs no kernel compile, sparse, backend command or device action.
It adds no probe, resource acquisition, mapping, runtime caller or power action.
No Wi-Fi hardware or driver usability claim follows from formatting or host tests.
