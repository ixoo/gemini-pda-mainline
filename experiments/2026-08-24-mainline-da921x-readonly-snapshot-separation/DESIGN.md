# DA921x read-only provider snapshot separation

## Production shape

The provider-owner configuration owns one endpoint with exactly these
unconditional fields:

- the bound device pointer used only for refusal diagnostics;
- I2C adapter and address;
- one two-message read-transfer callback; and
- one mutex spanning both snapshot samples.

The positive transaction's delay callback and mutable transaction record stay
inside `REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION`. The read-only
profile sets that option and its firmware-writer transaction-window dependency
to `n`, so neither field nor the Buck-B writer is linked.

The stable callback clears its output, validates the endpoint and root-adapter
lock operations, then takes the endpoint mutex followed by the root-adapter
lock. It saves retries, sets retries to zero, reads `0x56`, `0x51`, `0x5e`,
`0xd9`, and `0xda` twice without a loop retry, and accepts only byte-identical
samples. Every exit restores retries and both locks. Only a complete match
publishes ABI 1 with `valid=1`; every failure leaves the public output zero.

Acquire and release keep their current request validation and structured
`-EOPNOTSUPP` refusal when the positive option is off. They cannot call the
read transport in that configuration.

## Test shape

One new KUnit object uses an unregistered in-memory adapter at address `0x2a`.
It is selectable only when the positive transaction and firmware-writer
transaction window are both off. Five focused cases cover:

1. exact two-sample success and field publication;
2. negative and short results at every one of ten read ordinals;
3. mismatch of each byte in the second sample;
4. missing, duplicate, wrong-context, and exact unregister behavior; and
5. acquire/release `-EOPNOTSUPP` with zero transfer calls.

Every applicable failure assertion also checks an all-zero public record,
one root-adapter lock/unlock pair, retry restoration, and absence of an
unlocked or retry-enabled transfer.

## Patch and build boundary

Buildbox generates two patches from canonical state
`ac57421ae45c6e55ba34f2cac4131647e89762ad5988baf1b47364c2c75e77cb`:

1. provider endpoint and stable callback separation; and
2. Kconfig, Makefile, and focused in-memory tests.

Generation, canonical admission, compilation, symbol inspection, and QEMU
KUnit are distinct gates. This experiment cannot produce a boot candidate,
contact the Gemini, enable a DT node, perform physical I2C, write retained RAM,
or request a CPU.
