#!/usr/bin/env python3
"""Derive AL's collector from exact AH while replacing only resource probes."""

from __future__ import annotations

import argparse
import os
import pathlib
import shlex
import stat
import sys

sys.dont_write_bytecode = True

import candidate_al as al


OLD_RESOURCE_BLOCK = r'''	i2c6_node=/sys/firmware/devicetree/base/i2c@1100e000
	[ ! -d "$i2c6_node" ] || printf 'i2c6_dt_node_present=1\n'
	[ -d "$i2c6_node" ] || printf 'i2c6_dt_node_present=0\n'
	printf 'i2c6_status_hex='; property_hex "$i2c6_node/status"; printf '\n'
	i2c6_platform_count=0
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		node=$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)
		[ "${node##*/}" != i2c@1100e000 ] || i2c6_platform_count=$((i2c6_platform_count + 1))
	done
	printf 'i2c6_platform_count=%s\n' "$i2c6_platform_count"
	da9214_dt_count=0
	for node in "$i2c6_node"/*; do
		[ -d "$node" ] || continue
		compatible=$(property_hex "$node/compatible")
		[ "$compatible" != 646c672c64613932313400 ] || da9214_dt_count=$((da9214_dt_count + 1))
	done
	printf 'da9214_dt_count=%s\n' "$da9214_dt_count"
	da9214_client_count=0
	for client in /sys/bus/i2c/devices/*-0068; do
		[ -d "$client" ] || continue
		da9214_client_count=$((da9214_client_count + 1))
	done
	printf 'da9214_client_count=%s\n' "$da9214_client_count"
	da9214_bucka_count=0
	vproc_big_count=0
	for name_path in /sys/class/regulator/regulator.*/name; do
		[ -f "$name_path" ] || continue
		name=$(/bin/busybox cat "$name_path")
		[ "$name" != da9214-bucka ] || da9214_bucka_count=$((da9214_bucka_count + 1))
		[ "$name" != vproc-big ] || vproc_big_count=$((vproc_big_count + 1))
	done
	printf 'da9214_bucka_count=%s\n' "$da9214_bucka_count"
	printf 'vproc_big_count=%s\n' "$vproc_big_count"
'''

