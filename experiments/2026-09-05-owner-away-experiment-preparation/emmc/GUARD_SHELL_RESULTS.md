# eMMC logger guard exact-shell result

The one assigned Buildbox fixture invocation passed all 52 cases using the
exact retained ARM64 BusyBox and canonical QEMU. It exercised the published
source at `4038246fe16effe1ef3a18eebce85e441029c36d`, after host and independent
review described in [the preparation record](GUARD_SHELL_PREPARATION.md).
Collection and completion drafts remain disabled and runtime facts remain unset.
No physical admission, candidate revision or first-baseline protocol changed.

## Attributable invocation and receipt

The shared Buildbox lock was acquired before the userspace dispatch lock, both
nonblocking. Setup Git-fetched the exact published revision, checked its origin
and clean state, checked free space and verified the canonical emulator digest.
The established checkout was confirmed before execution. The execution step
reacquired both locks and repeated source, free-space and emulator checks.

Only the 1,914,704-byte public BusyBox binary was transferred, extracted from
the retained historical pre-authentication initramfs using the already reviewed
archive parser. Its public Ubuntu package provenance, archive, parser and
binary digests are recorded in the preparation document. Intake had the
prepared 30-second ceiling and 1,914,705-byte cap and required the exact length
and digest before making the file executable. No image, source tree,
authentication material or credential was transferred. There was no build or
candidate reconstruction/retest.

| Measurement | Result |
| --- | --- |
| Setup | Exit 0, complete stdin, 300-byte stdout, empty stderr; 3.941 seconds |
| Exact fixture cases | All 52, in the fixed published order |
| Fixture elapsed time | 61.183 seconds |
| Complete transfer/execution transport | 62.309 seconds |
| Transport result | Exit 0, complete stdin, no interruption or timeout |
| Fixture stdout / stderr | 2,846 bytes / 0 bytes |
| Invocation count | One; no retry |
| Per-case / suite ceiling | 90 / 600 seconds, with one-second child cleanup reserve |
| Outer invocation ceiling | 660 seconds, plus five seconds for forced cleanup |

The exact returned stdout is retained as
[`guard-shell-exact.json`](guard-shell-exact.json), SHA-256
`4743d51e1720763361fcdfba127ce56f18b1e56f6380e0d73f6e9176b1b7e4d5`.
It binds all source and executable hashes, the complete ordered case inventory,
the guard and original composed-program hashes, and the genuine baseline-tail
hashes. Its generated program hashes match the host receipt exactly. BusyBox
digest is `52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`;
QEMU digest is `4f55e2e88dc05dc0f619562d5795b8eb25ed2ad2547504fb4835207a6911c350`.

The remote dispatch removed its transferred binary and fixture work directory
and asserted their absence before returning zero. The local temporary binary
was also removed. Locks were released on process exit. Bounded transport,
setup and dispatch diagnostics remain under ignored private development
evidence; the public fixture receipt contains no credentials or personal paths.

Independent local receipt review recomputed the published source and generated
program hashes, checked the exact ordered inventory, executable pins, budgets,
process byte counts and dispatch-script digests, and found no gap. Cleanup
attribution follows the successful bound dispatch script; no additional remote
probe was used. The sanitized publication passed JSON, link and sensitive-path
checks and the common repository gate with all 189 profiles. Its Linux-only
kernel-package provenance test was skipped on macOS; no kernel build, DT/schema
test or device run was needed or performed for this fixture result.

## Scope of the result

The passing claim is `guard-before-fixed-body-and-exact-dispatch-only`.
It establishes exact-shell guard behavior, refusal-before-body, checked
pre/post composition, exact read dispatch and the bounded fixture controls.
Original full pre/post scripts were syntax-checked, then only their verified
body boundary was intercepted. Read execution reached only the fixed sentinel.
The receipt explicitly records no device access and no target bodies executed.

This is not an eMMC read result, logger continuity or seal result, baseline
acceptance, transport-to-device proof or hardware-support claim. Existing body
and orchestration evidence retain their separate scope. The target's single
16 MiB request, 20-second observer/40-second outer deadline, final independent
log preservation and attributable recovery requirements are unchanged.

The private eMMC launcher now pins the corrected shared baseline verifier and
the published inert guard generator. Its 17 launcher and 20 completion methods
passed normally and with Python optimization, using the actual shared archive
verifier and exact generator. The private checkpoint manifest is
`85cbcef2611855e7552d02289ae02fe4dbe4d3154065cb66f0fe8e54eaa78cdd`.
These drafts remain preparing with execution disabled. A verified first
authenticated baseline plus changed-ID recovery and separate packet admission
remain runtime prerequisites; this fixture does not admit them.
