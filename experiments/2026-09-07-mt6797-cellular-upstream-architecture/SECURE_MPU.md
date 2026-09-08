# Retained secure handler for modem MPU regions 7 and 13

## Result

The retained secure firmware implements the two region paths named by the
[Gemian protection log](GEMIAN_HANDOFF.md): AP–MD1 shared region 7 and staged
MD1 region 13. Both can reject a request because of an existing software lock
before any register write. Neither path verifies its final hardware writes.
This narrows the missing contract from an unknown implementation to **current
firmware identity, lock state, accepted result and resource lifetime**. It
admits no secure call, register read, mapping or memory release.

The [existing secure ABI audit](../2026-09-05-mt6797-wifi-contract/RETAINED_EMI_SECURE_ABI.md)
owns service dispatch, signed-low-word returns, selector-dependent address
normalization and their limitations. This follow-up extends its region-18/19
analysis to the two modem regions; those shared findings are not independently
new runtime observations.

## Input and region dispatch

The existing private `tee1.img` is 5,242,880 bytes with SHA-256
`2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
Its identity was verified before and after analysis in the RE VM. The existing
mapping is analysis address = file offset + `0x000ff3c0`. No new capture,
firmware execution or live-device operation occurred. The historical persistent
slot comparison linked by the earlier ABI audit is not today's active-firmware
attestation.

The handler indexes the 22-entry signed-halfword table at `0x1125e8` by
`region - 2`. Each target is `0x105588 + 4 * signed_entry`.

| Region | Table entry address | Entry value | Handler address | Software-lock byte | Range register | Permission register |
| --- | --- | ---: | --- | --- | --- | --- |
| 7 | `0x1125f2` | 102 | `0x105720` | `0x11dab8` | `0x10200198` | `0x102001bc` |
| 13 | `0x1125fe` | 222 | `0x105900` | `0x11daab` | `0x10200288` | `0x102002ac` |

Both handlers compare their lock byte with 1 and return low-word `0xfffffffc`
(-4) on equality. Otherwise a request with policy bit 26 set stores 1 to that
byte **before** programming. The unlocked path performs a barrier, clears the
permission register, performs a barrier, stores the normalized packed range,
performs a barrier, then reaches the shared permission-store tail at `0x105674`
and zero-return at `0x105c8c`. There is no final readback and no lock-clear path
in either traced region handler. This describes firmware software locks, not
their live values, complete hardware locking or overlap arbitration.

## Join to the host and loader

The [pinned host source receipt](results/memory-handoff-sources.json) identifies
`emi_mpu.c:1124–1138` and `emi_reg_rw.c:74–82`. The public wrapper masks the
policy to 24 bits, packs the region in bits 31:27, calls the lower secure
operation, discards its result and returns zero. It cannot request bit 26
through that packing, but it also cannot override an existing secure lock.
Applied to the three saved-log requests, its packed arguments would be:

| Saved request | Packed policy/region word | Lock request bit |
| --- | --- | ---: |
| Region 7, `0xb6d140` | `0x38b6d140` | 0 |
| Region 13 first stage, `0x16db44` | `0x6816db44` | 0 |
| Region 13 second stage, `0x16db64` | `0x6816db64` | 0 |

These are source-derived arguments, not captured SMC transactions. A logged
request followed by an outer zero return therefore cannot distinguish accepted
programming from the secure handler's lock denial. Even an attributable inner
zero would establish the store path, not verified hardware state.

The pinned public LK platform code separately requests an unlocked default for
shared region 7 (`ccci_lk_load_img_plat.c:775–781`) and deliberately omits the
lock request for image region 13 (`:356–364`). That is consistent with later
host updates, but does not prove that those policies were executed or that no
other agent locked either region. Source:
[LK platform file at f4988d74](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/ccci_lk_load_img_plat.c),
SHA-256 `3490e14dd9d61428a58ca6927089b048b365a65948f334567092b5f31887efae`.

## Reproduction and validation

Capstone 4.0.2 decoded the table and both complete 80-byte region windows.
GNU AArch64 objdump 2.42 independently decoded both windows and agreed on the
lock checks, stores and common-tail branches. Against the exact private input:

```sh
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0xff3c0 \
  --start-address=0x105720 --stop-address=0x105770 PRIVATE_TEE_INPUT
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0xff3c0 \
  --start-address=0x105900 --stop-address=0x105950 PRIVATE_TEE_INPUT
```

| Private file extent, half-open | SHA-256 |
| --- | --- |
| Region 7 `[0x6360,0x63b0)` | `4016af6eaeae6334d01268138b73a10d87777f04b4305fac07658086e08ce3f6` |
| Region 13 `[0x6540,0x6590)` | `d3a0b80783667b6a416ce9385bbf7e86dd83729a1de9a77eba7cc9cb70b6b7f3` |
| Region 7 table entry `[0x13232,0x13234)` | `887a0529fd9d76eb33c0ec808c05daaf32fa9f5e21e4c32224fb4bfaaa0af385` |
| Region 13 table entry `[0x1323e,0x13240)` | `08dc6a1a955ff0fca0a047e27264c5c090bd2f3b98d64dcc4deb43cb770b4c0d` |

Firmware bytes and raw disassembly remain private. Source references, dispatch
arithmetic and packed policy bits were checked. Repository, local-link,
whitespace and bounded sensitive-data checks passed before publication. No
kernel build or hardware support test was performed. Current acceptance,
translation/overlap ownership and MD1–MD3 release lifetime remain unresolved;
another identical protection request is not a diagnostic for those gaps.
