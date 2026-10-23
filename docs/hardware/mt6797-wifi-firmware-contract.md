# MT6797 Wi-Fi firmware: interface contract the driver relies on

This note records the behaviour the mainline driver depends on, at the level
needed to write and review driver code. It contains no firmware content, no
vendor source and no device-specific addresses; the underlying analysis is
retained privately, and this document states only what a driver author must do
or expect.

## Two images, two roles

The connectivity chip runs an on-chip system firmware (its RTOS, host
transport, radio stacks and the low-level HAL) and receives a separate Wi-Fi
image from the host at boot. The host-loaded image is a file the kernel reads
at runtime and hands to the chip: **no firmware is flashed**, so a bad image or
a rejected boot recovers by restoring the file.

The driver's business is with the host-loaded image and with the transport the
system firmware provides. Anything the driver does not explicitly ask for is
not its business.

## Transport

- One command is in flight at a time. Each command carries a sequence number
  and, when it has a reply, exactly one reply event comes back.
- Commands draw from a small credit pool that the driver must reconcile after
  each completion. A command refused for lack of credit did not execute.
- Receive traffic has two classes: replies to commands, and firmware-initiated
  notifications. Both must be serviced; a driver that only reads replies will
  stall.
- A short notification accompanies many ordinary commands. It is normal
  traffic, not an error, and must be consumed and discarded rather than
  treated as a fault.
- Command admission is state dependent: the same command can be accepted in
  one firmware state and refused in another, and the refusal is a protocol
  event, not a crash.

## Life cycle

Bring-up, in order: base configuration, NIC enable, regulatory domain, scan
filter. Scanning allows one scan in flight; a second concurrent request is
refused.

The tested join path activates the BSS slot, supplies BSS parameters, completes
authentication and association, and creates the station record. It then obtains
DTIM from a qualified post-association beacon and requires a credited connected
indication **before key installation**. This ordering is enforced by
[0211](../../patches/proposals/0211-wifi-mt6797-indicate-PM-connection-from-owned-beacon-before-keys.patch).
The connected indication is mandatory; association alone does not establish
the firmware's connected monitoring state.

Teardown, in order: abort indication, key removal, station removal, BSS slot
deactivation. This order is the only one that has produced a clean, fully
accounted teardown on hardware.

## Monitoring ownership

Once connected, the firmware owns beacon and connection monitoring and reports
loss by event. The driver must not run a competing beacon monitor; the
mac80211 flags expressing firmware ownership are the correct model, and the
driver must act on the firmware's loss event rather than on its own timeout.

## Keys

The firmware owns encryption and decryption. The driver receives key material
through mac80211's key callbacks and submits installation and removal commands.
The checked receive path also maintains separate host PN state for the initial
PTK and GTK, and rejects frames without the required metadata or a strictly
increasing PN. The [group RX contract](../../experiments/2026-10-13-mt6797-wifi-native-delivery-probe/MAC80211_GROUP_RX_CONTRACT.md)
describes those host checks; firmware crypto ownership does not replace them.

Key retirement and slot reuse for a second connection in the same boot are not
yet established. Returned command credits and station teardown alone do not
prove retirement of firmware-queued frames. Until that barrier is established,
the driver must not reset PN state or attempt a second protected lifetime.

## Diagnostic access

Two diagnostic paths exist and both are read-only from the driver's side: a
single-word register query and a bounded memory-dump query over a fixed window
of on-chip capture memory. The memory-dump path is the one used for the
project's capture work. Neither may be used to write registers.

## What this contract does not cover

- Power save: the firmware runs with power save off, which is why battery cost
  is high. Enabling it needs a firmware-side contract that is not yet derived.
- Bands and rates: only the tested access point and channel have been
  exercised. Aggregation is different: the firmware enables TX and RX
  block-ack by default in both directions, so the driver neither configures it
  nor may assume it is off. A driver that needs it disabled would have to send
  the firmware's aggregation control command, which this driver does not.
- Monitor mode: a firmware facility exists; its semantics are unverified.
- A delivery delay for a reserved management frame submitted shortly after a
  firmware keep-alive instant. The frame is not lost: it is held in the
  firmware's management queue and released when a later station- or key-state
  command reaches the firmware, which is normally the teardown chain itself.
  It then completes with either a transmitted status or a flushed status, and
  **a flushed completion means the frame never reached the air**. The driver
  must therefore report a deauthentication as sent only on a transmitted
  completion, and must not treat its own timeout as a transmission result. The
  host cannot observe the firmware's keep-alive instant, so it cannot
  deliberately schedule around the window.

## Obligations for driver changes

1. Keep one command outstanding and reconcile credit after every completion.
2. Service both receive classes, and discard the per-command notification.
3. Follow the bring-up, join and teardown orders above; never skip the
   connected indication.
4. Treat a state-dependent refusal as a protocol result, not a fault.
5. Do not use either diagnostic path to write.
6. Do not attempt a second connection lifetime until key retirement is
   characterised.
