# Exclude the generic AP-DMA CMDQ alias from the native diagnostic build

The [bounded alias audit](results/ap-dma-alias-audit.json) found that the
56-patch native link selects `CONFIG_MTK_CMDQ=y`. Its compiled subsystem table
names the whole AP-DMA block, while the intended WLAN observation owns only
the `0x11000080+0x80` channel. A source search found no explicit selected CMDQ
job targeting that channel, but a static address search cannot exclude
commands assembled dynamically. Read-only Gemian inspection confirmed one
bound `mtk_cmdq` platform device; that is not evidence of an AP-DMA command.

The [experiment fragment](cmdq-isolation.fragment) requests only
`CONFIG_MTK_CMDQ=n` for the headless native diagnostic kernel. The
[Buildbox builder](build-full-kernel.py) requires that exact resolved change
and records the fragment checksum. The first full compile found the native SMI
debug macro has the wrong argument count when CMDQ is off. A one-line
[experiment patch](patches/cmdq-isolation/0001-smi-keep-debug-macro-arity-without-CMDQ.patch)
keeps the caller's output selector argument but ignores it in that configuration;
the CMDQ-enabled branch is unchanged. The patch applies cleanly after the
prior 56. This creates a 57-patch source identity. This is a
candidate-isolation choice, not a board default or a change to the running
Gemian system. Full native linking and package validation are pending.

Disabling the CMDQ driver excludes its compiled submission path from this
kernel, but does not prove exclusive AP-DMA or clock ownership. Other kernel
clients, firmware masters, CONSYS remap/protection changes and unfinished
workers still need candidate-specific bounds before a radio cycle. No device
write or CMDQ/radio action occurred.
