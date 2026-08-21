# A34 production provenance-owner boundary

## Authority decomposition

The production owner must eventually satisfy three distinct statements:

1. a known-good platform or external reset completed;
2. the exact secure-firmware epoch began with private A72 replay state zero
   and no writer changed it before publication; and
3. the complete Linux A34 topology, mapping, owner, provider, transaction,
   fault, P30, and operation-attempt observation still matches the pure
   evaluator's immutable tuple.

No single current source supplies all three. The first production work must
preserve raw observations without converting them into authority.

## TOPRGU preservation result

The vendor and LK headers agree that status is the 32-bit word at TOPRGU offset
`0x0c`. The pinned LK implementation contains a trivial reader but no caller.
Its initialization never writes that offset. Mainline maps the resource before
it initializes watchdog state. Therefore a single `readl()` after successful
mapping and before `mtk_wdt_init()` is ordered ahead of the first mainline
watchdog mutation and does not change hardware.

The snapshot ABI must retain the complete raw word and explicit validity. It
must not map raw zero, hardware-watchdog, or software-watchdog bits directly to
either positive A34 provenance enum. Unknown bits remain data, not success.

## Preloader ram-console boundary

The retained ram-console region begins at `0x44400000` and is already reserved
`no-map` in the board DT. The pinned LK and vendor-kernel layouts agree on:

- signature `0x43474244`;
- 32-bit offsets and sizes for preloader, prior-preloader, LK, prior-LK,
  Linux, and console records; and
- the preloader record's first 32-bit word as its semantic reset status.

The public LK source identifies normal boot as zero and software watchdog as
two for its abnormal-boot policy, plus separate EINT and SYSRST bits. That is
not a complete preloader enum, and historical runtime value five remains only
a generic watchdog-class observation. A future reader must validate every
offset, alignment, size, and region bound before copying one immutable status
word. It must reject legacy fallback offsets and malformed headers for A34.

## Secure private replay boundary

In the retained secure payload, analysis address `0x11ea24` is the private
one-byte A72 replay ledger. It is zero in the exact payload image. The complete
static xref set is:

- `0x102a58` and `0x102c14`: deferred teardown reads the byte and clears the
  target bit after per-core teardown;
- `0x103ca0` and `0x103e5c`: A72 CPU-on reads the byte and sets the target bit
  after the power-on sequence.

These are analysis addresses under the previously published `0xff3c0` mapping
convention, not physical addresses and not a non-secure access proposal.

The exact A26 boot veto prevents the CPU-on set path before the production
owner opens. However, image-zero plus veto is owner-safe only after a proven
fresh secure-platform epoch. It is not safe after an unclassified warm reset,
and active PSCI `AFFINITY_INFO` cannot be used to inspect the byte.

## Selected implementation slice

Add only a default-off, raw TOPRGU boot-status capture to the existing MediaTek
watchdog owner. Requirements:

- capture exactly once after resource mapping and before `mtk_wdt_init()`;
- store raw 32-bit status plus validity in the per-device object;
- expose only a typed read-only snapshot, not a safe/unsafe classifier;
- test invalid, exact, every-bit, and immutability behavior without MMIO;
- add no ram-console mapping yet;
- add no A34 caller or CLOSED-to-AVAILABLE writer; and
- preserve A26, A14, P30 FREE, and all provider/hardware/PSCI exclusions.

The later combiner must require independent agreement among the raw TOPRGU
snapshot, validated preloader status, an explicit cold/platform epoch, the
secure-image/writer proof, and the complete A34 observation immediately before
atomic publication. Any missing input keeps the owner CLOSED.

## Rejected shortcuts

- `WDT_STATUS == 0` alone;
- a hardware- or software-watchdog bit alone;
- `boot_reason=0` or `androidboot.bootreason=power_key` alone;
- Linux BSS or static-object zero;
- Linux membership as an alias for firmware-private `big_on`;
- PSCI `AFFINITY_INFO` as a passive reader;
- accepting a warm reboot as a fresh secure epoch; or
- combining capture and lifecycle publication in the same first patch.
