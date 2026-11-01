# Offline boundary: preloader and A53 MTCMOS

This note records the offline work that was attempted but did not produce a
complete per-register sequence. It exists so the boundary is explicit rather
than implied by silence.

## Preloader

Input: retained preloader `boot0` image, build string `20190517-154415`.

Observed:

- Plaintext strings: `Pll init start...Done`, `mtcmos Start..Done!`,
  `vproc/vsram run as hw default`, `Set SRAM to 1.1V`, the
  `MT_CPU_DVFS_LL/L/B` domain names, and PWRAP/PMIC/DRAM init strings.
- The image contains a `BRLYT` boot header and a Thumb-2 code region. The
  string block is at file offset `0x260c8`; a plausible Thumb mapping uses
  base `0x200a00`, putting the block at `0x26ac8`.
- The code region around file offset `0x1c000` decodes as Thumb-2 and contains
  the expected PMIC/PLL/DRAM helper patterns.

Not established:

- The exact load base and section layout of the preloader.
- A reliable cross-reference from the PLL/MTCMOS strings to their callers.
- The initial CPU PLL, MTCMOS and VPROC/VSRAM register sequence.

Reason: the preloader is a multi-stage, partially position-dependent image;
without a confirmed load map, string cross-references are ambiguous. Closing
it needs a dedicated loader-format study, not a generic disassembly pass.
This does not affect the Linux/ATF ownership conclusions.

## A53 CPUSYS0/1 MTCMOS

Input: retained `tee1` TEE/ATF image.

Observed:

- Strings `Enable CPUSYS0`, `Enable CPUSYS1`, `CPUSYS1 OFF`,
  `CPUSYS0/1`-related branch code, and `big armpll`.
- The strings are referenced from AArch64 code near analysis addresses
  `0x10210c` (`Enable CPUSYS1`) and `0x10217c` (`Enable CPUSYS0`).
- The same region contains the MP2 path: a call to the per-core helper at
  `0x103c84`, SPM writes around `0x1022023c`/`0x10220400`, and cluster-index
  checks. This is consistent with a shared CPU power-on dispatcher for the
  A53 clusters and MP2.
- The MP2 cluster-top helper and per-core sequence were already audited in the
  [A72 firmware/power contract](../../2026-07-22-a72-firmware-power-contract/README.md).

Not established:

- The exact A53 CPUSYS0/1 MTCMOS, reset and isolation register sequence.
- Whether the A53 path shares every ordering rule with MP2 or only the
  dispatcher shape.

Reason: the A53 path was not decision-relevant to the current mainline CPU
work, and decoding the full ATF dispatcher without symbols is a larger
separate task. The existing MP2/secure-off audit remains the authoritative
deep result.

## What this means

The unknowns closed by this experiment are the PPM/HICA policy model and the
layered PCM/iDVFS ownership. The preloader and A53 MTCMOS remain offline-hard
but bounded; neither changes the current mainline provider boundary.
