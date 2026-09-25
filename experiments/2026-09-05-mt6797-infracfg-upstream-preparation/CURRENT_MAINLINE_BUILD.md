# Current-mainline reset topic build

The accepted six-patch revised reset topic passed sparse patch replay against
mainline commit `165768bb70265b5c38cf0b73fafd75be235f8b14`, but that does
not prove full-tree compilation. The `mt6797-infracfg-current-mainline`
profile runs the unchanged canonical-order series and existing isolated KUnit
configuration against that exact upstream commit. It is a compile/test profile,
not a device candidate or a replacement for the validated historical profile.

The commit was the advertised upstream `master` ref when checked on
2026-09-25. Its Makefile identifies `7.3-rc4`. Buildbox fetched the 269,928,430
byte codeload archive under the shared build lock, verified SHA-256
`0b93d1066473e53d981fdbad5ecd27831fb80ca08c0abea0884de214ced09412`,
and observed the expected first archive entry
`linux-165768bb70265b5c38cf0b73fafd75be235f8b14/`. The complete archive
remains in Buildbox's managed cache; no source tree was copied to the host.

Run once from a clean pushed checkout:

```sh
KERNEL_PROFILE=mt6797-infracfg-current-mainline ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-infracfg-current-mainline ./scripts/buildbox fetch-package
```

Require the source identity, all six applied patch hashes, resolved KUnit and
clock/reset configuration, ARM64 final link and complete package validation.
The already tested `7.3-rc1` source state and default profiles are unchanged.
Compilation does not establish reset-controller hardware behavior, provider
failure unwinding, maintainer ordering or human DCO certification.

## Completed validation

The exact pushed revision `18a238790c8e47b2357015a762f20782766ef916`
built on Buildbox with all six patches applied, a successful ARM64 final link,
118 DTBs and a validated 132-member package. The package was fetched through
the normal checksum and provenance gate. Its complete inventory digest is
`7afbe62e9ba5935f2b3c1e0a7fa5b5fc92832d8d7e2b91a73927fe6fc0479bc5`.
The [sanitized receipt](results/current-mainline-validation-20260925.json)
pins source, patchset, configuration and image identities.

One bounded QEMU boot of that exact package passed the eight intended reset
cases and shut down normally, but the strict two-suite classifier refused an
additional unrelated refcount suite. A distinct second boot used the current
KUnit source's `kunit.filter_glob=*reset*` option to select the two target
suites. Both suites and all eight cases passed with zero failures or skips; QMP
recorded guest-requested shutdown, QEMU exited zero and stderr was empty.
Private serial and QMP logs remain ignored; their serial digests are in the
receipt. These are arithmetic and descriptor tests, not provider probe or
hardware-reset tests.

The current prepared tree's infracfg binding, MT6797 DTS and public reset
header have the same complete hashes as the accepted optional-binding schema
inputs. The package's DTBs also compiled. This supports reuse of the earlier
focused schema result for those byte-identical inputs; no new `dt_binding_check`
or `dtbs_check` was executed on the current tree. Final upstream submission
still needs the actual authors' certification and maintainer ordering decision.
