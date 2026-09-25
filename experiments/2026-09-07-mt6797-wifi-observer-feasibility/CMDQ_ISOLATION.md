# CMDQ-off diagnostic build rejected

The [AP-DMA alias audit](results/ap-dma-alias-audit.json) found that the
successful 56-patch native link includes `CONFIG_MTK_CMDQ=y`. Its selected
CMDQ subsystem table names the whole AP-DMA block. No explicit selected CMDQ
job targeting the WLAN channel was found, but a source search cannot exclude
dynamically assembled commands. Read-only Gemian inspection found one bound
`mtk_cmdq` platform device; that is not evidence of an AP-DMA command.

An experiment-only `CONFIG_MTK_CMDQ=n` fragment was tested on Buildbox. The
first configuration guard rejected the dependent `CONFIG_MTK_CMDQ_MT2701`
removal. After pinning that expected delta, compilation exposed a native SMI
debug macro with the wrong argument count in the CMDQ-off branch. A one-line
experimental correction allowed the complete source to compile, but the final
link failed with 462 undefined-reference lines covering 34 CMDQ symbols.
Display, power, camera, JPEG and other built-in drivers depend on CMDQ. The
[failure receipt](results/cmdq-isolation-link.json) pins the exact commits,
package and log checksum. Neither failed package is a boot candidate.

The fragment, correction patch and 57-patch selection were removed from the
active builder. Its last successful 56-patch inputs and configuration are
restored. Excluding CMDQ would require a broader client isolation that this
headless diagnostic has not justified. Its AP-DMA alias remains an unresolved
ownership path, alongside CONSYS remap/protection, shared clock ownership and
worker failure lifetime. No device write, CMDQ command or radio action was
performed in this build investigation.
