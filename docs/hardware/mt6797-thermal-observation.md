# MT6797 thermal observation boundary

Scope: the named MT6797X Gemini PDA and its experimental mainline
`auxadc_thermal` path. These are source-backed interpretation constraints,
not proof of calibrated accuracy, sensor placement, thermal protection or
support on another Gemini variant. The
[thermal source/timing audit](../../experiments/2026-09-04-mt6797-a72-frequency-observation/THERMAL_AUDIT.md)
records exact source identity, method, captures and contradictions.

| Fact | Confidence and method | Interpretation boundary |
| --- | --- | --- |
| Reading the zone's sysfs temperature invokes the driver callback rather than returning only the background polling cache. | Confirmed in the integrity-verified production source. | A polling delay is not a sample-age guarantee; optional thermal emulation can override output if explicitly set. |
| The MT6797 zone reports a maximum across its configured bank/sensor readings. | Confirmed by the production callback and bank table. | It is not an identified A72 sensor temperature, and the winning sensor is not reported. |
| Bank selection uses the driver's shared lock and selector register. | Confirmed by the production callback. | A read-only userspace request still has normal internal bank-selection effects; independent raw-register probes could violate ownership. |
| V4 conversion quantizes output to 100 millicelsius. | Confirmed by the conversion arithmetic. | Repeated equal temperatures alone do not prove caching. |
| The callback reads measurement registers maintained by the thermal/AUXADC engine. | Confirmed by the production read path. | The current aggregate interface does not prove conversion age or provide an atomic cross-bank measurement. |

The cold and warm finite workload results differ in temperature response while
CPU, frequency and RAM results agree. Existing evidence does not distinguish
an actual cold transient from a changed hottest sensor or sampling effects.
No temperature threshold or safety limit is established by that comparison.
Calibration data remains private; accurate observation is separate from trips,
cooling, throttling and suspend support. Current runtime claims belong in the
[support matrix](../HARDWARE_SUPPORT.md), and ordered work in the
[roadmap](../ROADMAP.md).
