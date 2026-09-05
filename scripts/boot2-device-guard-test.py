#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the actual guard with injected Linux metadata; never access hardware."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


GUARD = Path(__file__).resolve().with_name("boot2-device-guard.sh")
ROOT = "36 1 179:29 / / rw,relatime - ext4 /dev/root rw\n"
PROC = "37 36 0:5 / /proc rw - proc proc rw\n"
SWAP_HEADER = "Filename Type Size Used Priority\n"
MOCKS = r'''
stat() {
    local path=${@: -1}
    case "$path" in
    /dev/mmcblk0p31|/dev/disk/by-partlabel/boot2|/dev/disk/by-uuid/target)
        if [[ -e "$FIXTURE/stat-second" && -e "$FIXTURE/target-stat-later" ]]; then
            command cat "$FIXTURE/target-stat-later"
        else
            if [[ -e "$FIXTURE/stat-first" ]]; then : >"$FIXTURE/stat-second"; fi
            : >"$FIXTURE/stat-first"
            command cat "$FIXTURE/target-stat"
        fi ;;
    /dev/mmcblk0) printf 'block special file|b3:0\n' ;;
    /dev/mmcblk0p29) command cat "$FIXTURE/root-stat" ;;
    /dev/mmcblk0p30) printf 'block special file|b3:1e\n' ;;
    *) return 1 ;;
    esac
}
readlink() {
    local path=${@: -1}
    case "$path" in
    /proc/self/ns/mnt) printf 'mnt:[4026531840]\n' ;;
    /proc/1/ns/mnt) command cat "$FIXTURE/namespace" ;;
    /sys/dev/block/179:31|/sys/class/block/mmcblk0p31)
        command cat "$FIXTURE/target-sys-path" ;;
    /sys/dev/block/179:29|/sys/class/block/mmcblk0p29)
        command cat "$FIXTURE/root-sys-path" ;;
    /sys/dev/block/179:30|/sys/class/block/mmcblk0p30)
        printf '/sys/devices/platform/mmc/block/mmcblk0/mmcblk0p30\n' ;;
    /sys/dev/block/179:0|/sys/class/block/mmcblk0)
        printf '/sys/devices/platform/mmc/block/mmcblk0\n' ;;
    *) return 1 ;;
    esac
}
cat() {
    local path=${@: -1}
    case "$path" in
    /proc/self/mountinfo)
        if [[ -e "$FIXTURE/mount-read" && -e "$FIXTURE/mountinfo-later" ]]; then
            command cat "$FIXTURE/mountinfo-later"
        else
            : >"$FIXTURE/mount-read"
            command cat "$FIXTURE/mountinfo"
        fi ;;
    /proc/swaps)
        if [[ -e "$FIXTURE/swaps-read" && -e "$FIXTURE/swaps-later" ]]; then
            command cat "$FIXTURE/swaps-later"
        else
            : >"$FIXTURE/swaps-read"
            command cat "$FIXTURE/swaps"
        fi ;;
    /sys/devices/platform/mmc/block/mmcblk0/mmcblk0p31/partition)
        command cat "$FIXTURE/partition" ;;
    /sys/devices/platform/mmc/block/mmcblk0/dev)
        printf '179:0\n' ;;
    /sys/devices/platform/mmc/block/mmcblk0/mmcblk0p31/dev)
        command cat "$FIXTURE/target-dev" ;;
    /sys/devices/platform/mmc/block/mmcblk0/mmcblk0p29/dev)
        printf '179:29\n' ;;
    /sys/devices/platform/mmc/block/mmcblk0/mmcblk0p30/dev)
        printf '179:30\n' ;;
    *) return 1 ;;
    esac
}
find() {
    if [[ "$1" == /sys/dev/block/179:0/holders ]]; then
        command cat "$FIXTURE/parent-holders"
        return
    fi
    [[ "$1" == /sys/dev/block/179:31/holders ]] || return 1
    [[ ! -e "$FIXTURE/holders-error" ]] || return 1
    command cat "$FIXTURE/holders"
}
# Exercise callers that test the function status, where Bash disables errexit.
if output=$(boot2_device_guard "$@" 2>&1); then
    printf '%s\n' "$output"
else
    printf '%s\n' "$output" >&2
    exit 1
fi
'''


