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

Join, in order: BSS slot activation, BSS parameters, authentication and
association, station record, key installation, and finally the connected
indication. **The connected indication is mandatory.** Without it the firmware
runs its own no-connection timer and will stop traffic on its own schedule,
regardless of what the host believes.

Teardown, in order: abort indication, key removal, station removal, BSS slot
deactivation. This order is the only one that has produced a clean, fully
accounted teardown on hardware.

## Monitoring ownership

Once connected, the firmware owns beacon and connection monitoring and reports
loss by event. The driver must not run a competing beacon monitor; the
mac80211 flags expressing firmware ownership are the correct model, and the
driver must act on the firmware's loss event rather than on its own timeout.

## Keys

The firmware owns the crypto engine. The driver installs and removes keys and
never touches key material, sequence numbers or replay state. Key retirement
and slot reuse for a second connection in the same boot are not yet
established; until they are, the driver must not attempt a second lifetime.

## Diagnostic access

Two diagnostic paths exist and both are read-only from the driver's side: a
single-word register query and a bounded memory-dump query over a fixed window
of on-chip capture memory. The memory-dump path is the one used for the
project's capture work. Neither may be used to write registers.

## What this contract does not cover

- Power save: the firmware runs with power save off, which is why battery cost
  is high. Enabling it needs a firmware-side contract that is not yet derived.
- Bands, rates and aggregation: only the tested access point and channel have
  been exercised.
- Monitor mode: a firmware facility exists; its semantics are unverified.
- A transmission stall observed when a reserved management frame is submitted
  shortly after a firmware keep-alive instant. Its cause is not established
  and may be in hardware.

## Obligations for driver changes

1. Keep one command outstanding and reconcile credit after every completion.
2. Service both receive classes, and discard the per-command notification.
3. Follow the bring-up, join and teardown orders above; never skip the
   connected indication.
4. Treat a state-dependent refusal as a protocol result, not a fault.
5. Do not use either diagnostic path to write.
6. Do not attempt a second connection lifetime until key retirement is
   characterised.