NEW_RESOURCE_BLOCK = r'''	i2c6_node=/sys/firmware/devicetree/base/i2c@1100e000
	i2c6_pins=/sys/firmware/devicetree/base/pinctrl@10005000/i2c6-pins
	da9214_node=$i2c6_node/regulator@68
	regulators_node=$da9214_node/regulators
	i2c6_node_canonical=$(/bin/busybox readlink -f "$i2c6_node" 2>/dev/null || true)
	da9214_node_canonical=$(/bin/busybox readlink -f "$da9214_node" 2>/dev/null || true)
	[ ! -d "$i2c6_node" ] || printf 'i2c6_dt_node_present=1\n'
	[ -d "$i2c6_node" ] || printf 'i2c6_dt_node_present=0\n'
	printf 'i2c6_status_hex='; property_hex "$i2c6_node/status"; printf '\n'
	printf 'i2c6_clock_frequency_hex='; property_hex "$i2c6_node/clock-frequency"; printf '\n'
	[ ! -e "$i2c6_node/mediatek,use-push-pull" ] || printf 'i2c6_push_pull_present=1\n'
	[ -e "$i2c6_node/mediatek,use-push-pull" ] || printf 'i2c6_push_pull_present=0\n'
	printf 'i2c6_pinctrl_names_hex='; property_hex "$i2c6_node/pinctrl-names"; printf '\n'
	printf 'i2c6_pinctrl_0_hex='; property_hex "$i2c6_node/pinctrl-0"; printf '\n'
	printf 'i2c6_pins_phandle_hex='; property_hex "$i2c6_pins/phandle"; printf '\n'
	printf 'da9214_dt_compatible_hex='; property_hex "$da9214_node/compatible"; printf '\n'
	printf 'da9214_dt_reg_hex='; property_hex "$da9214_node/reg"; printf '\n'
	printf 'da9214_bucka_name_hex='; property_hex "$regulators_node/BUCKA/regulator-name"; printf '\n'
	printf 'da9214_buckb_name_hex='; property_hex "$regulators_node/BUCKB/regulator-name"; printf '\n'

	i2c6_platform_count=0
	i2c6_device=unavailable
	i2c6_driver=unavailable
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		node=$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)
		[ "${node##*/}" != i2c@1100e000 ] || {
			i2c6_platform_count=$((i2c6_platform_count + 1))
			i2c6_device=${device##*/}
			if [ -L "$device/driver" ]; then
				i2c6_driver=$(/bin/busybox basename "$(/bin/busybox readlink -f "$device/driver")")
			else
				i2c6_driver=unbound
			fi
		}
	done
	printf 'i2c6_platform_count=%s\n' "$i2c6_platform_count"
	printf 'i2c6_device=%s\n' "$i2c6_device"
	printf 'i2c6_driver=%s\n' "$i2c6_driver"

	i2c6_adapter_count=0
	i2c6_adapter=unavailable
	for adapter in /sys/bus/i2c/devices/i2c-*; do
		[ -d "$adapter" ] || continue
		adapter_node=$(/bin/busybox readlink -f "$adapter/of_node" 2>/dev/null || true)
		if [ -n "$i2c6_node_canonical" ] && [ "$adapter_node" = "$i2c6_node_canonical" ]; then
			i2c6_adapter_count=$((i2c6_adapter_count + 1))
			i2c6_adapter=${adapter##*/i2c-}
		fi
	done
	printf 'i2c6_adapter_count=%s\n' "$i2c6_adapter_count"
	printf 'i2c6_adapter=%s\n' "$i2c6_adapter"

	da9214_dt_count=0
	for node in "$i2c6_node"/*; do
		[ -d "$node" ] || continue
		compatible=$(property_hex "$node/compatible")
		[ "$compatible" != 646c672c64613932313400 ] || da9214_dt_count=$((da9214_dt_count + 1))
	done
	printf 'da9214_dt_count=%s\n' "$da9214_dt_count"
	da9214_client_total=0
	da9214_client_count=0
	da9214_device=unavailable
	da9214_driver=unavailable
	da9214_parent=unavailable
	for client in /sys/bus/i2c/devices/*-0068; do
		[ -d "$client" ] || continue
		da9214_client_total=$((da9214_client_total + 1))
		client_node=$(/bin/busybox readlink -f "$client/of_node" 2>/dev/null || true)
		if [ -n "$da9214_node_canonical" ] && [ "$client_node" = "$da9214_node_canonical" ]; then
			da9214_client_count=$((da9214_client_count + 1))
			da9214_device=${client##*/}
			da9214_parent=$(/bin/busybox basename "$(/bin/busybox dirname "$client_node")")
			if [ -L "$client/driver" ]; then
				da9214_driver=$(/bin/busybox basename "$(/bin/busybox readlink -f "$client/driver")")
			else
				da9214_driver=unbound
			fi
		fi
	done
	printf 'da9214_client_total=%s\n' "$da9214_client_total"
	printf 'da9214_client_count=%s\n' "$da9214_client_count"
	printf 'da9214_device=%s\n' "$da9214_device"
	printf 'da9214_driver=%s\n' "$da9214_driver"
	printf 'da9214_parent=%s\n' "$da9214_parent"

	da9214_bucka_count=0
	da9214_bucka_class=unavailable
	da9214_bucka_parent=unavailable
	da9214_bucka_state=unavailable
	da9214_bucka_microvolts=unavailable
	vproc_big_count=0
	vproc_big_class=unavailable
	vproc_big_parent=unavailable
	vproc_big_state=unavailable
	vproc_big_microvolts=unavailable
	for name_path in /sys/class/regulator/regulator.*/name; do
		[ -f "$name_path" ] || continue
		name=$(/bin/busybox cat "$name_path")
		regulator_device=${name_path%/name}
		parent=$(/bin/busybox readlink -f "$regulator_device/device" 2>/dev/null || true)
		parent=${parent##*/}
		if [ "$name" = da9214-bucka ]; then
			da9214_bucka_count=$((da9214_bucka_count + 1))
			da9214_bucka_class=${regulator_device##*/}
			da9214_bucka_parent=$parent
			da9214_bucka_state=$(/bin/busybox cat "$regulator_device/state" 2>/dev/null || printf unavailable)
			da9214_bucka_microvolts=$(/bin/busybox cat "$regulator_device/microvolts" 2>/dev/null || printf unavailable)
		fi
		if [ "$name" = vproc-big ]; then
			vproc_big_count=$((vproc_big_count + 1))
			vproc_big_class=${regulator_device##*/}
			vproc_big_parent=$parent
			vproc_big_state=$(/bin/busybox cat "$regulator_device/state" 2>/dev/null || printf unavailable)
			vproc_big_microvolts=$(/bin/busybox cat "$regulator_device/microvolts" 2>/dev/null || printf unavailable)
		fi
	done
	printf 'da9214_bucka_count=%s\n' "$da9214_bucka_count"
	printf 'da9214_bucka_class=%s\n' "$da9214_bucka_class"
	printf 'da9214_bucka_parent=%s\n' "$da9214_bucka_parent"
	printf 'da9214_bucka_state=%s\n' "$da9214_bucka_state"
	printf 'da9214_bucka_microvolts=%s\n' "$da9214_bucka_microvolts"
	printf 'vproc_big_count=%s\n' "$vproc_big_count"
	printf 'vproc_big_class=%s\n' "$vproc_big_class"
	printf 'vproc_big_parent=%s\n' "$vproc_big_parent"
	printf 'vproc_big_state=%s\n' "$vproc_big_state"
	printf 'vproc_big_microvolts=%s\n' "$vproc_big_microvolts"
'''

