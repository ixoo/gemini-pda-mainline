# MT6797 thermal serviceability design

## Source changes

The reusable SoC node gains the one source-proven reset input but stays
disabled:

```dts
resets = <&infrasys MT6797_INFRA_THERM_CTRL_RST>;
status = "disabled";
```

The driver requests the sole reset without a name, and the binding exposes no
`reset-names` property, so none is added.

A dedicated Gemini DT includes the base board and changes only experiment
policy:

```dts
/ {
	thermal-zones {
		soc-thermal {
			polling-delay-passive = <0>;
			polling-delay = <1000>;
			thermal-sensors = <&thermal>;
		};
	};
};

&thermal {
	status = "okay";
};
```

It deliberately contains no trip, cooling map, cpufreq, OPP, idle, suspend,
IRQ, watchdog, or CPU node change. The inherited standalone AUXADC platform
node remains disabled because the thermal controller directly owns the mapped
AUXADC registers and clock during its ordered transaction.

## Runtime attribution

Thermal-zone registration occurs only after calibration retrieval, exclusive
reset acquisition, both clock acquisitions, reset, APMIXED configuration,
global-idle checks, all six bank preparations, the single AUXADC channel
commit, all bank releases, and a valid first sample from every bank. Therefore
one bound thermal driver plus one readable, plausible zone is attributable
evidence that these preceding gates completed. Runtime DT evidence separately
proves the exact reset input and consumer isolation.

The profile must also link the existing DVFSP validation helpers referenced by
the thermal object's EEM support. That previously tested owner is an explicit
binary dependency, not a new CPU or frequency action; every downstream CPU,
cpufreq, OPP, I2C6, and admission action remains disabled for this boot.
