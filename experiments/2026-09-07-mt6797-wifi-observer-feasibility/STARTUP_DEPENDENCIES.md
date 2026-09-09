# Minimal Wi-Fi startup dependencies

Source assessment, 2026-09-09. The minimal startup selected in
[cycle control](CYCLE_CONTROL.md#minimal-startup-direction-and-kernel-actors-2026-09-09)
needs a concurrent WMT command responder and two firmware lookup arrangements.
A one-shot detector loader followed by a blocking WLAN-on write cannot supply
all these dependencies. No startup program, radio operation or candidate is
admitted by this assessment.

The [receipt](results/startup-dependencies-review.json) pins seven source files
against their complete Git objects at Gemian commit
`59e00a9144d782e148332009a835b99c43382467`, six recorded compiler commands and
the retained resolved configuration. The package is the same compile-review
artifact validated by the [compiler-input assessment](NATIVE_SOURCE_FEASIBILITY.md#recorded-compiler-command-follow-up-2026-09-09).
These are source/build facts, not installed-binary or current-boot attribution.

## Initialization and the asynchronous dependency

The established [detector producer](../2026-09-06-mt6797-connectivity-producer-source-attribution/README.md)
and [inner initialization order](../2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/README.md)
remain separate from function-on. Detector registration does not run the
connectivity initializer. The later initializer registers common, Bluetooth,
GPS, FM, WLAN and ANT paths in its recorded order; excluding their userspace
services does not remove those registrations. Preserve per-component results
and actual resource effects instead of accepting the arithmetic aggregate as
readiness. These vendor interfaces are experiment compatibility dependencies,
not proposed mainline APIs.

In `wmt_ic_soc.c`, `CFG_WMT_MULTI_PATCH` is defined as 1. The ordinary SoC
initialization calls `mtk_wcn_soc_patch_info_prepare()` before reading the patch
count and downloading the patches. It returns an error if preparation fails.
The preparation call reaches `wmt_ctrl_patch_search()`, which sends `srh_patch`
to userspace through `wmt_ctrl_ul_cmd()` and waits for a response. Its signal
budget is 2000 ms. This wait occurs inside common initialization, so the
responder must already be available while the separate WLAN request is blocked.
Pre-setting a patch filename does not remove this selected search call.

`WMT_open()` waits for the common-device initialization flag. That flag is set
before some later initialization work, so an open is not proof that every
initializer or resource effect completed. Its close path decrements a software
reference count;
it does not call function-off or prove resource shutdown. A responder exiting
or losing its descriptor is therefore not a recovery action.

## Command service is not a harmless logging stream

`WMT_read()` obtains the command with `wmt_lib_get_cmd()`, which clears the
pending bit before the copy to userspace. A short destination buffer truncates
the result, and a copy fault still consumes that pending indication. Do not
inspect this interface on the live device as if it were passive log output.
A selected responder must use one complete bounded read and retain what it
actually received; truncation or an error ends the normal-cycle interpretation.

The reply parser compares the zero-filled buffer case-insensitively with `ok`.
A newline is significant: a conventional line-oriented `ok\n` reply is rejected.
Other nonempty replies signal failure. The signal contains a result, without
a command sequence number. The request timeout path does not clear an unread
pending bit. The responder must not retry, acknowledge an unknown request, or
send a late success after timeout; those cases cannot establish which request
completed. This identifies requirements for the exact responder, not permission
to substitute a program that blindly acknowledges requests.

Patch metadata is also more than a name. `SET_PATCH_NUM` allocates an array;
`SET_PATCH_INFO` copies each download-sequence/address/name record into it.
Its static completion counter counts submissions, without establishing that
all sequence indices were unique. A successful ioctl return therefore cannot
replace a complete, ordered, duplicate-free manifest and captured publication
result. The existing launcher implementation and its selected metadata still
need attribution before it can be used in this startup.

## Two firmware consumers

| Consumer | Inspected lookup contract | Consequence for the minimal filesystem |
| --- | --- | --- |
| Common WMT patch/config reads | `wmt_dev_patch_get()` calls `request_firmware()` with the supplied name. Firmware class tries the optional configured directory, versioned/update directories, then `/lib/firmware`. | Pin the exact requested names and bytes and provide them in the direct lookup path before any request. A filename alone is not a loaded-byte identity. |
| WLAN image | `kalFirmwareOpen()` tries `/storage/sdcard0/` then `/vendor/firmware/`; the selected `CONFIG_ANDROID=y` excludes its `/lib/firmware/` alternative. MT6797 appends `_6797` to `WIFI_RAM_CODE`. | Supply the selected image under the native WLAN path and exclude an unintended earlier match. Placing only that image in `/lib/firmware` does not satisfy this build. |

The WLAN `request_firmware()` alternative is under `#if 0`; it must not be
confused with the active common-WMT helper. The firmware-class user-helper
fallback is enabled in this configuration. Its source default timeout is one
second, not a measured bound on file I/O or the complete cycle, and the timeout
is mutable. A fallback attempt or missing direct file is an unsuccessful
startup predicate; no helper should silently provide different bytes. Firmware,
configuration and calibration applicability remain distinct, privately pinned
inputs, with no redistribution permission implied here.

## Sequence to finish

Prepare and verify the fixed filesystem and capture/recovery facility first.
Then initialize the selected built-in stack, recording each initializer result
and callback registration before the first WLAN request. Start and verify the
attributed command responder, including its transport mode and exact patch
manifest. Only after those gates should the separately admitted controller
request one WLAN load and shutdown while the responder and capture remain
active. Any early WLAN callback, missing reply, fallback, alternate consumer or
incomplete evidence invalidates the normal-cycle result.

This is a dependency order, not a runnable session: the responder identity and
metadata, early initialization effects, persistent capture layout and total
recovery budget are still unresolved. No current service, character device,
firmware, configuration, partition or radio state was read or changed. Only
public source and retained build records were inspected on Buildbox.
