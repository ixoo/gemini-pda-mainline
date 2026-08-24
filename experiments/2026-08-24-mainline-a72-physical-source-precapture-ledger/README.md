# Experiment: A72 physical-source pre-capture ledger

## Status

The first physical-source candidate is rejected before its first retained
`before-bigidvfs` checkpoint. Changed-ID Gemian recovery found both owned
first-dmesg records exact empty, pstore empty, and the exact candidate still on
boot2. The result proves that BigiDVFS was not reached but cannot distinguish
observer non-entry, source deferral, or a platform/provider/clock failure.

This non-identical successor moves the two qualified first-dmesg records
earlier and intentionally makes no physical-source capture:

1. `probe-enter` is the first physical-source observer probe operation;
2. `sources-held` follows successful acquisition of the bound platform-state,
   protected-clock, and BigiDVFS source devices.

After record 2, the probe releases all three references and returns success.
It does not register the direct source or call platform, DA921x, protected
clock, BigiDVFS, publication, owner mutation, or CPU-request paths.

## Decision table

| Retained result | Interpretation | Next action |
| --- | --- | --- |
| neither | Observer probe did not enter, or the first-dmesg checkpoint refused | Move before observer probe/init without repeating this artifact |
| `probe-enter` only | Probe entered but all three bound source devices were not acquired on its first attempt | Split the three acquisition boundaries |
| `probe-enter` + `sources-held` | All three source devices were bound and retained; failure in the rejected candidate lies inside its capture path | Isolate platform, DA921x, and clock returns before reintroducing BigiDVFS |
| malformed or foreign record | Attribution failed | Reject without path inference |

## Safety and build contract

- At most two short writes use only first-dmesg records 1 and 2 through the
  already-qualified all-ones/empty-header, payload-before-metadata,
  signature-last, barrier, and full-readback writer.
- There is no overwrite, clear, retry, partition write, protected/secure call,
  MMIO snapshot, I2C transaction, owner mutation, CPU request, reset, reboot,
  or power operation in the new probe path.
- One canonical patch follows `0356` and is generated on Buildbox from the
  exact integrity-verified managed source. The patch is experiment-only and
  retains a synthetic, non-certifying author with no DCO sign-off.
- Buildbox compile, package checksums, linked/excluded symbol review, candidate
  assembly, and independent Android-v0 validation must pass before deployment.

## Next action

Generate and admit the one-patch pre-capture ledger, then compile its isolated
profile on Buildbox. No native VM kernel build is authorized.
