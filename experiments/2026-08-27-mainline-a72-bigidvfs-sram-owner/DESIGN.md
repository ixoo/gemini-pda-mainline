# One-shot A72 BigiDVFS SRAM-LDO owner

## Ownership boundary

The existing `mt6797-bigidvfs-backend` device remains the sole owner of the
secure transport and its operation mutex. The default-off SRAM option extends
that device; it does not create another platform device, lock, firmware
conduit, or raw-register interface. Existing stable readback and the new
effect therefore cannot overlap.

The public API accepts one request containing ABI, CPU, nonzero attempt and
cookie identities, provider-held attestation, isolation-crossed attestation,
and CPU8/CPU9 online state. It accepts only CPU8 while both A72 CPUs remain
offline and both prerequisite attestations are true. Structural invalidity is
`-EINVAL`; a valid but ineligible prestate is `-EPERM`. Neither consumes the
owner or performs an operation.

The later complete binder owns cross-resource composition. It must derive all
request fields from the same transition identity and the already-proven
provider/platform results; this owner neither acquires those resources nor
manufactures their evidence.

## Exact effect and proof sequence

The owner consumes and stores the exact request before its first effect. It
then performs exactly:

1. invoke implemented AArch64 FID `0xc20003bf` with `x1 = 110000` and all
   other arguments zero;
2. accept only return word zero, while recognizing that this is not state
   confirmation;
3. hold the backend mutex through one 240--260 microsecond settle;
4. read selector `0x102222b0`, calibration `0x102222b4`, selector again, and
   calibration again through existing FID `0xc200035f`;
5. require both complete samples to match full-word-for-full-word;
6. require selector low 12 bits `0x8fb`; and
7. require calibration upper 16 bits zero and lower 16 bits nonzero.

The result records the exact attempt, requested units, every attempted and
completed step, both raw samples, terminal error, effect-attempted state,
verification state, and sealing state. The existing four-register public
readback remains unchanged; only the owner may request the added calibration
address.

## Failure and one-shot boundary

Any failure after the set attempt is state uncertainty. The owner becomes
permanently faulted and sealed, the backend latches its existing sticky fault,
and no read or effect can proceed through that device. Selector/calibration
movement returns `-EAGAIN`; invalid stable state returns `-ERANGE`; transport
failures preserve their injected kernel errno. A repeated exact request returns
`-EALREADY`; a foreign identity returns `-EPERM`; neither performs another
operation.

There is no disable, voltage-change, inverse, reset, release, or retry API.
Once the service is attempted, external power remains owned by the encompassing
CPU8 transition and reset recovery is the only permitted failure exit.

## Hardware-free proof

The focused KUnit suite invokes only the internal owner with injected set,
delay, read, and ordered-log callbacks. Eight cases cover exact success,
structural and prerequisite guards, same/foreign one-shot rejection, service
failure, each of four read failures, selector/calibration instability, invalid
selector state, and both invalid calibration forms.

The production adapter is linked but has no production caller. QEMU has no
matching MT6797 device, and the test suite never invokes SMCCC or physical
delay. The profile contains exactly this KUnit test option and excludes the
platform-effect, executor, watchdog, ledger, provider, and protected-readback
test suites.
