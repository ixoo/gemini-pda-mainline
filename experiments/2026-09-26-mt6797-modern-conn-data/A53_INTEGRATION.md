# A53 modern CONN provider integration gate

The isolated modern MT6797 CONN child-domain proposals compile, but they have
not been linked with the accepted A53 service foundation. This profile checks
that exact integration before a shared CONSYS owner or effect-bearing DT child
is added. It keeps the frozen A53 fragments and patch bytes, then selects the
nine modern provider proposals in canonical series order. Only the modern
provider is enabled; the legacy SCPSYS provider remains disabled.

The hypothesis is that the combined kernel links with the modern provider and
MT6797 CONN data, while the resulting Gemini DTB contains no modern controller
compatible, CONN child or consumer. The unique evidence is the clean pushed
project commit, validated Buildbox package, resolved config, linked symbols and
DTB inspection. A patch conflict or link failure must be repaired at the
specific integration boundary. A DTB containing an enabled modern CONN child
would invalidate this compile-only gate and require a separate effect review.

This profile is not a boot2 image or device candidate. No new CONN power,
rail, reset, remap, EMI, firmware, radio or DMA action is requested. A later
active candidate still needs one shared owner, external VCN/CONMCU sequencing,
retained-writer exclusion, remap/EMI policy and failure retention. Build success
alone will not prove those contracts or Wi-Fi support.
