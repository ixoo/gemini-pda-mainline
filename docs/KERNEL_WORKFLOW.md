# Pinned stable-kernel patch workflow

This repository stores an ordered patch series and the inputs needed to apply it
to a verified stable Linux release. It does not store a Linux source tree or
build outputs.

## One-command build

From macOS:

```sh
./scripts/dev-vm build-kernel
```

That command performs the complete workflow inside the ARM64 development VM:

1. reads `kernel/manifest.json`;
2. downloads the pinned kernel.org tarball into the guest cache;
3. verifies its SHA-256 before extraction;
4. creates a managed source tree on the guest ext4 filesystem;
5. applies every patch named in `patches/series`, in order;
6. starts from arm64 `defconfig` and merges the project fragments;
7. builds `Image` and all arm64 DTBs out-of-tree;
8. packages the Image, MediaTek DTBs, configuration, provenance, and checksums
   under `~/artifacts/gemini-pda/`.

The download, source, build, and artifact locations never live in the macOS
checkout. Print their exact guest paths with:

```sh
./scripts/dev-vm kernel paths
```

## Patch series

Create logical commits in a disposable development clone, then export them with
`git format-patch`. Store the resulting files below a directory named for the
baseline and list them in application order:

```text
patches/
  series
  v7.1.3/
    0001-arm64-dts-mediatek-add-gemini-pda.patch
    0002-clk-mediatek-add-required-clock.patch
```

`patches/series` would contain:

```text
v7.1.3/0001-arm64-dts-mediatek-add-gemini-pda.patch
v7.1.3/0002-clk-mediatek-add-required-clock.patch
```

Blank lines and lines beginning with `#` are ignored. Missing files, unsafe
paths, whitespace in paths, checksum failures, and patches that do not apply
cleanly stop the build before compilation.

When the series changes, the next preparation replaces only the generated,
versioned source tree. Do not make unique edits in that managed tree; author
changes in a separate Git clone and export them back into this repository.

## Kernel configuration

The manifest names an upstream base configuration and an ordered list of config
fragments. The current fragment is `configs/gemini.fragment`. Add a symbol with
the patch that requires it. Kernel `merge_config.sh` reports redundant or
overridden values, and `olddefconfig` resolves new dependencies.

## Individual stages

```sh
./scripts/dev-vm kernel status
./scripts/dev-vm kernel check-latest
./scripts/dev-vm kernel prepare
./scripts/dev-vm kernel configure
./scripts/dev-vm kernel build
```

The manifest remains pinned until reviewed and changed in Git. `check-latest`
only compares it to kernel.org; it never changes build inputs automatically.

Set `BUILD_MODULES=1` inside a guest shell when modules are needed. The default
early-bring-up build produces the uncompressed arm64 Image and DTBs only.

## Moving artifacts to the flashing machine

After reviewing the guest artifacts:

```sh
./scripts/dev-vm export-artifacts
```

This creates a timestamped, Git-ignored host directory. Verify its
`SHA256SUMS` and the provenance metadata before transferring selected files to
the separate Windows flashing machine. The normal workflow must never package
or write the preloader, NVRAM, GPT, or a whole-device image.
