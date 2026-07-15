# Experiment: Gemini external-display bridge identity and mainline boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-external-display-recovery` |
| Status | `inconclusive` for populated hardware; read-only binding/source audit completed |
| Subsystem | SII9022 HDMI/MHL bridge, EDID, vendor HDMI path |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date(s) | 2026-07-13 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Are the SII9022 and EDID nodes in the running Gemian device populated and
usable, and can Linux 7.1.3's existing bridge/DRM support be reused without
copying the vendor HDMI ABI?

## Provenance and safety

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live collector: [`collect-live-external-display.sh`](scripts/collect-live-external-display.sh).
- Private raw capture: `artifacts/device-inventory/20260713-live/external-display.txt`
  (Git-ignored and access-restricted).
- Vendor source: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: Linux `7.1.3` in the development VM.

The live procedure is read-only. It reads I2C/platform sysfs metadata, device
node names, interrupt counters, and filtered kernel messages. It does not open
`/dev/hdmitx`, issue bridge ioctls, read or write I2C registers, toggle GPIOs,
change clocks or regulators, or enable a display path.

## Procedure

From the repository root:

```sh
mkdir -p artifacts/device-inventory/20260713-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-13-external-display-recovery/scripts/collect-live-external-display.sh \
  > artifacts/device-inventory/20260713-live/external-display.txt
chmod 700 artifacts/device-inventory/20260713-live
chmod 600 artifacts/device-inventory/20260713-live/external-display.txt
```

The source-only comparison runs in the VM:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-13-external-display-recovery/scripts/analyze-external-display-contract.sh
```

The immutable vendor ELF/source audit runs in the VM and does not execute the
image:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-13-external-display-recovery/scripts/analyze-sil9022-vendor-elf.sh
```

## Observations

- I2C bus 3 has `3-0039`, named `sii9022_hdmi`, compatible
  `mediatek,sii9022_hdmi`, and `driver=unbound`.
- I2C bus 3 has `3-0050`, named `siiedid`, compatible `mediatek,siiedid`, and
  `driver=unbound`.
- Platform names `soc:sii9022`, `soc:sii9022_hdmi`, and `soc:mhl@0` exist, and
  a root-owned `/dev/hdmitx` node exists. These prove vendor software
  declarations, not a working bridge or connected display.
- The live interrupt table contains `EINT_HDMI_HPD-eint` with zero observed
  handlers in the capture. Filtered kernel messages contain no SII9022, HDMI,
  MHL, or EDID probe/attach line.
- No I2C register read, HPD transition, EDID transaction, or external-display
  mode-setting test was attempted.
- A bounded live ID-probe availability check was retried on 2026-07-13. SSH
  transport worked, but the device has no `/dev/i2c-*` character device,
  `/sys/class/i2c-dev`, `i2c-tools`, or Python SMBus module. Passwordless sudo
  was unavailable for installing or exposing an access path. No register read
  was attempted; the negative result is recorded in
  [`live-id-probe-attempt.txt`](results/live-id-probe-attempt.txt). Installing
  `i2c-tools` alone would not create a missing kernel I2C device, and the
  private `/dev/hdmitx` ABI is not a substitute for a chip-ID transaction.

The bounded ELF audit confirms symbols for `sil9022_i2c_probe`, `HDMI_reset`,
`HDMI_I2C_READ/WRITE`, and EDID helpers. The vendor probe accepts only the two
client names `sii9022_hdmi` and `siiedid`, enables GPIO247's 1.2 V state before
the 20/50/20 ms reset sequence, and registers the GPIO62/EINT1 HPD line. Its
TPI startup writes `0` to `0xc7`, then checks indexed ID `0x9022` and byte
`0xb0` at register `0x1b`; this is the same silicon/protocol family as Linux's
`sii902x` driver. The vendor source reads EDID through a separate `0x50`
client, but its segment pointer `siiSegEDID` is declared without an assignment
in the pinned source; that vendor bug/omission must not be carried forward.
Linux uses a standard DDC I2C mux/DRM EDID path.

