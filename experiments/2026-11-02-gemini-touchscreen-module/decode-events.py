#!/usr/bin/env python3
"""Summarize a capture of /dev/input/eventN taken on the arm64 station."""
import struct
import sys

EVENT = struct.Struct("<qqHHi")
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
ABS_MT_SLOT, ABS_MT_POSITION_X, ABS_MT_POSITION_Y = 0x2f, 0x35, 0x36
ABS_MT_TRACKING_ID = 0x39

data = open(sys.argv[1], "rb").read()
slot = 0
active = {}
frames = peak = 0
contacts = {}
for offset in range(0, len(data) - EVENT.size + 1, EVENT.size):
    _, _, kind, code, value = EVENT.unpack_from(data, offset)
    if kind == EV_ABS and code == ABS_MT_SLOT:
        slot = value
    elif kind == EV_ABS and code == ABS_MT_TRACKING_ID:
        if value < 0:
            active.pop(slot, None)
        else:
            active[slot] = value
            contacts[value] = {"slot": slot, "x": [], "y": []}
    elif kind == EV_ABS and code in (ABS_MT_POSITION_X, ABS_MT_POSITION_Y):
        if slot in active:
            axis = "x" if code == ABS_MT_POSITION_X else "y"
            contacts[active[slot]][axis].append(value)
    elif kind == EV_SYN and code == 0:
        frames += 1
        peak = max(peak, len(active))

print(f"events {len(data) // EVENT.size}, frames {frames}, "
      f"contacts {len(contacts)}, most at once {peak}")
for tracking_id, contact in contacts.items():
    x, y = contact["x"], contact["y"]
    if x and y:
        print(f"contact {tracking_id} slot {contact['slot']}: "
              f"x {min(x)}..{max(x)} y {min(y)}..{max(y)} samples {len(x)}")
    else:
        print(f"contact {tracking_id} slot {contact['slot']}: no position")
