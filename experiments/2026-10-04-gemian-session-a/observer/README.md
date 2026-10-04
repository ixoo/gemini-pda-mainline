# Passive REG06 observer inputs — incomplete checkpoint

These independently written GPL-2.0-only snippets implement the
[adapter review](../REG06_ADAPTER_REVIEW.md) design. The MIT generator applies
bounded exact-parent replacements to three pinned Gemian GPLv2 files on
Buildbox and emits an internal format patch. It does not build or install a
kernel. The synthetic patch author is explicitly non-certifying, without a
DCO sign-off; this is diagnostic preparation, not an upstream submission.

The implementation inputs and host result predicate are ready. The first
[generated draft](../results/observer-preparation.json) replayed exactly on
Buildbox. Style review identified new-code formatting/tag placement issues, now
corrected in successor inputs; regenerate/replay before accepting a patch.
Kernel integration/locking validation and Buildbox compile remain pending.
No deployable candidate or device test is admitted.

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

Next generate/replay the patch from clean pushed inputs on Buildbox, inspect
its exact diff and run relevant compile/negative integration checks. Kernel
builds must use `GEMINI_BUILD_EXPERIMENT=gemian-reg06
./scripts/build-kernel --backend buildbox`. The compile lane is prepared, but remains blocked until the final reviewed patch is admitted at
`../patches/0001-diagnostic-observe-existing-REG06-read.patch`. It uses only that
patch and the pinned native config, with a distinct kernel release name.
This checkpoint has not compiled a kernel.