OLD_AW9523_CLIENT_BLOCK = r'''	aw9523_client_count=0
	aw9523_driver=unavailable
	for client in /sys/bus/i2c/devices/*-005b; do
		[ -d "$client" ] || continue
		aw9523_client_count=$((aw9523_client_count + 1))
		if [ -L "$client/driver" ]; then
			aw9523_driver=$(/bin/busybox basename "$(/bin/busybox readlink -f "$client/driver")")
		else
			aw9523_driver=unbound
		fi
	done
	printf 'aw9523_client_count=%s\n' "$aw9523_client_count"
	printf 'aw9523_driver=%s\n' "$aw9523_driver"
'''

NEW_AW9523_CLIENT_BLOCK = r'''	aw9523_client_count=0
	aw9523_device=unavailable
	aw9523_driver=unavailable
	for client in /sys/bus/i2c/devices/*-005b; do
		[ -d "$client" ] || continue
		aw9523_client_count=$((aw9523_client_count + 1))
		aw9523_device=${client##*/}
		if [ -L "$client/driver" ]; then
			aw9523_driver=$(/bin/busybox basename "$(/bin/busybox readlink -f "$client/driver")")
		else
			aw9523_driver=unbound
		fi
	done
	printf 'aw9523_client_count=%s\n' "$aw9523_client_count"
	printf 'aw9523_device=%s\n' "$aw9523_device"
	printf 'aw9523_driver=%s\n' "$aw9523_driver"
'''


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"AH collector token count changed: expected {count}, found {actual}"
        )
    return text.replace(old, new)


def derive(source: str, validator: pathlib.Path) -> str:
    al.require_artifact_pins()
    text = replace_exact(
        source,
        "readonly EXPECTED_INSTALLED_FULL_SHA256=" + al.AH_PADDED_SHA256,
        "readonly EXPECTED_INSTALLED_FULL_SHA256=" + al.PADDED_SHA256,
        1,
    )
    text = replace_exact(text, OLD_RESOURCE_BLOCK, NEW_RESOURCE_BLOCK, 1)
    text = replace_exact(
        text,
        OLD_AW9523_CLIENT_BLOCK,
        NEW_AW9523_CLIENT_BLOCK,
        1,
    )
    text = text.replace("Candidate AH", "Candidate AL")
    text = text.replace("candidate-ah", "candidate-al")
    text = text.replace("__AH_", "__AL_")
    old_script_dir = r'''script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"'''
    text = replace_exact(
        text,
        old_script_dir,
        "# shellcheck disable=SC2034\n" + old_script_dir,
        1,
    )
    old_host_end = "\tprintf '__AL_HOST_END__\\n'\n"
    new_host_end = (
        "\tprintf 'regulator_access_path=regulator-sysfs-driver-regmap-serialized\\n'\n"
        "\tprintf 'regulator_sysfs_may_be_regcache=yes\\n'\n"
        "\tprintf 'physical_readback_claim=none\\n'\n"
        + old_host_end
    )
    text = replace_exact(text, old_host_end, new_host_end, 1)
    old_validator = 'python3 "$script_dir/validate-runtime.py" --capture "$output"'
    new_validator = (
        f"python3 {shlex.quote(os.fspath(validator))} --capture \"$output\" "
        '--expected-installed-full-sha256 "$installed_full_sha256"'
    )
    text = replace_exact(text, old_validator, new_validator, 1)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=pathlib.Path)
    parser.add_argument("--validator", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        source = al.read_regular(args.source, "exact Candidate AH runtime collector")
        if al.digest_path(args.source) != al.AH_RUNTIME_COLLECTOR_SHA256:
            raise ValueError("source-pinned Candidate AH runtime collector changed")
        al.read_regular(args.validator, "Candidate AL runtime validator")
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite derived runtime collector")
        parent = args.output.parent.resolve(strict=True)
        if args.output.parent.is_symlink() or not stat.S_ISDIR(
            args.output.parent.lstat().st_mode
        ):
            raise ValueError("derived collector output parent is unsafe")
        output = parent / args.output.name
        text = derive(source.decode("utf-8", errors="strict"), args.validator.resolve())
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o700)
            stream.write(text)
        print("validation=candidate-al-runtime-collector-derived")
        print(f"output={output}")
        print(f"foundation_sha256={al.AH_RUNTIME_COLLECTOR_SHA256}")
        print("explicit_runtime_operations=read-only")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