class GuardTests(unittest.TestCase):
    def run_guard(self, changes=None, target="/dev/mmcblk0p31", expected="179:31",
                  expected_root=None):
        defaults = {
            "target-stat": "block special file|b3:1f\n",
            "root-stat": "block special file|b3:1d\n",
            "target-sys-path": "/sys/devices/platform/mmc/block/mmcblk0/mmcblk0p31\n",
            "root-sys-path": "/sys/devices/platform/mmc/block/mmcblk0/mmcblk0p29\n",
            "target-dev": "179:31\n",
            "partition": "31\n",
            "mountinfo": ROOT + PROC,
            "namespace": "mnt:[4026531840]\n",
            "swaps": SWAP_HEADER,
            "holders": "",
            "parent-holders": "",
        }
        defaults.update(changes or {})
        # Explicit managed temporary root; TemporaryDirectory cleans on failures.
        with tempfile.TemporaryDirectory(prefix="gemini-boot2-guard-", dir="/tmp") as temporary:
            fixture = Path(temporary)
            for name, value in defaults.items():
                if value is not None:
                    (fixture / name).write_text(value)
            program = 'set -eu\nsource "$1"\nshift\n' + MOCKS
            args = ["bash", "-c", program, "fixture", str(GUARD), target, expected]
            if expected_root is not None:
                args.append(expected_root)
            return subprocess.run(args, env={**os.environ, "FIXTURE": temporary},
                                  text=True, capture_output=True, timeout=10, check=False)

    def accepted(self, **kwargs):
        result = self.run_guard(**kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("boot2_device_guard=passed", result.stdout)
        self.assertIn("root_major_minor=179:29", result.stdout)
        self.assertIn("root_device=/dev/mmcblk0p29", result.stdout)

    def rejected(self, **kwargs):
        result = self.run_guard(**kwargs)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("boot2_device_guard=passed", result.stdout)

    def test_inactive_target_with_root_alias(self):
        self.accepted()

    def test_root_source_aliases_do_not_define_ownership(self):
        for source in ("/dev/disk/by-uuid/root", "/dev/mmcblk0p29", "rootfs"):
            with self.subTest(source=source):
                self.accepted(changes={"mountinfo": ROOT.replace("/dev/root", source) + PROC})

    def test_target_alias_is_verified_numerically(self):
        self.accepted(target="/dev/disk/by-partlabel/boot2")

    def test_mounted_target_via_alias_bind_and_hidden_mount(self):
        for source, root, mount in (("/dev/root", "/", "/mnt"),
                                    ("/dev/disk/by-uuid/target", "/", "/media/card"),
                                    ("none", "/subdir", "/bind"),
                                    ("/dev/unrelated", "/", "/hidden\\040mount")):
            with self.subTest(source=source):
                row = f"38 36 179:31 {root} {mount} rw - ext4 {source} rw\n"
                self.rejected(changes={"mountinfo": ROOT + PROC + row})

    def test_target_is_actual_root_despite_source_text(self):
        self.rejected(changes={"mountinfo": ROOT.replace("179:29", "179:31") + PROC})

    def test_mapped_root_has_target_holder(self):
        self.rejected(changes={"holders": "/sys/dev/block/179:31/holders/dm-0\n"})

    def test_whole_disk_mount_holder_or_swap_refuses(self):
        self.rejected(changes={"mountinfo": ROOT.replace("179:29", "179:0") + PROC})
        self.rejected(changes={"mountinfo": ROOT + PROC +
                               "38 36 179:0 / /disk rw - ext4 /dev/mmcblk0 rw\n"})
        self.rejected(changes={"parent-holders": "/sys/dev/block/179:0/holders/dm-0\n"})
        self.rejected(changes={"swaps": SWAP_HEADER + "/dev/mmcblk0 partition 100 0 -2\n"})

    def test_missing_holder_inspection_refuses(self):
        self.rejected(changes={"holders-error": "1"})

    def test_swap_alias_matches_device_number(self):
        for name in ("/dev/mmcblk0p31", "/dev/disk/by-uuid/target"):
            with self.subTest(name=name):
                self.rejected(changes={"swaps": SWAP_HEADER + f"{name} partition 100 0 -2\n"})

    def test_other_known_swap_device_is_allowed(self):
        self.accepted(changes={"swaps": SWAP_HEADER + "/dev/mmcblk0p30 partition 100 0 -2\n"})

    def test_unknown_swap_identity_refuses(self):
        for row in ("/swapfile file 100 0 -2\n", "/dev/missing partition 100 0 -2\n",
                    "/dev/mmcblk0p30 partition bad 0 -2\n", "garbage\n"):
            with self.subTest(row=row):
                self.rejected(changes={"swaps": SWAP_HEADER + row})

    def test_missing_or_malformed_observations_refuse(self):
        changes = (
            {"mountinfo": None}, {"mountinfo": ""}, {"mountinfo": PROC},
            {"mountinfo": ROOT + ROOT},
            {"mountinfo": ROOT + "38 36 179:31 / /mnt rw -\n"},
            {"mountinfo": ROOT.replace("179:29", "0:29") + PROC},
            {"mountinfo": ROOT.replace("179:29", "0179:29") + PROC},
            {"mountinfo": ROOT.replace(" - ext4", " ext4") + PROC},
            {"mountinfo": ROOT.replace("36 1", "not-id 1") + PROC},
            {"mountinfo": ROOT + PROC + "malformed unrelated row\n"},
            {"swaps": None}, {"swaps": ""},
            {"root-stat": "regular file|0:0\n"},
            {"target-stat": "regular file|0:0\n"},
            {"target-stat": "block special file|b3:1e\n"},
            {"target-stat": "block special file|zz:1f\n"},
            {"target-stat": "block special file|1000:1f\n"},
            {"target-stat": None},
            {"target-sys-path": "/sys/dev/block/179:31\n"},
            {"partition": None}, {"partition": ""}, {"partition": "0\n"},
            {"target-dev": "179:30\n"},
            {"target-dev": "179:31\n179:31\n"},
            {"target-dev": None},
            {"root-sys-path": "/sys/dev/block/179:29\n"},
            {"root-sys-path": None},
            {"root-stat": "block special file|b3:1e\n"},
            {"namespace": "mnt:[1234]\n"}, {"namespace": ""},
        )
        for change in changes:
            with self.subTest(change=change):
                self.rejected(changes=change)

    def test_invalid_expected_identity_refuses(self):
        for number in ("", "0:31", "179:", "179:031", "179:31 garbage",
                       "179:31\n179:31", "4096:31", "179:1048576"):
            with self.subTest(number=number):
                self.rejected(expected=number)

    def test_optional_root_pin_is_enforced(self):
        self.accepted(expected_root="179:29")
        self.rejected(expected_root="179:30")
        self.rejected(expected_root="0:0")
        self.rejected(expected_root="")

    def test_mount_or_root_change_during_collection_refuses(self):
        self.rejected(changes={"mountinfo-later": ROOT + PROC +
                               "38 36 179:31 / /mnt rw - ext4 /dev/root rw\n"})
        self.rejected(changes={"mountinfo-later": ROOT.replace("179:29", "179:30") + PROC})

    def test_swap_or_device_change_during_collection_refuses(self):
        self.rejected(changes={"swaps-later": SWAP_HEADER +
                               "/dev/disk/by-uuid/target partition 100 0 -2\n"})
        self.rejected(changes={"target-stat-later": "block special file|b3:1e\n"})

    def test_direct_execution_requires_explicit_check(self):
        for args in ([], ["--execute"], ["/dev/mmcblk0p31", "179:31"]):
            result = subprocess.run(["bash", str(GUARD), *args], capture_output=True,
                                    text=True, timeout=5, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("boot2_device_guard=passed", result.stdout)

    def test_library_can_be_embedded_without_main(self):
        source = GUARD.read_text()
        start = "# BOOT2_DEVICE_GUARD_LIBRARY_BEGIN\n"
        end = "# BOOT2_DEVICE_GUARD_LIBRARY_END\n"
        self.assertEqual(source.count(start), 1)
        self.assertEqual(source.count(end), 1)
        library = source.split(start)[1].split(end)[0]
        result = subprocess.run(["bash", "-n"], input=library, capture_output=True,
                                text=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
