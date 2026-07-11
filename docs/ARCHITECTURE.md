# Architecture and ownership

## Target architecture

The project aims to move the maintainable boundary as far down the boot stack as practical without making risky boot-firmware replacement a prerequisite for useful Linux support.

```text
Phase 1: safe enablement

MediaTek BootROM                 immutable silicon
  -> retained preloader / ATF    DRAM, secure-world, early platform init
  -> retained Planet LK          development shim and recovery choices
  -> upstream-derived Linux      generic MT6797 support + Gemini board DT
  -> standard initramfs/rootfs   distribution-neutral userspace

Phase 2: boot ownership

MediaTek BootROM
  -> retained or replaceable early firmware, evaluated separately
  -> maintained U-Boot/open LK chainloader
  -> standard Image/DTB/initramfs selection
  -> owner-controlled verification and recovery keys
```

Replacing the preloader or secure firmware is a separate stretch project. Linux hardware enablement must not depend on it.

## Ownership boundaries

| Layer | Desired owner | Project rule |
| --- | --- | --- |
| Linux generic drivers | Upstream subsystem | Extend generic drivers; no Gemini-only copies |
| MT6797 SoC description/support | Upstream Linux/DT maintainers | Keep reusable SoC work separate from board data |
| Gemini board Device Tree | Upstream Linux | Declarative board description with reviewed bindings |
| Temporary integration series | This repository | Pinned, reviewable, disposable after upstream merge |
| Initramfs/build tooling | This repository or distribution | Reproducible and non-destructive by default |
| Root filesystem | Distribution | No project-specific userspace requirement |
| Boot selection/recovery | Device owner | Preserve known-good path and owner-controlled artifacts |
| Modem/Wi-Fi firmware | Device firmware boundary | Retain only where unavoidable; expose standard kernel/userspace interfaces |

## Non-negotiable principles

### Upstream is the product

Every local kernel change needs:

- an upstream destination;
- a responsible issue;
- test evidence;
- a stated dependency chain;
- a deletion condition.

Branches may be rebased. GitHub issues and public mailing-list archives are the durable project record.

### No vendor-code laundering

Vendor source is evidence, not automatically acceptable implementation. Facts may be re-expressed; copied code must have clear provenance, compatible licensing, and a reason it cannot be replaced with an existing upstream abstraction.

### Generic before board-specific

Changes should layer cleanly:

```text
binding -> generic driver capability -> MT6797 SoC node -> Gemini board node
```

A Gemini quirk in a generic driver must be narrowly justified. Board policy does not belong in a reusable SoC driver.

### Standard subsystem contracts

Userspace should see ordinary Linux interfaces. Examples include DRM/KMS, evdev, power_supply, hwmon/thermal, MMC, USB role switch, ALSA ASoC, rfkill, and a documented modem transport usable by ModemManager or oFono.

### Firmware is isolated

Some embedded firmware will likely remain opaque. Acceptable firmware:

- runs on an isolated device or coprocessor;
- is loaded through a standard kernel mechanism where possible;
- does not require an out-of-tree proprietary kernel module;
- has documented version, source, checksum, and redistribution status outside Git when redistribution is not allowed.

### Reproducibility and evidence

Every boot artifact must be traceable to source revisions, configuration, toolchain, and packaging inputs. Hardware claims progress through the support-matrix states; compilation alone never means `working`.

### Safety is architectural

- Development targets a non-primary boot slot.
- Recovery remains independently bootable.
- Scripts reject ambiguous block-device and partition targets.
- NVRAM, GPT, preloader, and secure firmware are outside ordinary workflows.
- Logs are redacted before publication.

## Patch lifecycle

Temporary patches live under a directory named for their upstream base only when active work needs them. Each series should contain:

```text
patches/<upstream-base>/<topic>/
  README.md       purpose, dependencies, owner, upstream target, status
  series          ordered patch list
  0001-*.patch
```

Once merged upstream, remove the patches and replace them with the first containing release/commit in the issue and support matrix.

## Decision records

Material decisions belong in issues labeled `type: decision`. A decision must state context, options considered, safety impact, upstream impact, and reversal conditions. This prevents repository-local convention from silently becoming a new downstream ABI.
