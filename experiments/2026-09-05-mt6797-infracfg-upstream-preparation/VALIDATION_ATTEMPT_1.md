# First isolated validation attempts

Both original gates **REFUSED**. Preserve these outcomes; no repeat, kernel
rebuild, contract relaxation or hardware action followed them. This record does
not establish submission readiness or new Gemini hardware support.

The execution checkout was the clean, Git-fetched revision
`30f20586cf19293fd985e4aec838c75b3d1c94c6`. The retained package was built at
`4ec63076aeb6388ba24b33ee20afcf19ced541e1`; its 132-member inventory,
`8393a89ef3dbdb3bbae967d6adc78cf5a1cd907c21f21e9ba2efc015ba041917`,
passed complete verification. Its actual release is
`7.3.0-rc1-mt6797-infracfg-upstream-kunit`. The historical package directory's
`7.1.3` label does not change that identity. No package was replaced or copied.

## Preconditions and receipts

The exact checkout passed the Linux QEMU 28, setup 4 and schema 10 fixtures.
These include real Linux parent-death and signal-boundary fixtures. The final
log-display command failed after all checks had completed; the retained test
logs, each ending in `OK`, are the test authority.

The [runtime prefix checker](scripts/verify-qemu-runtime-prefix.py) was streamed
as a read-only host check before and after the sole guest run. Both checks
verified all 2257 prefix members by type, link target and regular-file hash,
rejected extras except the pinned setup receipt, hashed all 50 resolved
libraries and compared actual eager loader resolution. Its inspection invokes
version and supported-machine/CPU enumeration only, without a guest kernel.

[The receipt inventory](results/validation-30f20586/inventory.json) pins the
complete copied logs and receipts. Embedded log hashes were verified after
fetch. Only logs and receipts were fetched; no Linux sources, firmware or
package bytes were transferred. The raw serial bytes retain CRLF and the
synthetic build banner `gemini-pda@devvm`; the build provenance establishes
Buildbox execution, not a native VM build.

## QEMU: original two-suite gate refused

The [original receipt](results/validation-30f20586/infracfg-qemu-4ec63076-attempt-1/result.json)
records `incomplete, unexpected or duplicate KTAP structure`. Its frozen
contract expected two suites and eight cases, while the
[complete serial log](results/validation-30f20586/infracfg-qemu-4ec63076-attempt-1/serial.log)
contains a top-level `1..3` plan and twelve passing cases:

| Suite | Cases | Observation |
| --- | --- | --- |
| `refcount_interrupt` | single IRQ change, nested change, multiple change, IRQ save | four pass, unexpected by original contract |
| `mtk-reset-bounds` | map bounds, register pairs, invalid bank, missing banks | four pass |
| `mt6797-infracfg-reset` | descriptor, thermal, PWRAP, unexposed IDs | four pass |

Every suite has an exact four-case plan and zero failures or skips. QEMU exited
zero after 0.852986 seconds, within the 45-second ceiling. QMP recorded resume
and guest-requested shutdown; serial ended in `reboot: Power down`. Stderr was
empty, the owned process group was absent, and neither TERM nor KILL was needed.
The two virtual CPUs, 512 MiB memory, no network/disk/initrd, fixed QEMU data
prefix and exact kernel input are recorded in the receipt. No panic, oops or
warning appears in the complete serial log.

### Attribution of the additional upstream suite

At pinned upstream `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`,
`kernel/irq/Makefile` line 19 builds `refcount_interrupt_test.o` directly under
`CONFIG_KUNIT`. Disabling `CONFIG_IRQ_KUNIT_TEST` excludes the separate
`irq_test.o`, not this suite. A scan of test-specific config symbols therefore
missed an unconditional core-KUnit dependency.

| Source | SHA-256 |
| --- | --- |
| `kernel/irq/Makefile` | `86c59b3e60c84831ed9d3b68d04343aee5559ad116d711b7fb50b7e8d1911f1e` |
| `kernel/irq/refcount_interrupt_test.c` | `c84e48fd09f18f407a39bdbd0a4986492a0fa63a212e7b6fd052ce44495eaf7d` |

All four source cases were inspected. They exercise bounded local virtual-CPU
interrupt disable/enable counting and save/restore interactions; suite entry
and exit assert interrupts enabled. They are not pure arithmetic tests, but
perform no physical MT6797 access, storage operation or reset pulse. The two
intended suites inspect mapping, descriptor and register-address arithmetic,
including invalid-bank output sentinels; they perform no MMIO or provider
registration. These facts explain the extra suite without changing the original
admission contract.

A separately reviewed offline accounting of these retained logs could recognize
the exact three suites and twelve cases, while retaining the original refusal.
It would need to pin the full serial/QMP/result hashes, validate all original
process/input limits and refuse missing, duplicate, skipped, failed or extra
cases. This is a proposal, not an amended execution contract or a pass claim.
No new guest run is needed to examine the already complete evidence.

## Schema: generated output exceeded the file-size ceiling

The [original schema receipt](results/validation-30f20586/infracfg-schema-4ec63076-attempt-1/result.json)
records `command failure`. Under the normal nonblocking Buildbox lock, full
source-integrity verification first passed in 14.941708 seconds. The binding
command then exited 2 after 203.062663 seconds, before its 300-second deadline.

[The complete diagnostic](results/validation-30f20586/infracfg-schema-4ec63076-attempt-1/dt_binding_check.stderr)
shows `dt-mk-schema` raising `OSError: [Errno 27] File too large` while writing
`processed-schema.json`. Make deleted that incomplete generated output. The
collector applies its 16 MiB log ceiling through `RLIMIT_FSIZE`; that inherited
limit also constrains regular generated files. This identifies a tooling limit,
not a demonstrated binding defect. The tiny stdout/stderr logs themselves did
not exhaust the log allowance.

All eleven protected source files and nine protected build files matched before
and after the failure. The owned process group was absent and needed no TERM or
KILL. The later DTB make check, direct validation, node/schema checks and full
source-integrity-after command did not run. The targeted source comparisons
must not be described as a completed full-tree postcheck.

The original failure and partial-output deletion are retained. No limit increase,
retry or source/build repair was performed. Any future schema window needs a
reviewed distinction between bounded diagnostic output and legitimate generated
schema size, with refusal fixtures and preserved exact kernel inputs. Ordered
follow-up remains in the [roadmap](../../docs/ROADMAP.md#upstream-delivery-gate).

## Later checker review: receipt snapshot correction

Independent review reproduced a hash/parse race in the originally streamed
prefix checker: it hashed the setup receipt, then reopened that path to parse
its inventory. Replacement between those reads could associate the old digest
with a different accepted inventory. This is a demonstrated checker defect,
not evidence that the retained historical receipt was replaced. The original
attempts and before/after receipts remain immutable, with their original scope.

The corrected checker reads one bounded snapshot (at most 4 MiB), hashes those
bytes and parses those same bytes. A nonblocking, no-follow open and descriptor
regular-file check reject substituted symlinks or special files; size mismatch
or an exceeded bound refuses. Eight offline fixtures pass. The deterministic
race fixture changes the receipt and one of 2257 tiny prefix files immediately
after the read; the real setup prefix verifier rejects the changed file against
the hashed original inventory. No emulator, schema or device run was repeated
for this correction, and no historical receipt was replaced or reclassified.
