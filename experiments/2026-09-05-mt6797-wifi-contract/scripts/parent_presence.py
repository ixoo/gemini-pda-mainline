#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One bounded presence diagnosis; the caller pins both source files before use."""

import json
import os
import signal
import stat

import wifi_sysfs as core


MAX_SECONDS = 10
HELPER_PATH = "experiments/2026-09-05-mt6797-wifi-contract/scripts/wifi_sysfs.py"
HELPER_SHA256 = "c89820e47e499fd6bc5ebc39846125ab7e64fd38df12a17bdb4ddc58c8489d65"
WLAN = "/sys/class/net/wlan0"
PLATFORM = "/sys/bus/platform/devices/180f0000.wifi"
OF_PARTS = ("sys", "firmware", "devicetree", "base", "soc", "wifi@180f0000")
PATHS = (
    ("wlan", WLAN),
    ("device", WLAN + "/device"),
    ("subsystem", WLAN + "/device/subsystem"),
    ("driver", WLAN + "/device/driver"),
    ("of_node", WLAN + "/device/of_node"),
    ("compatible", WLAN + "/device/of_node/compatible"),
    ("clock_names", WLAN + "/device/of_node/clock-names"),
    ("platform_driver", PLATFORM + "/driver"),
)


def kind(mode):
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "regular"
    raise core.Refusal("special_path")


def metadata_kind(reader, path, resolve_final):
    if resolve_final:
        parts = reader.resolve(path)
    else:
        parent, name = path.rsplit("/", 1)
        parts = reader.resolve(parent) + (name,)
    fd = reader.directory(parts[:-1])
    try:
        reader.check_time()
        return kind(os.stat(parts[-1], dir_fd=fd, follow_symlinks=False).st_mode), parts
    except OSError as exc:
        raise reader.translate_error(exc) from None
    finally:
        os.close(fd)


def expected(label, parts):
    if label == "wlan":
        return parts[:2] == ("sys", "devices") and parts[-3:] == ("180f0000.wifi", "net", "wlan0")
    if label == "device":
        return parts[:2] == ("sys", "devices") and parts[-1:] == ("180f0000.wifi",)
    if label == "subsystem":
        return parts == ("sys", "bus", "platform")
    if label in ("driver", "platform_driver"):
        return parts == ("sys", "bus", "platform", "drivers", "mt-wifi")
    if label == "of_node":
        return parts == OF_PARTS
    if label == "compatible":
        return parts == OF_PARTS + ("compatible",)
    return parts == OF_PARTS + ("clock-names",)


def inspect_path(reader, label, path):
    record = {"entry_kind": "unavailable", "target_kind": "unavailable",
              "resolved_relation": "unavailable"}
    try:
        record["entry_kind"], _ = metadata_kind(reader, path, False)
        record["target_kind"], parts = metadata_kind(reader, path, True)
        record["resolved_relation"] = "expected" if expected(label, parts) else "other"
        wanted = "regular" if label in ("compatible", "clock_names") else "directory"
        if record["target_kind"] != wanted:
            record["resolved_relation"] = "other"
    except core.Inconclusive:
        # A missing component and a permission failure are both unavailable;
        # this diagnostic does not turn an unresolved path into physical absence.
        pass
    return record


def provenance():
    return {"helper_path": HELPER_PATH, "helper_sha256": HELPER_SHA256,
            "verification": "caller_must_pin_loaded_source_bytes"}


def collect(reader, kernel, boot):
    result = {"schema": 1, "mode": "fixture" if reader.fixture else "live",
              "provenance": provenance(), "radio_operations": 0,
              "property_payload_reads": 0, "identity_checked_end": False}
    try:
        result["identity"] = core.check_identity(reader, kernel, boot)
        records = {}
        for label, path in PATHS:
            records[label] = inspect_path(reader, label, path)
        result["paths"] = records
        result["status"] = "observed" if all(
            record["resolved_relation"] == "expected" for record in records.values()
        ) else "inconclusive"
    except core.ObservationError as exc:
        result.update(status="refused", reason=str(exc))
    if "identity" in result:
        try:
            core.check_identity(reader, kernel, boot)
            reader.check_time()
            result["identity_checked_end"] = True
        except core.ObservationError as exc:
            result.update(status="refused", reason=str(exc))
    result["budget"] = {"identity_bytes_read": reader.bytes_read,
                        "fixed_paths": len(PATHS), "max_seconds": MAX_SECONDS,
                        "symlink_depth_per_resolution": 16,
                        "components_per_resolution": 96}
    return result


def main(argv=None):
    reader = None
    alarm_set = False
    try:
        parser = core.JsonParser(description=__doc__)
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--collect", action="store_true")
        mode.add_argument("--fixture-root")
        parser.add_argument("--expected-kernel")
        parser.add_argument("--expected-boot-id")
        args = parser.parse_args(argv)
        if not args.collect and args.fixture_root is None:
            result = {"schema": 1, "mode": "dry-run", "status": "not-collected",
                      "provenance": provenance(), "fixed_paths": len(PATHS),
                      "radio_operations": 0, "property_payload_reads": 0,
                      "max_seconds": MAX_SECONDS}
        else:
            if (not args.expected_kernel or not core.KERNEL.fullmatch(args.expected_kernel) or
                    not args.expected_boot_id or not core.UUID.fullmatch(args.expected_boot_id)):
                raise core.Refusal("expected_identity_required")
            signal.signal(signal.SIGALRM, core.alarm_handler)
            signal.setitimer(signal.ITIMER_REAL, MAX_SECONDS)
            alarm_set = True
            reader = core.Reader(args.fixture_root if args.fixture_root is not None else "/",
                                 fixture=args.fixture_root is not None, seconds=MAX_SECONDS)
            result = collect(reader, args.expected_kernel, args.expected_boot_id)
    except core.Refusal as exc:
        result = {"schema": 1, "status": "refused", "reason": str(exc)}
    except (OSError, RuntimeError):
        result = {"schema": 1, "status": "refused", "reason": "environment_unavailable"}
    finally:
        if alarm_set:
            signal.setitimer(signal.ITIMER_REAL, 0)
        if reader is not None:
            reader.close()
    print(json.dumps(result, sort_keys=True))
    return {"not-collected": 0, "observed": 0, "inconclusive": 2, "refused": 3}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
