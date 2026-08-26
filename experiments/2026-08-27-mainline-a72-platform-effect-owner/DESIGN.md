# Serialized A72 platform-effect owner

## Ownership boundary

The existing `mt6797-a72-platform-state` device remains the sole owner of the
SPM regmap, exclusive PWRAP reset, MCUCFG mapping, and mutex. Enabling the new
default-off option extends that owner; it does not acquire parallel resources
or add a second lock. Read-only snapshots and effects therefore cannot overlap.

The owner accepts one nonzero attempt/cookie handle. It consumes that identity
before its first platform read and has no reset, release-after-isolation, or
retry API. A foreign handle performs no operation. The later binder must use
the same values as the DA921x provider generation/cookie so isolation can
require the exact held provider identity without taking provider ownership.

## P27 acquire and inverse

P27 acquire requires SPM `0x218 == 0x00010132`, then performs exactly:

1. set bit 0 and read back full word `0x00010133`;
2. read MCUCFG B-PLL word `0x4a0` for the proven ordering dependency; and
3. assert the exclusive PWRAP reset and require logical status one.

The cumulative result distinguishes every attempted effect from every
completed readback. Any failure after the first write retains P27 ownership and
seals the owner.

The only inverse is available while P27 is held and before isolation. It
requires exact held SPM/PWRAP state, deasserts and verifies PWRAP first, then
restores and verifies full SPM word `0x00010132`. Any mismatch retains the
handle and seals the owner; success retires P27 and seals it as released.

## Isolation and DCM

Isolation requires the exact platform handle and a DA921x provider handle with
matching attempt/cookie values. Under the same mutex it requires held P27,
external isolation `0x00000002`, and asserted PWRAP. It marks isolation
attempted before clearing SPM `0x290` bits 1:0, requires full readback zero,
deasserts and verifies PWRAP, and completes one 240--260 microsecond guard.
There is no guessed inverse after this operation begins.

DCM is allowed only from the isolated state with CPU8 reported online and CPU9
reported offline. It requires MCUCFG `0x274` bits 6:0 to be zero, preserves all
upper bits, writes and reads back low bits `0x0f`, then writes and reads back
`0x0d`. Completion and every post-isolation failure seal the owner.

## Hardware-free proof

The KUnit suite invokes only the internal owner with injected SPM words,
PWRAP state, MCUCFG words, delay recorder, and ordered action log. Eight cases
cover the complete success transcript, clean P27 refusal, every P27 fault,
exact inverse and its faults, provider/handle/isolation gates, every isolation
fault, CPU topology refusal, and every DCM read/write/readback fault.

The production API has no caller in this milestone. QEMU contains the physical
adapter but has no matching MT6797 device and the focused suite never invokes
it. No MMIO, reset controller, delay, provider, watchdog, retained RAM, secure
call, CPU request, device, or boot candidate is exercised.
