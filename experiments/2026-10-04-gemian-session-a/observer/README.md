# Passive REG06 observer inputs — parked checkpoint

These independently written GPL-2.0-only snippets implement the
[adapter review](../REG06_ADAPTER_REVIEW.md) design. The MIT generator applies
bounded exact-parent replacements to three pinned Gemian GPLv2 files on
Buildbox and emits an internal format patch. It does not build or install a
kernel. The synthetic patch author is explicitly non-certifying, without a
DCO sign-off; this is diagnostic preparation, not an upstream submission.

The [final patch](../patches/0001-diagnostic-observe-existing-REG06-read.patch)
replayed exactly against its pinned parents on Buildbox. Style review reports
zero errors; intentional findings are recorded in the
[preparation receipt](../results/observer-preparation.json). Static review
checked pointer ownership and the shared transfer core. The first compile
attempt linked, then failed an incorrect built-in metadata package check. That check is corrected but has not been rerun. The roadmap
review in `06769f76` parks this observer because it changes no current mainline
decision; C1 does not wait on it. Patch mode fidelity and runtime validation
remain pending, with no deployable candidate or admitted device test.

## Entry and scope

The proposed boot-only, read-only parameter is `bq25890.reg06_observer=1`.
Without it, the extra attribute is absent and the observer never arms. With it,
first reading `/sys/devices/platform/bq25890-user/reg06_observe` arms one result;
actual resolved sysfs path must be verified in the future candidate. That read
changes diagnostic memory only, and does not submit a charger request.
Subsequent reads report pending or the immutable terminal result; no rearm or
write attribute exists. Do not use this proposed path on the currently running
unmodified Gemian kernel.

Only an existing VREG configuration read with register six, mask `0x3f`, shift
two is eligible. Other byte-helper callers remain ineligible. The existing
charger I2C mutex protects arm/consume/result state; consume precedes the
eligible request. The diagnostic wrapper takes the same adapter lock and calls
the same core transfer routine as the normal wrapper. Identity mismatch falls
back to the original two-message request and produces no accepted observation;
it must not skip, repeat or change the ongoing policy operation.

Pending record/message pointers exist only under the adapter lock. The normal
master matches the exact message pointer, validates controller fields under its
mutex, and exposes the active record only during that existing transfer. It
clears the active pointer before unlocking. The FIFO count and IRQ values are
copied from values already read by that transfer; no additional MMIO read or
I2C request is added. The driver copies the returned byte into its result only
when the acceptance predicate passes, before releasing its I2C mutex.

Every failed or incomplete result omits the register value. The normal transfer
return and charger data/policy behavior are preserved, including inherited
errors and reset behavior. Capturing a result does not repair the vendor driver
or validate the following configuration write. An admitted host collection
will need a finite pending deadline and must stop without rearming on timeout.

## Focused host validation

Run:

```sh
python3 experiments/2026-10-04-gemian-session-a/observer/test-result.py
```

This compiles the actual header predicate against minimal integer-type stubs.
The 159 cases include valid zero and `0xff` values, every four-bit FIFO count,
negative/partial transfer returns, completion/error combinations, missing
controller metadata and duplicate/missing transfer entries. It does not test
kernel integration, mutex ownership, sysfs behavior or physical transport.

Compile the admitted single patch with:

```sh
GEMINI_BUILD_EXPERIMENT=gemian-reg06 ./scripts/build-kernel --backend buildbox
```

The lane uses the pinned native config and toolchain with a distinct kernel
release name. It excludes the separate Wi-Fi diagnostic patches. Successful
compilation will not admit a boot candidate or prove device behavior.
