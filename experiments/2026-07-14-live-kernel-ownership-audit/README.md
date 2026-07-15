# Experiment: live vendor kernel ownership versus Linux 7.1.3

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-14-live-kernel-ownership-audit` |
| Status | `completed` for read-only config/ownership comparison; mainline runtime remains untested |
| Subsystem | vendor kernel configuration, module boundary, first-boot driver ownership |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant remains unestablished |
| Date | 2026-07-14 |

## Question

Does the current live vendor kernel actually use loadable modules, and which
vendor-built-in paths must be replaced by built-in or explicitly deferred Linux
7.1.3 paths before the first mainline boot?

## Method and safety

The audited inventory collector was run over SSH as root through `sudo -S` and
read only `/proc/config.gz`, `/proc/modules`, `dmesg`, and already-exposed kernel
state. The output is sanitized and retained privately under
`artifacts/device-inventory/20260714-live/`. No device node, bus, register,
driver binding, suspend state, reboot path, or partition was touched.

The analyzer compares that capture with the existing vendor configuration dump
and the guest-owned Linux 7.1.3 package. It does not execute vendor code and
does not infer probe success from a Kconfig value or a `System.map` symbol.

## Associated code

- [`scripts/analyze-live-kernel-ownership.py`](scripts/analyze-live-kernel-ownership.py)
- Private capture: `artifacts/device-inventory/20260714-live/kernel.txt`
- Private identity capture: `artifacts/device-inventory/20260714-live/identity.txt`
- Vendor config: `artifacts/device-inventory/20260712-live/vendor-kernel.config`
- Historical package: `linux-7.1.3-gemini-ca17601dcdeb`
- Current package: `linux-7.1.3-gemini-a9a7c5002038`

Run the comparison in the ARM64 VM:

```sh
./scripts/dev-vm run python3 \
  /mnt/gemini-pda-mainline/experiments/2026-07-14-live-kernel-ownership-audit/scripts/analyze-live-kernel-ownership.py \
  --capture /mnt/gemini-pda-mainline/artifacts/device-inventory/20260714-live/kernel.txt \
  --identity /mnt/gemini-pda-mainline/artifacts/device-inventory/20260714-live/identity.txt \
  --vendor-config /mnt/gemini-pda-mainline/artifacts/device-inventory/20260712-live/vendor-kernel.config \
  --mainline-config /home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-a9a7c5002038/kernel.config \
  --system-map /home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-a9a7c5002038/System.map \
  --build-json /home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-a9a7c5002038/provenance/build.json
```

## Analysis boundary

The vendor image has `CONFIG_MODULES` unset and exposes no `/proc/modules`
namespace, so every active vendor driver in this capture is a built-in path.
The Linux 7.1.3 package intentionally enables module infrastructure and now
contains optional modules, but those files are rootfs material only; they do
not imply that a device can probe or that the module was loaded.

The comparison therefore separates four cases:

1. a vendor built-in path replaced by a Linux built-in provider on the first
   boot (UART, watchdog, pinctrl, eMMC, and basic handoff infrastructure);
2. a vendor built-in path represented by an optional Linux module (display,
   audio, and thermal), which needs a rootfs and a later runtime gate;
3. a vendor built-in path with no compatible Linux transport (CONSYS/BTIF and
   CCCI/CLDMA), which needs a new backend and firmware ownership contract; and
4. a vendor feature intentionally absent from the first candidate, such as
   camera, DVFSP, and the multimedia consumer graph.

## Result

The fresh capture reproduces the older configuration inventory while adding a
stronger module conclusion: the vendor kernel is monolithic for its active
drivers. This explains why vendor config deltas cannot be treated as optional
module choices. Linux 7.1.3's current built-in dependency boundary remains
the conservative first-boot set; module packaging is useful for later rootfs
work but does not advance hardware support.
The reproducible analyzer output is recorded in
[`results/live-kernel-ownership-20260714.txt`](results/live-kernel-ownership-20260714.txt)
(SHA-256 `744f7be46b537343c10ec6010aa4bc3e85fc1e779e34fb97d665807b98c44f31`).

The same capture was rerun against the authoritative current 72-patch package.
The byte-identical result is recorded in
[`results/live-kernel-ownership-current-72-package-20260714.txt`](results/live-kernel-ownership-current-72-package-20260714.txt);
it preserves the vendor built-in/module boundary while updating the current
configuration, `System.map`, and package provenance hashes.

## Follow-up

- Use the result when deciding whether a new Gemini driver must be built-in for
  the first boot or can be deferred to the optional module tree.
- After a controlled non-primary boot, compare `/proc/modules`, probe logs, and
  `modalias`/sysfs ownership against this static boundary.
- Keep vendor-only transport and firmware paths out of the initial DT until a
  non-transmitting handshake and memory-ownership contract are recovered.
