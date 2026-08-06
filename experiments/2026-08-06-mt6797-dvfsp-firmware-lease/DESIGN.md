# Firmware-owner lease design

## Boundary

The existing Linux lease in patch `0174` serializes the handoff object and
holds its generation/cookie across one MT65xx I2C6 transfer. It does not prove
the vendor firmware pause source. Patch `0175` therefore adds a second,
private lease whose only authority is a registered external owner.

The current mainline handoff is not that owner: it maps only CSPM, validates a
stopped receiver, and has no CSRAM mapping, PCM image residency, firmware
request, or reset/IM/PCM kick sequence. A future owner must first establish
those start/resource facts, or explicitly identify a trusted firmware service
that has already started and owns the PCM. A direct `SW_PAUSE`/`FW_DONE`
implementation without that prerequisite is rejected.

```text
Linux transfer lease {generation,cookie}
        |
        +-- firmware acquire request (SEMA_I2C_DRV contract)
        |      pause source 0x2; SW_PAUSE bit 13; FW_DONE bit 15; 2 ms bound
        |
        +-- physical I2C6 transaction (future caller; not added here)
        |
        +-- firmware release request with the same owner handle
```

The callback registry is empty by default. Both operations are mandatory,
registration is single-owner, and unregister returns `-EBUSY` while a firmware
lease is held. The registry mutex stays held while the callback runs so its
context cannot disappear; a callback must not recursively register or
unregister itself.

## Acquire response

The owner must return:

- ABI and user identity unchanged;
- `status == 0`, `returned == 1`, and the exact Linux generation/cookie;
- a nonzero opaque `owner_handle`;
- pause-source map `0x2`;
- all three `SW_PAUSE` words asserted; and
- all three `FW_DONE` words asserted.

Only this response creates the stored firmware lease. A missing owner or a
fully structured refusal returns `-EOPNOTSUPP` before any lease is held.

## Release response

Release carries the exact Linux token and stored owner handle. A successful
response must echo the identity and handle, report `status == 0`, clear the
pause-source map, and clear all three `SW_PAUSE` words. The `FW_DONE` words are
an acquire acknowledgement and are not used as a post-release ownership claim.

Any release refusal, callback error, stale handle, malformed response, or
state/token change faults the handoff and retains the firmware lease. No
automatic inverse or retry is allowed.

## Review boundary

This contract names the vendor protocol but does not prove that the current
one-way receiver implements it. A future callback owner must identify its
firmware domain, prove callback lifetime and concurrent writers, and provide
independent evidence for the three pause/acknowledgement words. Until that
proof exists, the provider cannot perform page selection or register-data
writes.
