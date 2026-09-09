# Gemian USB power-driver selection

Bounded read-only observation begun 2026-09-09 00:39:19 UTC (2026-09-08 local).
The root task was the sole device custodian for these two SSH requests. The
hypothesis was that installed configuration and driver bindings could narrow
the source alternatives without changing USB roles or charger controls.

## Identity and acquisition

Authenticated Gemian LAN SSH returned `3.18.41+`, `aarch64`, boot ID
`6a5395c2-71d0-4392-a397-be3be83b049b`. The first request checked kernel release
and architecture before inspecting configuration or bindings, and recorded
the same boot ID at both ends. The follow-up required that exact kernel and
boot ID before inspection and returned the same ID afterward. This is a fresh
identity check; it does not reuse the older keyboard packet's expected boot ID.

Only filtered `/proc/config.gz`, I2C client names, driver symlinks and filtered
kernel log output were read. The first request included absent `0-0022` and
`1-0022` paths; those yielded nothing and establish no controller absence.
The follow-up used the historical clients' actual `0x25` addresses. No I2C
register files, role attributes, raw memory, debug control interfaces or power
settings were accessed. Both SSH requests exited successfully. No matching
RT9466/BQ25890/FUSB301 kernel-log lines survived in the queried log output;
this cannot establish whether their probes ran or succeeded earlier.

Private, mode-0600 captures remain under the ignored directory
`artifacts/device-runtime-evidence/usb-owner-config-20260909T003919Z/`.

| Capture | SHA-256 |
| --- | --- |
| `raw.txt` | 69af10fe1cd7043b46d5b32aa7c36827a364cb56810ea65c785c3d2be13744bd |
| `bindings-log.txt` | b46fdffab9ea0d7b04fcceee6512a3252efdf1691437cacb6a83ba545fb9e8f1 |

## Observed configuration and bindings

| Item | Current observation |
| --- | --- |
| `CONFIG_MTK_BQ25896_SUPPORT` | `y` |
| `CONFIG_MTK_RT9466_SUPPORT` | `y` |
| `CONFIG_MTK_BQ25898_DUAL_SUPPORT` | Not set |
| `CONFIG_MTK_BQ25890_SUPPORT` | Not set |
| `CONFIG_USB_C_SWITCH` | `y` |
| `CONFIG_USB_C_SWITCH_FUSB301` / `FUSB302` | Both `y` |
| I2C0 `0x6b` | `sw_charger`, bound to `bq25890` |
| I2C0 `0x70` | `buck_boost`, bound to `fan49101` |
| I2C0 `0x25` | `fusb301a`, bound to `FUSB301_1` |
| I2C1 `0x25` | `fusb301`, bound to `FUSB301_0` |
| I2C0 `0x53` | `rt9466`, unbound |

The BQ25890-named driver's binding despite the unset BQ25890-named option is
consistent with the vendor BQ25896-selected path: the pinned power Makefile
at lines 43–44 selects `bq25890.o` and `charging_hw_bq25890.o` there under
`CONFIG_MTK_SMART_BATTERY`.
Neither configuration labels nor driver names uniquely identify the charger
silicon. The two FUSB301 bindings support keeping their software paths distinct;
no FUSB302 silicon identity follows from the second build option's name.

## What changes, and what remains open

For the pinned source, the observed configuration excludes the dual-BQ25898
xHCI branch and includes the conditional BQ25890/RT charger-interface branch.
This is source/configuration correspondence, not an exact binary match or an
observation of a live OTG invocation. The running selection scalar was not read.

The [source receipt](source-inputs.json) now also pins `rt9466.c`. Its scalar
`chargin_hw_init_done_rt` starts false at line 46 and is set true at line 3033,
at the successful end of probe after registration and initialization. A
whole-tree literal search finds only that initializer and assignment as writers
in the inspected source. An unbound client does not prove the scalar's current
value: a previous successful bind, later removal, or a different running binary
would defeat that inference. Do not promote this observation to a proved active
BQ25890 boost path.

The next useful attribution must join an exact running implementation and
selected charger path with GPIO94 and physical connector identity. It still
requires the electrical ownership contract before any role or boost change.
These observations strengthen the [source investigation](README.md) without
admitting a USB power operation or establishing new mainline support.
