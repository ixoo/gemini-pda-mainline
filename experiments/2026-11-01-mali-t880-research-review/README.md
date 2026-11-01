# Experiment: Mali-T880 research cross-check

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mali-t880-research-review` |
| Status | Completed offline review; GPU runtime remains untested |
| Scope | Review of the October GPU research and offline bring-up recipe |
| Project input | `c20b93a9` |
| Device access | None |

## Inputs and method

Reviewed the [October 4 source investigation](../2026-10-04-gemini-gpu-re/README.md),
[October 31 preparation](../2026-10-31-mali-t880-offline-bringup/README.md),
their selected patches and the [hardware record](../../docs/hardware/mali-t880.md).
Used the retained public Gemian Git object at
`8cfe6596a503612e3332d9c26e292a19525a7f07` on Buildbox, the existing Linux
7.1.3 prepared source, and targeted AArch64 disassembly in the RE VM
(GNU Binutils for Ubuntu 2.42). No
source tree was copied, kernel built, candidate composed for deployment, or
device contacted.

The vendor source identities remain in the October 4
[input manifest](../2026-10-04-gemini-gpu-re/source-inputs.json).
The retained active vendor ELF SHA-256 is
`cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162`.
The Linux `panfrost_device.c` comparison input remains byte-identical to that manifest.
Additional inspected Linux source identities are:

| File | SHA-256 |
| --- | --- |
| `drivers/clk/mediatek/clk-mtk.h` | `67c603ab0a319e7672fba7f569a4e691fd8b3772b031427524d8da934198e6d9` |
| `drivers/clk/mediatek/clk-gate.c` | `f7ce5febabcda46321b658c8bc00d747d50c09f9b7642313227153c8dbceef8b` |
| `drivers/opp/of.c` | `eb5f2cef313366da0e3ca72c9e876d59ff5e8aa0ee782f71df791a71cce7e9ae` |
| `drivers/opp/core.c` | `7abb501d648d74e6d6313cdb3346c0ecb6e31b14202e818ae49d6421008e7014` |
| `drivers/regulator/helpers.c` | `860f6e07370505cf909331d120390a3f622056af8d1c197dac795b1f5f9fa981` |

Disassembly, extracts and other raw analysis stay outside tracked files. Only
independently described facts with public source support appear below.

## Findings

### 1. The core-driver reuse conclusion holds

The observed `0x0880` identity is covered by Panfrost's T880 model. The open
work remains MT6797 platform sequencing and resource ownership. The official
[Mesa Panfrost documentation](https://docs.mesa3d.org/drivers/panfrost.html),
checked on 2026-11-01, explicitly lists T880 with OpenGL ES 3.1 and OpenGL 3.1;
its Midgard row has no Vulkan support. This resolves the earlier record's
unverified recollection of Mesa model coverage. GPU rendering and native
display-controller integration remain distinct validation targets. This review
adds no mainline probe, rendering, power-cycle or thermal result.

### 2. The clock propagation gap was a macro-reading error

October 4 F11 read `MUX_GATE` and `GATE_MTK` as lacking rate propagation.
However, [`MUX_GATE`](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mtk.h#L139-L149)
supplies `CLK_SET_RATE_PARENT`, and
[`mtk_clk_register_gate()`](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-gate.c#L205-L225)
adds the same flag. No flag-only patch is needed for that path.

This does not prove a 520 MHz assignment succeeds, which parent CCF selects,
the inherited PLL state, or safe divider changes. Check the selected parent,
actual rate and PLL handling before treating the composed DT as a fixed point.
The vendor's divider-change parking requirement remains unresolved.

### 3. Async timing uses the maximum table frequency

[`mtk_platform_init()`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_config_platform.c#L679-L684)
reads table index zero and selects `async_value = 0xa` for a maximum of at
least 780 MHz, otherwise `0x5`. The power-on callback ORs this value into
G3D offset `0x1c`. Type 12 has a 900 MHz maximum, so it selects **`0xa` even
while operating at 520 MHz**. The previous instruction to use `0x5` merely
because bring-up targets 520 MHz was unsupported.

The active ELF independently confirms the index-zero call at
`0xffffffc0005d0820`, the comparison against 779999 and selection of 10/5 at
`0xffffffc0005d0838`–`0xffffffc0005d0858`, and the read/OR/write at
`0xffffffc0005cfe40`–`0xffffffc0005cfe50`. These are static instruction
observations; no live `MFG_ASYNC_CON` value was read.

### 4. Voltage requests and representable outputs differ

The vendor's 1.0006 V calibration request passes through
[`rt5735_set_voltage()`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/rt5735.c#L250-L275),
which truncates `(microvolts - 600000) / 6250`. It programs selector 64,
**1.0000 V nominal**. Targeted disassembly of the active ELF function at
`0xffffffc0004bbae0` confirms that conversion. This supports 1.0 V as the
matching nominal selector for the proposed calibration point; it is not a
measurement of physical voltage or proof of mainline safety.

The later example OPP table had a different problem: scalar
[`opp-microvolt`](https://github.com/gregkh/linux/blob/v7.1.3/drivers/opp/of.c#L679-L688)
sets target, minimum and maximum equal. The OPP core passes those limits to
the regulator; the
[`linear voltage mapper`](https://github.com/gregkh/linux/blob/v7.1.3/drivers/regulator/helpers.c#L388-L412)
rejects a rounded selector above the maximum. For example, 846700 µV requires
850000 µV, exceeding its exact limit. Six of the seven example scalar values
are unrepresentable; only 975000 µV is exact. The vendor's truncation cannot
be transferred to a mainline OPP table by saying "let the regulator round".
Supported selectors or explicit reviewed voltage ranges and a voltage ceiling
are required before any dynamic OPP recipe is usable.

### 5. A disabled GPU consumer does not isolate SCPSYS effects

The GPU profile enables legacy SCPSYS. Its
[`mtk_register_power_domains()`](https://github.com/gregkh/linux/blob/v7.1.3/drivers/pmdomain/mediatek/mtk-scpsys.c#L510-L551)
calls `power_on()` for every described domain before registering the provider;
unused domains are powered down late. The GPU series does not select the
display experiment's boot-state-adoption change. Therefore even the base DTB
with its GPU node disabled does **not** establish a GPU-power-inert boot.
Compile-only remains the profile's boundary.

This also invalidates the proposed LDO placement as an already settled
implementation: vendor LDO enable precedes VGPU and MFG_ASYNC, whereas an
MFG callback runs after its ASYNC parent and independently of Panfrost's
regulator init. An owner must cover provider probe, consumer probe, runtime PM,
failure rollback and shutdown before enabling the path.

### 6. Correct protection bits do not establish equivalent sequencing

The vendor power-on order is LDO → VGPU → VCG → ASYNC → MFG → cores → BG3D →
100 µs → release bits 21/23. On power-off it protects before disabling BG3D
and cores. The active ELF confirms the LDO write and VGPU call at
`0xffffffc0005cfd0c`/`0xffffffc0005cfd10`, then protection release at
`0xffffffc0005cfe34` after clock enables and the delay.

`gpu/0001` instead assigns the mask to MFG: generic SCPSYS releases protection
at the end of **MFG** power-on, before leaf core requests and the consumer's
BG3D enable; it asserts protection during MFG power-off, after its children
can already be off. Thus the mask is source-backed, but the October 4 H1
claim of matching the vendor order was incorrect. Whether the earlier release
and later assertion are safe is untested.

Panfrost probe requests domain links → deasserts the optional reset → enables
clocks → initializes OPP/regulator → initializes the GPU. With MT6797
`pm_features = 0`, runtime PM does not toggle TOPRGU; merely adding `resets`
does not reproduce the vendor's one-time assert/delay/deassert pulse. See
[`panfrost_device.c`](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panfrost/panfrost_device.c).

### 7. The offline validator is not a resource or runtime proof

The existing positive/negative fixture self-test passes. Independent mutations
of a composed fixture nevertheless each produce exit zero and
`PASS: GPU config and enabled DT contract`:

- Set `/i2c@11010000:status` to `disabled`.
- Set `/syscon@13000000:status` to `disabled`.
- Replace all four domain pairs with `<0xdeadbeef 0>`.
- Replace the core clock with `<0xdeadbeef 1>`, retaining the valid bus pair.

For example, after composing the supplied fixture:

```sh
fdtput -t s gpu-enabled.dtb /i2c@11010000 status disabled
python3 experiments/2026-10-31-mali-t880-offline-bringup/scripts/validate-gpu-config.py \
  --config gpu.config --dtb gpu-enabled.dtb --expect enabled
```

The validator checks selected properties but not provider availability, exact
domain references or the core clock reference. Fix those omissions before it
can gate a candidate. This review records the counterexamples; it does not
change the tooling or authorize deployment.

## Outcome and limits

Corrected the durable hardware recipe and linked the historical records to
this review. No driver, patch selection, manifest, runtime configuration or
support claim changed. The next work is sequencing design and offline
validation, ordered in the [roadmap](../../docs/ROADMAP.md), rather than a GPU
boot with the current composition.

Validation: public-source cross-check on Buildbox and official Mesa documentation;
targeted active-vendor ELF
disassembly in the RE VM; existing fixture self-test and the independent
validator counterexamples above. No kernel build, binding check, live register
read, Panfrost probe, rendering or device power transition was performed.
Repository checks passed using the installed Python 3.14; the Linux-only
package-provenance fixture was skipped on this host. Changed-file link and
sensitive-text checks and `git diff --check` passed.
