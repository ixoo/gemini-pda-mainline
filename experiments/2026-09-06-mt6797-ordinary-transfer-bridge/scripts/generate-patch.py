#!/usr/bin/env python3
"""Deterministically generate the dormant ordinary-transfer proposal patch."""
from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent.parent
PATCH = HERE / "0012-wifi-mediatek-compile-ordinary-transfer-bridge.patch"
SOURCE = (HERE / "src/ordinary-transfer.c", HERE / "src/ordinary-transfer.h")
TARGETS = (
    "drivers/net/wireless/mediatek/mt6797/ordinary-transfer.c",
    "drivers/net/wireless/mediatek/mt6797/ordinary-transfer.h",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def new_file(path, target):
    lines = path.read_text().splitlines()
    body = ["diff --git a/%s b/%s" % (target, target),
            "new file mode 100644", "--- /dev/null", "+++ b/%s" % target,
            "@@ -0,0 +1,%d @@" % len(lines)]
    body.extend("+" + line for line in lines)
    return body


def generate():
    sections = [
        "From 0000000000000000000000000000000000000012 Mon Sep 17 00:00:00 2001",
        "From: MT6797 ordinary-transfer bridge experiment <nobody@example.invalid>",
        "Date: Sun, 6 Sep 2026 00:00:00 +0000",
        "Subject: [PATCH] wifi: mediatek: compile ordinary transfer bridge",
        "",
        "Add an original dormant batch bridge around the existing real HIF",
        "ordinary-section API.  It performs complete structural prevalidation",
        "and records bounded progress without adding an owner or runtime caller.",
        "",
        "Internal compile experiment only; synthetic non-certifying author, no DCO.",
        "Assisted-by: LLM",
        "---",
        " drivers/net/wireless/mediatek/mt6797/Makefile             |   1 +",
        " drivers/net/wireless/mediatek/mt6797/ordinary-transfer.c | %3d +" % len(SOURCE[0].read_text().splitlines()),
        " drivers/net/wireless/mediatek/mt6797/ordinary-transfer.h | %3d +" % len(SOURCE[1].read_text().splitlines()),
        " 3 files changed, %d insertions(+)" % (sum(len(p.read_text().splitlines()) for p in SOURCE) + 1),
        " create mode 100644 drivers/net/wireless/mediatek/mt6797/ordinary-transfer.c",
        " create mode 100644 drivers/net/wireless/mediatek/mt6797/ordinary-transfer.h",
        "",
        "diff --git a/drivers/net/wireless/mediatek/mt6797/Makefile b/drivers/net/wireless/mediatek/mt6797/Makefile",
        "index 917cdda..917cddb 100644",
        "--- a/drivers/net/wireless/mediatek/mt6797/Makefile",
        "+++ b/drivers/net/wireless/mediatek/mt6797/Makefile",
        "@@ -6,3 +6,4 @@ obj-y += image-binding.o",
        " obj-y += emi-abi.o",
        " obj-y += remap-fields.o",
        " obj-y += resource-layout.o",
        "+obj-y += ordinary-transfer.o",
    ]
    for path, target in zip(SOURCE, TARGETS):
        sections.extend(["", *new_file(path, target)])
    PATCH.write_text("\n".join(sections) + "\n")
    print(sha(PATCH.read_bytes()))


if __name__ == "__main__":
    generate()
