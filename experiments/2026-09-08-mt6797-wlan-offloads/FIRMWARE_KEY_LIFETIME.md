# Retained firmware key installation and transmit readiness

## Result

Command `0x07` has a mapped retained-firmware handler and a WLAN-index-specific
installation path. That path attempts a distinct unsolicited **event `0x24`**.
The public host handles this event by finding the BSS/peer station and enabling
its protected transmit queue. This supplies a concrete key-readiness protocol
edge omitted from the earlier host review; it does not establish receive replay
protection, reliable event delivery or safe rekey ordering.

The [receipt](results/firmware-key-lifetime.json) pins the existing firmware
identity, private analysis methods and four public host files. This is static
inspection in the RE VM, with the existing instruction/data mapping premises.
No firmware was executed, no device was accessed and no key material was read
from a live or captured network. Raw firmware, addresses and disassembly remain
private. The existing [station lifetime analysis](FIRMWARE_STATION_LIFETIME.md)
provides the command-dispatch and output-callback context.

## Command and installation path

The already decoded 81-entry dispatch table associates command `0x07` with a
handler whose selected direct-flow graph exhausts after 232 instructions.
It obtains the packet through incoming-object offset 8 and treats the next
eight bytes as the normal command header. The add/remove, peer, BSS, algorithm,
key index, length and WLAN-index accesses agree with the public
`CMD_802_11_KEY` at `include/nic_cmd_event.h:375–389`.

For add requests, one path looks up the peer and passes the complete command
payload, WLAN index and station pointer to a separate installation helper.
Other branches prepare key-material copy arguments for BSS-indexed storage;
they are not proof
that every key request follows the same installation/notification path. The
helper's selected graph exhausts after 460 instructions. The initially capped
384-node result is retained separately and is not treated as complete.

The installation helper prepares table fields and key-material copy arguments,
invokes a
mapped table-update wrapper and an unresolved callback with WLAN index,
algorithm, key index and prepared key-data pointer, then calls the notification
helper. The callback return is not tested before that notification call in the
inspected tail. The notification is therefore an observed sequencing point in
this static path, not a proved hardware-success acknowledgement. The callback's
implementation and error contract remain unavailable in the mapped plaintext.

## Unsolicited key-ready event

The notification helper requests a 16-byte object. If allocation returns null,
it takes a diagnostic/return path without constructing the event. On the
allocated path it writes the following fields and passes a six-byte peer-copy
tuple to the same unmapped copy-shaped helper seen in the station analysis:

| Field | Static construction | Public host match |
| --- | --- | --- |
| Packet length/type | 16 bytes / `0xe000` | Normal event header plus eight-byte payload |
| Event ID | `0x24` | `EVENT_ID_ADD_PKEY_DONE`, `include/nic_cmd_event.h:234` |
| Payload byte 0 | BSS index | `ucBSSIndex` |
| Payload bytes 2–7 | Peer-address source and six-byte copy arguments | `aucStaAddr[6]` |

The payload declaration at `include/nic_cmd_event.h:548–552` contains only BSS,
a reserved byte and peer address. It has no key ID, cipher or key generation.
The constructor does not explicitly copy the incoming command sequence into
this event; allocator/header initialization is not established here.

The host's selected `nic/nic_rx.c:2305–2324` case matches BSS plus peer address,
sets `fgIsTxKeyReady` and calls `qmUpdateStaRec()`. It does not correlate the
event with a pending command sequence or key incarnation.
`nic/que_mgt.c:400–435` requires that readiness flag before allowing transmit
for a valid station in a protected BSS. This is positive host transmit-gating
behavior, not a receive replay check.

The firmware notification uses output selector zero and the previously
inspected common output path. Activation responses used selector one. The
selector's queue and ordering meanings remain unresolved; neither value proves
a cross-queue fence. A normal add-key request's no-response setting therefore
must not be interpreted as absence of all firmware key events. Conversely, this
unsolicited event must not be mistaken for the ordinary command ACK.

## Receive-sequence and counter limit

The public command reserves payload bytes 48–63 for `aucKeyRsc`;
`include/mgmt/privacy.h:62` identifies algorithm 4 as CCMP. For an ordinary
16-byte CCMP key, neither inspected body directly uses the RSC field as a
receive-sequence source. This selected-body argument trace and the unknown
copy/callback implementations do not establish a firmware-wide absence of reads.
The earlier host result remains: ordinary Linux key addition does not populate
this field with the supplied receive sequence.

A selected installation branch with a station pointer, transmit-key flag and
non-authenticator role constructs six zero bytes and passes them with the WLAN
index to a mapped helper. That helper packs six input bytes little-endian into
two adjacent words at a destination supplied through an unresolved callback.
It preserves only the upper 12 bits of the second word. This is a concrete
initialization effect, but its address, counter direction and hardware meaning
are not established. Calling it an RX replay reset or a validated PN floor
would go beyond the evidence. No counter value or write from this image was
executed on the device.

A bounded search of immediate-address windows found the known callback loads
but no initializer resolving the selected key-output and destination callbacks.
It is not an exhaustive absence proof, and no ROM implementation is invented.

## Implementation consequence and validation

A future backend must distinguish local command submission, firmware key-ready
notification and receive replay validation. BSS/peer matching alone cannot
authenticate a late event after rekey or station reuse. A missing event must
remain a failure/uncertainty outcome, not become success or a blind repeated
key installation. Event reliability, key-switch ordering and queued old RX need
their own exact-firmware contract before advertising crypto/replay offload.

All selected walks except the retained initial installation walk exhausted their
queues without invalid instructions or unresolved non-call computed transfers.
Calls are skipped with an assumed return; selected immediate-derived callees
were inspected separately. These graph results do not prove every callee,
runtime path, cipher implementation or hardware effect. Private script hashes,
bounds and public source hashes are retained in the receipt. Repository checks
cover publication; no kernel build, radio test or mainline support is claimed.