The vendor DTS includes `sil9024a.dtsi`, despite naming its wrapper nodes
`sii9022`. That include requests reset GPIO57, HPD/EINT GPIO62, a 1.2 V enable
GPIO247, DPI GPIO39–54, and an `mhl_12v` supply. The pinned vendor tree also
contains the matching implementation under `drivers/misc/mediatek/hdmi/sil9024/`;
its source and compiled ELF are immutable evidence, not code to copy. Static
analysis recovered the same `0xb0` register identity used by Linux `sii902x`, a
vendor indexed `0x9022` family ID, the reset/1.2 V/pinctrl sequence, and a
separate EDID client. Hashes and bounded disassembly are recorded in
[`sil9022-vendor-elf-validation.txt`](results/sil9022-vendor-elf-validation.txt)
and the source comparison in
[`mainline-external-display-source-validation.txt`](results/mainline-external-display-source-validation.txt).

## Analysis

The candidate bridge and EDID clients are unbound, so the current capture does
not establish that an SII9022 is fitted or that a physical external connector
is wired. The `/dev/hdmitx` character node belongs to the vendor HDMI ABI and
must not be treated as a mainline DRM bridge probe. The static identity match
supports reusing Linux's chip driver; it does not prove that the board's
reference-tree nodes are populated.

Linux 7.1.3 already contains the `sii902x` bridge and binding. Its identity
check (`0xb0` at register `0x1b`) and byte-data register protocol agree with
the vendor source/ELF, so a new chip driver is not indicated by the recovered
evidence. Reuse is conditional: the vendor path still needs a board-specific
reset/power adaptation (GPIO57 reset, GPIO247 1.2 V enable, and an explicit
I/O supply), a 16-bit DPI input graph, HPD wiring, and standard DRM/EDID
integration. The vendor `mediatek,sii9022_hdmi` compatible, SII9024A-named
include, separate `siiedid` client, and private `/dev/hdmitx` ABI cannot be
selected by compatible-string substitution. Existing Gemini DRM work describes
only the internal DSI panel and does not establish an external-output route.

## DPI producer source comparison

The external bridge cannot be treated as a standalone I2C problem: it needs a
parallel DPI producer. The vendor tree describes DPI0 at `0x1401e000` with
SPI231 and uses the same register sequence represented by Linux's generic
`mtk_dpi` driver (enable/reset, timing generator, output setting, size,
status, checksum, and `0xf00` test-pattern register). Vendor power-on enables
`DISP1_DPI_MM_CLOCK` and `DISP1_DPI_INTERFACE_CLOCK`; its pixel-clock path
selects `TVDPLL_D2/D4/D8/D16` and writes the TVDPLL registers at APMIXED
offsets `0x270`/`0x274`.

Linux 7.1.3 already exposes the matching MT6797 top-clock TVDPLL/factor
outputs, MM DPI/interface gates, and MMSYS routes to `DPI0`. The new
MT6797-specific platform data therefore reuses `mtk_dpi` with an inferred
factor table, leaves horizontal-frequency/edge-selection features off, and
adds only a disabled node with unconnected graph ports. It does not add a
bridge node, pinctrl, rail, HPD, audio path, or enabled DRM route. The exact
source hashes and assumptions are in
[`mainline-mt6797-dpi-source-validation.txt`](results/mainline-mt6797-dpi-source-validation.txt).

## Conclusion

`inconclusive` for physical population and external-display functionality.
The strongest current result is negative: the SII9022 and EDID I2C clients are
unbound and no runtime bridge activity was observed. Keep the external-display
row unknown and do not add an enabled board node or vendor HDMI ioctl adapter.

## Follow-up

- Inspect the physical board/connector and identify whether the candidate is a
  true SII9022/9024A-family part or unused reference-tree scaffolding.
- If physically present, recover bridge ID and EDID with a source-audited,
  bounded read-only transaction after explicitly documenting rails and reset;
  do not use generic `i2cdetect`.
- Before that transaction, provide a read-only I2C character-device path (or a
  narrowly scoped debug build) and record how it is removed; do not infer chip
  population from the unbound client names alone.
- Reconcile the recovered 16-bit DPI/HPD/audio graph with Linux's `sii902x`
  binding, then add only disabled DT data until a controlled external-monitor
  test exists.
- Validate the MT6797 DPI factor/PLL contract and graph on hardware before
  enabling `dpi0`; the current factor table is source-derived but not a
  runtime proof.
