# Architecture and ownership

## Target architecture

The project moves the maintainable boundary as far down the boot stack as
practical without making risky firmware replacement a prerequisite for useful
Linux support.

```text
Phase 1: safe enablement

MediaTek BootROM                 immutable silicon
  -> retained preloader / ATF    DRAM, secure-world, early platform init
  -> retained Planet LK          development shim and recovery selection
  -> upstream-derived Linux      generic MT6797 support + Gemini board DT
  -> standard initramfs/rootfs   distribution-neutral userspace

Phase 2: boot ownership

MediaTek BootROM
  -> retained or replaceable early firmware, evaluated separately
  -> maintained U-Boot/open LK chainloader
  -> standard Image/DTB/initramfs selection
  -> owner-controlled verification and recovery keys
```

Replacing the preloader or secure firmware is a separate stretch project.
Linux hardware enablement must not depend on it.

## Ownership boundaries

| Layer | Desired owner | Project rule |
| --- | --- | --- |
| Generic Linux drivers | Upstream subsystem | Extend generic drivers; do not create Gemini-only copies. |
| MT6797 support and SoC DT | Upstream Linux/DT maintainers | Keep reusable SoC work separate from board data. |
| Gemini board DT | Upstream Linux | Use declarative board description and reviewed bindings. |
| Temporary integration series | This repository | Keep it pinned, ordered, reviewable, and disposable after merge. |
| Build and initramfs tooling | This repository or distribution | Make builds reproducible and hardware actions safe by default. |
| Root filesystem | Distribution | Require no project-specific userspace ABI. |
| Boot selection and recovery | Device owner | Preserve an independent known-good path. |
| Modem, Wi-Fi, and other firmware | Explicit firmware boundary | Retain only where unavoidable and expose standard host interfaces. |

## Non-negotiable principles

### Upstream is the product

Every local kernel change needs:

- an upstream destination;
- test evidence;
- a stated dependency chain;
- a deletion condition.

Branches may be rebased. Public issues, mailing-list archives, experiment
records, and accepted commits are the durable record.

### Vendor material is evidence

Vendor source and binaries may establish register, resource, and sequencing
facts. They are not automatically acceptable implementation. Any copied code
needs clear provenance and compatible licensing; otherwise re-express only the
independently established facts using an upstream subsystem model.

### Generic before board-specific

Changes should layer cleanly:

```text
binding -> generic driver capability -> MT6797 SoC node -> Gemini board node
```

A Gemini quirk in a generic driver must be narrowly justified. Board policy
does not belong in a reusable SoC driver.

### Driver reuse follows the protocol

Naming similarity is not enough. Compare observed identity, register map,
transport, power/reset/IRQ resources, and firmware ownership with the proposed
upstream driver.

| Evidence | Mainline action |
| --- | --- |
| Same protocol and standard resources | Reuse the existing driver and add only data or a narrow binding extension. |
| Same family with an unrepresented revision | Add a separated variant with an explicit compatibility record. |
| Different register, transport, or ownership contract | Select the matching family driver or add a new driver and binding. |
| Identity or resources remain indirect | Keep the node disabled and design the next discriminating observation. |

Do not make the closest driver emulate a vendor ABI. The current legacy DA921x
case is an example: the observed DA9213/DA9214/DA9215-family contract does not
match the upstream DA9211/A-family probe and therefore needs a genuine legacy
driver or strictly separated variant. See the
[durable boundary](hardware/da921x-i2c6-a72.md).

### Standard subsystem contracts

Userspace should see ordinary Linux interfaces: DRM/KMS, evdev,
power_supply, regulator, hwmon/thermal, MMC, USB role switch, ALSA ASoC,
rfkill, IIO, and a documented modem transport consumable by standard tools.

### Firmware is isolated

Opaque firmware is acceptable only when its boundary is explicit:

- it runs on an isolated device or coprocessor;
- it is loaded through a standard kernel mechanism where possible;
- it does not require an out-of-tree proprietary host module;
- version, source, checksum, and redistribution status are recorded outside Git
  when redistribution is not allowed.

### Reproducibility and evidence

Every boot artifact must trace to a source revision, canonical patch selection,
configuration, toolchain, DTB, initramfs, and packaging input. Compilation is
not hardware support. Observation, inference, and implementation state remain
separate.

