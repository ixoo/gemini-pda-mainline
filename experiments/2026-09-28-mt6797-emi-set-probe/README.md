# One-shot mainline EMI region-18 policy diagnostic

The selected mainline boot has already powered CONN, released CONMCU reset and
reached the AHB Wi-Fi function/WCIR path while retaining its 2 MiB no-map boot
reservation. Its powered read returned empty region-18/19/23 ranges and a
nonzero region-1 control. The working [Gemian v9 boot](../2026-09-26-gemian-wifi-reference/results/runtime-v9-1.json)
completed both WLAN firmware-section copies while requesting the temporary
region-18 policy `0xb6da28` and sealing to `0xb6da2d`; each direct readback
matched. Mainline has not issued an EMI set call. This diagnostic tests that
missing secure-call/readback step without transferring firmware.

[Patch 0043](../../patches/proposals/0043-soc-mediatek-probe-bounded-MT6797-EMI-policy.patch)
extends only the one-shot CONSYS probe. Its named
`mt6797-a53-wifi-emi-set-probe` profile requires the previously checked
power/reset/HIF path and additionally claims the four-byte read-only EMI
selector at `0x10001f00`. Immediately before any set call, it requires CONN
confirmed ON, reset released, chip ID `0x0279`, selector bit 13 set, the
known nonzero region-1 read control and empty region-18/19/23 ranges plus
empty region-18/19 policy words. The boot reservation supplies an aligned,
32-bit first 512 KiB; the active selector chooses direct units. The first
SMC32 `0x82000209` requests region 18 at `0xb6da28`. Only a zero signed
low-word status and matching direct range/policy readback admit the final
`0xb6da2d` call. After that call, the owner checks its status/readback and
that neighboring range words stayed unchanged. It marks the attempt before
the first call and retains all powered resources and uncertain effects until
the reviewed reboot/recovery path. It never asks the secure service to lock a
region, writes region 19 or 23, copies firmware, starts it or enables DMA.

The **one-boot hypothesis** is that the deployed secure service accepts this
bounded region-18 policy pair from mainline and reports the requested words.
The unique observation is the exact built boot2 image and changed-boot kernel
identity joined to both signed statuses, immediate range/policy readbacks,
complete kernel log, A53 service regression and changed-boot Gemian return.
A precondition refusal makes zero set calls and redirects state/selector
investigation. A nonzero status, mismatching readback, changed neighboring
range, missing log or regression failure stops this candidate: preserve all
available evidence, do not replay the same image, and use only the reviewed
recovery path. Two matching requests support secure-service compatibility in
this one boot and permit designing the owned firmware-copy transaction; they
do not establish effective bus permissions, master domain, region-23 overlap
priority, exclusive external-writer handoff or working mainline Wi-Fi.

The effect budget is two region-18 secure set calls, their direct reads and
the already reviewed one-shot power/reset/HIF actions, once per boot. The
first call can have effects even when its status or readback fails. No
software timer can cancel an in-flight SMC; failure retains the current state
until recovery. The synthetic experiment author does not supply a DCO
certification, and this patch is not an upstream submission.

Build only from a clean pushed commit with `./scripts/build-kernel --backend
buildbox` using the named profile. Verify the kernel, DTB, binding and full
package inventory before composing a private boot2 candidate. Any later
installation uses the reviewed live-GPT boot2 guard, predecessor/full readback
and clean shutdown. The owner selects boot2 physically. Raw logs, firmware,
credentials and the boot image stay under ignored `artifacts/`.

## Prepared candidate

The clean pushed commit `5b99ce59d0b39132a9aa434143f201d506d9e026`
built on Buildbox under this named profile. Full package inventory, the focused
binding/example check, and schema validation of the built Gemini DTB passed.
The kernel schema target skipped optional `yamllint` because that package was
not installed in the retained `dtschema-2026.9` environment. The private
RAM root retains 52 members and identical firmware; only the release gate in
`init` changed. The candidate preserves the observed HIF board DTB and adds
only the EMI-selector resource and one-shot flag. LK boot-container validation
and the pinned candidate validator passed. Its full 16-MiB boot2 SHA-256 is
`4199be928613b2ec65b171bb2c9e27c98e8d434ac293fe3d8d9753a91c38d0f2`.
[Offline validation](results/offline-validation.json) and the
[checksum-only candidate receipt](results/candidate.json) pin the inputs;
no device action has occurred for this candidate.

The release-bound [collector](passive-host.py) records the complete mainline
log, parses both signed secure-call statuses and immediate range/policy
readbacks, runs the A53 service regression, and follows the reviewed native
Gemian return. The [USB watcher](watch-boot.py) has a 900-second budget and
requires the installer's deployment summary before it can arm. A refusal is
recorded as a completed diagnostic with `accepted: false`; it is not a Wi-Fi
pass and must not be replayed without a changed hypothesis.

## First device attempt and late capture

The reviewed installer ran from changed known-good Gemian boot
`27784c9e-5f97-44c4-ae4b-f03849bca6a0`, resolved inactive logical
`boot2` from the live GPT, passed its block-identity and stable-power gates,
and found the expected v9 Gemian predecessor. It wrote the candidate, matched
the full 16-MiB readback, and confirmed a clean shutdown. The prearmed
900-second USB watcher stayed at the MediaTek `20ff` stage through expiry.
The owner then confirmed boot2 selection and a visible mainline console. The
[watch receipt](results/attempt-1.json) records that host-only limit.

After watcher expiry, the Mac enumerated the mainline gadget with its expected
direct USB route. The validated collector captured a changed mainline boot ID,
complete sealed log, and the [positive one-boot result](results/runtime-1.json).
The same-boot power, chip-ID, reset-release and HIF gates passed. Immediately
before the secure calls, the selector was `0x11403200`, region-1 was the
expected nonzero control, and region-18/19/23 ranges were empty. Both bounded
region-18 SMC32 calls returned raw zero. The direct range readback was
`0xbfa0bfa7` for the first 512 KiB of the boot reservation; the policy
readback was `0x00b6da28` after the copy request and `0x00b6da2d` after the
final request. The owner logged the sealed state and made no firmware transfer.
The A53 RAM-service regression passed. Reviewed recovery returned a changed
Gemian boot with independently observed `wlan0/carrier=1`.

This establishes that this mainline boot can request and read back the two
region-18 policy values. It does not establish effective bus permissions,
master-domain mapping, region-overlap priority, external-writer exclusion,
firmware execution or usable mainline Wi-Fi. The next executor must own the
firmware-copy transaction and retain protection/resource lifetime through
handoff or failure; another secure-set-only boot has no decision value.
