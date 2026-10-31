# Stock Android thermal policy: format and content

Source: `planet-community/android_device_planetcom_geminipda` branch
`cm-14.1`, `configs/.tp/` (installed to `/vendor/etc/.tp/`), and
`planet-community/android_vendor_planetcom_geminipda` branch `cm-14.1`
(`vendor/bin/thermal*`, `vendor/lib*/libmtcloader.so`,
`vendor/lib*/libthermalalgo.so`).

Method: static inspection of the public vendor libraries and files. Decoded
copies remain private; this document records the format and the policy facts.

## The files are obfuscated, not encrypted

`libmtcloader.so` contains a leaf function that rewrites each line in place:

```
plain = ((cipher + 59 - (column % 10)) % 91) + 0x20   /* 0x20 <= cipher <= 0x7a */
```

Column resets at every line feed, and bytes outside the printable range pass
through. That is a Caesar rotation over the 91 printable characters with a
period-10 column key — no key material, no authentication. The decoded files
end with the literal line `EOF`, matching the loader's own `strncmp` marker.

Reproduce with the [codec script](../scripts/mtk-tp-policy.py):

```sh
curl -O https://raw.githubusercontent.com/planet-community/android_device_planetcom_geminipda/cm-14.1/configs/.tp/thermal.conf
../scripts/mtk-tp-policy.py dec thermal.conf | less
```

## Decoded format

A flat sequence of two-line records, terminated by `EOF`:

```
/proc/driver/thermal/tz<zone>
<trip table>
/proc/mtkcooler/<cooler>
<parameters>
```

The daemon opens the named procfs file and writes the second line verbatim. The
zone trip table is `<n_trips>` followed by ten fixed
`<temperature_mdegC> <field> <cooler_name>` slots and one or two trailing
scalars. `n_trips` equals the number of non-`no-cooler` slots.

## Boot-default policy (`thermal.conf`)

| Zone | Trips (temperature → cooler) |
| --- | --- |
| CPU (`tzcpu`) | 110 °C → `mtktscpu-sysrst`; 58 °C → `cpu_adaptive_0`; 57 °C → `cpu_adaptive_1` |
| PMIC | 145 °C → `mtktspmic-sysrst` |
| Battery | 60 °C → `mtktsbattery-sysrst`; 48/47/46 °C → `mtk-cl-bcct02/01/00` |
| Board NTC + PA | 100 °C → `mtktspa-sysrst`; 57 °C → camera; 56 °C → LCD-off charge current; 50 °C → frame-rate cap; 47 °C → adaptive charge current |
| Modem/PA | 120 °C → shutdown; 110 °C → modem off; 100 °C → IMS off; 57 °C → adaptive modem throttle |
| WMT / PA / DRAM / DA9214 | 120 °C / 120 °C / 200 °C / 200 °C → reset coolers |
| Auxiliary sensors 1/2/4 | 150 °C → staged power-off |

Cooler parameters include adaptive CPU budget knobs (`clatm_setting`),
staged charge-current limits (`clbcct`, `clabcct`, `clabcct_lcmoff`), modem
throttling (`clmutt`), display frame-rate steps (`clfps_level`, 60/30/20/15),
and a CPU/GPU frequency-voltage table (`clctm`).

## Policy variants

| File | Distinguishing content |
| --- | --- |
| `thermal.conf` | Boot default; CPU 110/58/57 °C, adaptive knob 560 |
| `.thermal_policy_00` | Drops the frame-rate trip, charge throttling from 51-52 °C, knob 900 |
| `.thermal_policy_01` / `_02` | Byte-identical to each other; knob 1100 |
| `.thermal_policy_03` | Adds camera coolers at 100/90 °C on `tzcpu`; knob 2100 |
| `thermal.off.conf` | Only reset and shutdown coolers; `clctm` disabled; CPU 117/105/85 °C |
| `.ht120.mtc` | Minimal 117 °C CPU-only profile; no battery zone |

## Daemons

| Component | Role |
| --- | --- |
| `thermal_manager` | Root, one-shot: loads a `.tp` file through `libmtcloader.so` and writes the procfs nodes |
| `libmtcloader.so` | Codec, parser, procfs writer, policy selection |
| `thermalloadalgod` + `libthermalalgo.so` | Adaptive target-junction algorithm; netlink socket to the kernel driver |
| `thermald` | Registers PIDs and broadcasts Android notifications |
| `thermal` | Modem/WMT throttling side; local sockets, modem info |
| `thermalindicator` | On-screen throttling overlay |
| `thermal.mt6797.so` | Android thermal HAL; exposes `mtktscpu`, `mtktsAP`, `mtktsbattery` |

No temperature constant is compiled into any thermal daemon or HAL; the shipped
trip points come from the `.tp` data.

## Limits

- The second field of a trip tuple and the trailing scalars are not decoded;
  they are plausibly type/hysteresis and polling interval.
- Cooler parameter meanings (`clctm`, `clmutt`, `clatm_setting`) are inferred
  from magnitude, not from reversed kernel code.
- Which policy a given SKU selects at runtime, and whether `.ht120.mtc` is ever
  loaded, was not established.
- The sectioned `Sec`/`Sec_Chip_Name`/`Sec_End` variant in the loader is not
  used by any shipped file and was not reversed.
