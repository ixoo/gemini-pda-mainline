# Complete native controller kernel link

The [Buildbox-only builder](build-full-kernel.py) compiles the complete native
kernel from [forty pinned patches](full-kernel-inputs.json): the previously
compiled controller composition, the emergency reset correction, and historical
patch 0001's A72 refusal/configuration declaration. It does not select the old
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
