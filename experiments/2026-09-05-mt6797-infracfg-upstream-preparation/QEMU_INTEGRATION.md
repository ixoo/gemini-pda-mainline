# Virtual-test preparation integration

The coordinator adopts the five QEMU preparation files through worker commit
`610a6ae9`. The kernel remains the validated `4ec63076` package; this work adds
no kernel, DT, configuration, device session or hardware-support claim.

## Review and corrections

The initial `417fbbfc` helper passed its 20 synthetic tests, but independent
review reproduced three missing refusal/cleanup cases: silent directory-walk
errors, descendants surviving a successful leader exit, and an interrupted
runner leaving its separate-session child active. Source review also found
that `-nodefaults` did not disable host QEMU configuration. These were corrected
in `c5b30dfa`, with bounded real-process fixtures, `-no-user-config`, Linux
direct-child parent-death protection and explicit descendant limitations.

The next review reproduced a signal arriving during final receipt publication.
`610a6ae9` resolves this with an explicit completion boundary after validation,
cleanup and log hashing. Independent review passed 26 host tests, including six
real signal timing cases and additional prior-mask restoration checks. One Linux
parent-death fixture remains an execution prerequisite. No guest ran during
these reviews. The pinned upstream KUnit output source agrees with the parser's
required suite/case formatting; synthetic logs alone were not its oracle.

Integration clarifies the SIGKILL wording around atomic replacement and adds
the isolated tool dependency: a fixed `-L` directory derived from the selected
executable prefix, neutral receipt paths, and exact executable/setup-receipt
identity checks. A new synthetic setup test covers the positive case and wrong
prefix, changed executable/receipt, missing data directory and symlink refusals.
The command fixture checks the data path and existing guest restrictions.

## Tool setup and run boundary

The [QEMU setup](QEMU_DEPENDENCIES.md) and
[schema environment](SCHEMA_DEPENDENCIES.md) are ready on Buildbox. Both supply
exact input and output receipts. Their setup did not modify system packages,
compiler settings or the retained source/build/package. Independent schema
review checked both hash locks, dependency closure, merged pip reports and live
package/interpreter/compiler/extension identities; it did not repeat installation
or establish binary reproducibility.

For QEMU execution, the coordinator must first run the final helper's complete
fixtures on Linux, including parent-death containment, and verify the exact
retained package. Recheck the full QEMU prefix against the remote setup receipt's
member inventory, and rehash its recorded resolved libraries before and after
the run. The helper's setup-receipt identity check alone does not perform those
full checks. Preserve the immutable prefix while the guest is active.

Use only invocation-local `PATH`, `LD_BIND_NOW=1`, `LD_LIBRARY_PATH` and
`QEMU_MODULE_DIR` as recorded in the dependency note. No loader preload is
selected. Run the committed helper from an exact Git checkout, once, with the
new evidence child `infracfg-qemu-4ec63076-attempt-1`. The 45-second guest budget,
five-second termination grace, two suites/eight cases and independent guest
poweroff attribution remain in [the protocol](QEMU_VALIDATION.md). Every refusal
retains evidence and requires classification before a changed attempt.

The [focused schema collector](SCHEMA_EXECUTION.md) is adopted from worker
commit `036c1b81`. Independent review passed all ten synthetic fixtures and
checked its eleven source hashes, nine protected build hashes and toolchain
identities against the retained receipts. Exact Linux fixtures, live tool and
source checks, and diagnostic review remain execution prerequisites. It must
hold the shared Buildbox build lock and preserve the same source, configuration,
kernel image and objects. QEMU and schema success remain
separate results. No physical test or boot2 request follows from either
preparation or execution.
