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
