# Complete native controller kernel link

The [Buildbox-only builder](build-full-kernel.py) compiles the complete native
kernel from [forty-one pinned patches](full-kernel-inputs.json): the previously
compiled controller composition, the emergency reset correction, and historical
patch 0001's A72 refusal/configuration declaration, plus the detector's watchdog
header dependency. It does not select the old
recovery trigger, profile or consumed artifact.

Run `python3 build-full-kernel.py COMMIT JOBS` from the experiment's clean,
pushed Buildbox checkout while holding the normal shared Buildbox lock. The
builder uses the existing pinned Gemian source and GCC 6.3 toolchain. It reuses
a prepared source tree keyed by the complete input manifest, verifies that tree
with the repository's existing integrity tool, and builds in a separate
managed temporary output. The generated DCT input must match the existing
normalized checksum. Configuration permits only the experimental symbol and
the established disabled-ANBOX serialization change. Build identity fields are
fixed; two-build reproducibility has not been established.

The link must contain the capture, recovery and request entry points, contain
no historical delayed recovery callback, and have no unresolved symbols.
Outputs include the linked kernel, symbol map, configuration, logs and checksum
manifest. No Android boot container or minimal filesystem is constructed.
The retained configuration still contains unrelated vendor drivers; a successful
link does not establish their exclusion or authorize running this kernel.

This is an integration check toward a recoverable observation candidate.
Filesystem construction, complete reset/resource isolation, capture preparation,
independent reproduction, container validation and an approved device session
remain separate requirements. Firmware files remain private and are not inputs
to this compile-only package.

The first attempt stopped before compilation because the linker identity check
lacked the pinned library environment. After that correction, full compilation
exposed a missing `ext_wd_drv.h` include path in the detector's native Makefile.
The retained [failure identity and correction](results/controller-build-sources.json)
record that error; isolated object checks had supplied this path explicitly.
The correction adds a configuration-dependent include path to the native rule.
Failed compilation now retains complete logs with a checksum manifest.

The [complete link receipt](results/full-kernel-link.json) records success at
`d19a9c4947614d51363085f6c47a4c7b51ec3964`. All eleven fetched package files
match the remotely validated inventory and checksum manifest. The full source
tree retained its integrity digest through compilation, all required entry
points are linked, and the linked kernel has no unresolved symbols.

Modpost reports 69 section mismatches. The retained observer package reports
the same count, but mismatch identities have not been compared. Native compiler
commands retain `-w`; this is not warning-clean evidence. The controller and
recovery entries and the inspected wrapper symbols reside in `.text`, which
does not establish the lifetime of every downstream callback or data object.
This result closes the complete-link check for these inputs, not device admission.
