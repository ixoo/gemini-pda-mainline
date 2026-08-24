# Experiment: DA921x read-only provider snapshot separation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-da921x-readonly-snapshot-separation` |
| Status | implementation input prepared; generation and build pending |
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

`pending-generation`: no support claim, build result, boot candidate, or device
action exists yet.