Detailed candidate construction and runtime chronology belong in
[`experiments/`](../experiments/README.md). Architecture records stable
ownership and layering; the
[support matrix](HARDWARE_SUPPORT.md) records concise current runtime claims.
Exact audit counts, rejected-profile lists, build identities, and other
point-in-time snapshots stay in their experiment records. The
[roadmap](ROADMAP.md) is the sole owner of ordered remediation and
implementation steps; other durable documents state constraints and link to
it.

### Safety is architectural

- Development targets only an explicitly authorized non-primary boot slot.
- Recovery remains independently bootable.
- Scripts resolve partition identities from the live GPT and reject ambiguous,
  active, mounted, undersized, or unwritable targets.
- NVRAM, GPT, preloader, and secure firmware are outside ordinary workflows.
- Hardware-writing actions are explicit, bounded, flushed, read back, and
  checksummed.
- Logs and hardware evidence are redacted before publication.

## Patch and profile lifecycle

Temporary patches live below the pinned upstream-base directory. The canonical
`patches/series` is the ordering authority; a manifest-pinned experiment profile
may select a canonical-order subsequence:

```text
patches/
  series                         canonical ordered superset
  series-<named-experiment>      optional profile subsequence
  <upstream-base>/
    0001-*.patch
```

Every selected patch must also appear in the canonical series in the same
relative order. One patch should represent one logical upstream change.
Experiment-only policy belongs in a named configuration fragment and profile,
not in `configs/gemini.fragment`.

The manifest's default configuration profile remains `full`; diagnostic
builds explicitly select a named experiment profile. The rule and validator
workflow belong in [the kernel workflow](KERNEL_WORKFLOW.md); point-in-time
counts and findings belong in experiment records.

Point-in-time conformance findings belong in a
[profile-series audit](../experiments/2026-07-28-profile-series-invariant-audit/README.md);
remediation order and exit criteria belong in
[Roadmap gate 0](ROADMAP.md#0-repair-the-profile-series-invariant).

Once a change is merged upstream, remove the local patch and record the first
containing commit or release in the relevant issue and support entry.

## Current implementation boundary

The repository currently layers the development path as follows:

```text
retained BootROM / preloader / ATF / LK
  -> validated Android-v0 container on non-primary boot2
  -> Linux 7.1.3 + ordered local integration patches
  -> loader-retained console, keyboard, USB gadget shell, restart
  -> CPU0-7 serviceability baseline
  -> DVFSP handoff and shared AP-DMA preservation
  -> MT6797 I2C6 native packed/FIFO short-read and exact short-write contract
  -> legacy DA921x read-only board contract
  -> runtime-proven legacy-family read-only regulator provider
  -> one runtime-proven default-off same-value write/readback
  -> unimplemented production rail ownership and active rollback
  -> unavailable Cortex-A72 CPUs 8 and 9
```

| Layer | Implemented boundary | Deliberately outside the claim |
| --- | --- | --- |
| Boot container | Reproducible, validated non-primary development images | Standard upstream bootloader ownership |
| Console/display | Loader-retained simple framebuffer and fbcon | Native DRM, DSI, panel, and backlight ownership |
| Input | AW9523 plus generic matrix path | Complete key/wake/rollover regression protocol |
| USB | Peripheral gadget Ethernet and development shell | Host mode, role switching, charging, both-port mapping |
| Restart | Native MT6797 TOPRGU restart | Full power-off, suspend, and every reset source |
| CPU | Eight Cortex-A53 CPUs online on the diagnostic baseline | A72, OPP/cpufreq, idle, thermal, suspend, scheduler policy |
| I2C6 | Exact native packed/FIFO one-byte pointer plus one-byte read and one reviewed two-byte same-value write | Arbitrary messages or writes, failure recovery, stress, and resume |
| External regulator | Read-only legacy-family board tuple, two-provider registration, and one default-off same-value write/readback | Active rail transitions, production ownership, rollback, consumers, resume |

This table is an implementation map, not an experiment ledger. Exact runtime
evidence and negative results remain in the linked experiment directories.

## Decision records

Material decisions belong in issues labeled `type: decision`. A decision must
state context, options considered, safety impact, upstream impact, and reversal
conditions. This prevents a repository-local convention from silently becoming
a downstream ABI.
