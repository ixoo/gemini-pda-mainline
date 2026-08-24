# Experiment: DA921x read-only provider snapshot separation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-da921x-readonly-snapshot-separation` |
| Status | patches generated, validated, and admitted; isolated build pending |
| Subsystem | DA921x provider registry and stable snapshot |
| Device variant | hardware-free source and in-memory KUnit only |
| Date(s) | 2026-08-24 America/New_York |
| Tracking | Roadmap Gate 7 physical-source qualification Phase A |

## Question

Can the already implemented stable five-register DA921x snapshot be available
under the provider owner without compiling the positive Buck-B writer?

## Hypothesis

Yes. The snapshot needs only an adapter, address, transfer callback, and mutex.
Those fields and the fixed reader can be unconditional under the provider
owner, while the delay callback, transaction result, acquire/release machinery,
and Buck-B writer remain under their existing positive option.

## Exact input

- Repository parent: signed and pushed commit
  `c08b2e819bd4c9bc28aea76b16fb437545831f3d`.
- Canonical parent: patch `0347` in `patches/series`.
- Prepared Buildbox source state:
  `ac57421ae45c6e55ba34f2cac4131647e89762ad5988baf1b47364c2c75e77cb`.
- Prepared-source integrity:
  `d87fe0d866aec4825c2e2c2bf5f1df628299692e5bad63e581b07c64d0f3c22d`.

Exact edited-file hashes, constraints, and result fields are pinned in
[`contract.json`](contract.json). The implementation and test boundary is in
[`DESIGN.md`](DESIGN.md).

## Safety

This stage creates only deterministic patch-generation input. It performs no
kernel build, device access, physical I2C, MMIO, SMC, retained-memory write,
CPU action, boot-image construction, or partition write. Generated patches
remain non-candidates until canonical admission and their isolated Buildbox
KUnit proof.

## Procedure

1. Verify the clean pushed repository commit and exact canonical source state.
2. Copy only the five pinned source files into an ephemeral Buildbox worktree.
3. Apply the provider separation and validate the production source.
4. Add the focused test and validate the cumulative source.
5. Create two unsigned experiment-authored `git format-patch` files.
6. Replay both patches on the pinned parent and run strict checkpatch.
7. Fetch only the validated patch-review package for local admission.

Commands after this input is signed and pushed:

```sh
./scripts/buildbox generate-da921x-readonly-snapshot-patches
./scripts/buildbox fetch-da921x-readonly-snapshot-patches
```

## Current result

Buildbox generation from exact clean commit
`866d528c6454cd1fd49c4446ac432791984af61f` passed the pinned-source,
semantic, exact replay, and strict checkpatch gates. The two generated files
were fetched with validated package checksums and admitted byte-for-byte as
canonical patches `0348` and `0349`. Their exact identities and generation
receipt are in [`contract.json`](contract.json) and
[`results/buildbox-generation-866d528c.txt`](results/buildbox-generation-866d528c.txt).

The isolated `da921x-readonly-snapshot-kunit` profile explicitly disables the
positive provider transaction and firmware-writer transaction window. Its
Buildbox compile, linked-symbol inspection, and focused no-network QEMU proof
remain pending. No support claim, boot candidate, hardware operation, device
action, or CPU request exists yet.
