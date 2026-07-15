#!/usr/bin/env bash

# Summarize the captured Gemini sensor HAL without executing it.
# Run in the development VM; the input is an AArch64 ELF from artifacts/.

set -u
export LC_ALL=C

binary=${1:?usage: $0 PATH_TO_SENSORS_HAL}
[[ -r "$binary" ]] || {
	printf 'not readable: %s\n' "$binary" >&2
	exit 1
}

printf 'binary=%s\n' "$binary"
file "$binary"
sha256sum "$binary"
readelf -h "$binary" | grep -E 'Class:|Machine:|Type:|Entry point'
printf '\n===== physical and virtual sensor symbols =====\n'
nm -D -C "$binary" 2>/dev/null | grep -Ei \
	'(SensorBase|Hwmsen|AccelerationSensor|GyroscopeSensor|MagneticSensor|AmbiLightSensor|ProximitySensor|PressureSensor|HumiditySensor|FindDataFd|readSensorData|ioctl)' | \
	head -n 320 || true
printf '\n===== legacy device and control paths =====\n'
strings -a "$binary" | grep -Ei \
	'(/dev/hwmsensor|/dev/input/event|/sys/class/misc/(m_|hwmsensor)|devnum|active|delay|batch|flush|enable|m_alsps_input|m_acc_input|m_gyro_input)' | \
	head -n 260 || true

if command -v objdump >/dev/null 2>&1; then
	printf '\n===== selected AArch64 event decoder disassembly =====\n'
	printf '%s\n' 'The offsets are symbol-relative ELF virtual addresses from the stripped-but-symbol-preserving HAL.'
	objdump -d -C --start-address=0x10498 --stop-address=0x10658 "$binary" 2>/dev/null || true
	objdump -d -C --start-address=0x10658 --stop-address=0x10774 "$binary" 2>/dev/null || true
	objdump -d -C --start-address=0x11fb8 --stop-address=0x1214c "$binary" 2>/dev/null || true
	objdump -d -C --start-address=0x1214c --stop-address=0x12268 "$binary" 2>/dev/null || true
fi
