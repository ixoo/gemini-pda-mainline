# MT6797 DRM component boundary for Linux 7.1.3

## Result

The Gemini primary display is best modeled by reusing Linux's existing
MediaTek DRM component generations where the register windows match, with
dedicated MT6797 platform data and one native MIPI-TX PHY implementation where
the fields differ. A wholly new DRM architecture is not needed, but blindly
reusing the nearest SoC data is unsafe.

The current series keeps every multimedia and DSI consumer disabled. These
results establish a source/register contract, not display support on hardware.

## Reproducible provenance

- Vendor source: Gemian MT6797 kernel commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Planet board source: commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Linux source: prepared and patched Linux `7.1.3` tree in the development VM.
- Source analyzer:

  ```sh
  ./experiments/2026-07-12-mt6797-drm-component-recovery/scripts/analyze-mt6797-drm-contract.sh
  ```

The analyzer records vendor Git blob IDs, Linux SHA-256 values, bounded source
anchors, and runs the existing fixed-function and DSI/PHY mechanical checks.
It does not read display MMIO, change clocks, or send panel commands.

## Recovered primary path

The retained vendor path resolves to:

```text
OVL0 -> OVL0-2L -> OVL1-2L -> COLOR0 -> CCORR -> AAL -> GAMMA ->
OD -> DITHER -> RDMA0 -> UFOE -> DSI0
```

The vendor route table also contains `OVL0_VIRTUAL`, `PATH0`, and `PWM0`.
Those are routing/backlight abstractions rather than additional pixel engines;
the Linux DRM master represents the 12 actual display components. The live
UFOE value `0x4` selects bypass, and the vendor primary path is video-mode,
four-lane DSI.

## Component reuse and differences

### OVL, OVL-2L, and RDMA

OVL register offsets and layer stride match the Linux MT8173 generation. MT6797
needs the MT8167-style `LAYER_SMI_ID_EN` data-path bit, a four-layer OVL0
record, and two-layer records for the two OVL-2L blocks. The retained format
word `0x010020ff` is the DRM ABGR8888 encoding (byte swap and alpha enabled).

RDMA0 also matches the MT8173 register generation and uses the memory address
at `0xf00`. The live FIFO field proves an 8 KiB FIFO; threshold tuning remains
performance policy. The retained source snapshot does not contain a complete
MT6797 RDMA implementation, so the live register capture and common Linux
driver behavior are the authoritative evidence for this boundary.

### COLOR, CCORR, AAL, GAMMA, OD, DITHER, and UFOE

- COLOR uses the MT8173 `0xc00` start/size window.
- CCORR coefficients are 12-bit fields. Linux's `matrix_bits = 10` is the
  correct 2.10 representation. Keep relay enabled without a DRM CTM; program
  coefficients before selecting the engine when a CTM is supplied.
- AAL has no MT6797 output-size register at `0x4d8`. The MT6797 data must skip
  that write, advertise no integrated gamma, and start in relay.
- GAMMA has one 2 KiB LUT window at `0x700`--`0xeff`: 512 entries, three
  10-bit channels. Start in relay until a LUT is installed.
- OD has internal dither fields, but Gemini uses the separate DITHER block.
  Keep OD in relay and do not enable its internal dither.
- DITHER uses the common engine-enable behavior, and UFOE's bypass bit is
  exact-match evidence rather than a generic default for every board.

The retained proprietary PQ state (`AAL_CFG=0x16`) is not a safe Linux default.
The first mainline light should use explicit relay behavior and only add PQ
programming after its ownership and color-management semantics are recovered.

### DSI host and MIPI-TX PHY

DSI0 is an MT8173-generation host with command-queue registers at `0x200` and
VM-command registers at `0x130`/`0x134`; the common Linux DSI host can be
reused with MT6797 data. The MIPI-TX aperture is not operation-compatible with
MT8173: MT6797 places pre-divider in bits 3:2, post-divider in 6:4, and S2Q in
13:12, with distinct bandgap selectors. The retained sequence preserves lane
trim and voltage selectors, supports divider ratios 1/2/4/8/16 from 50 MHz to
1.25 GHz, and pulses the PCW-change latch.

Therefore the PHY needs native MT6797 clock operations inside the common
MediaTek PHY framework. Reusing MT8173 masks would write the right offsets with
the wrong fields.

## Linux 7.1.3 boundary

The local patches add dedicated compatible/data records, not new display
algorithms. The shared DRM component, color-management, DSI, and PHY cores
remain the implementation base. MT6797-specific data/guards cover:

1. OVL/OVL-2L layer counts, format table, FIFO and SMI-ID behavior;
2. fixed-function register windows and relay/feature capabilities;
3. the 12-component primary master path and its exact M4U ports;
4. DSI command/VM offsets and the native MIPI-TX PLL fields;
5. disabled-first DT resources, power domains, clocks, resets, and graph ports.

The panel framework is a separate contract: exact panel suffix, command
sequence, reset, bias, and backlight must be proven together before enabling a
DRM connector. No generic panel or retained PQ ioctl behavior is inferred from
the component match alone.

## Bring-up gates

Before enabling any display consumer, verify:

- MM power-domain and clock sequencing, including the M4U/SMI fabric;
- the component's interrupt, reset, GCE event/subsystem, and exact M4U port;
- a minimal RDMA0-to-DSI0 transaction with a recovery path;
- panel bias/reset/backlight electrical behavior and DSI lane calibration;
- repeated screen-on/off and suspend/wake cycles without relying on vendor
  framebuffer ioctls.

Keep writeback, DSI1, secure display threads, camera, and vendor PQ controls
out of first light. Compile/schema success remains necessary but is not proof
of hardware support.

