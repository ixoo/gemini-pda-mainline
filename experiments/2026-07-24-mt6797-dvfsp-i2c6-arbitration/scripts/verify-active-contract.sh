#!/usr/bin/env bash
# Read-only identity and call-graph checks for the retained active Gemian ELF.

set -euo pipefail

if [[ $# -ne 2 ]]; then
	echo "usage: $0 ACTIVE-VMLINUX PUBLIC-SOURCE-TREE" >&2
	exit 2
fi

vmlinux=$1
source_tree=$2
source_rev=59e00a9144d782e148332009a835b99c43382467
expected_vmlinux_sha=cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162
objdump_tool=aarch64-linux-gnu-objdump

for tool in sha256sum nm git "$objdump_tool"; do
	if ! command -v "$tool" >/dev/null 2>&1; then
		echo "missing required tool: $tool" >&2
		exit 1
	fi
done

if [[ ! -f $vmlinux ]]; then
	echo "active ELF not found: $vmlinux" >&2
	exit 1
fi

if ! git -C "$source_tree" cat-file -e "$source_rev^{commit}" 2>/dev/null; then
	echo "source revision unavailable: $source_rev" >&2
	exit 1
fi

actual_vmlinux_sha=$(sha256sum "$vmlinux" | awk '{print $1}')
if [[ $actual_vmlinux_sha != "$expected_vmlinux_sha" ]]; then
	echo "active ELF checksum mismatch: $actual_vmlinux_sha" >&2
	exit 1
fi

echo "active_vmlinux_sha256=$actual_vmlinux_sha"
echo "source_revision=$source_rev"

check_source_blob()
{
	local path=$1
	local expected_sha=$2
	local actual_sha

	actual_sha=$(git -C "$source_tree" show "$source_rev:$path" | sha256sum | awk '{print $1}')
	if [[ $actual_sha != "$expected_sha" ]]; then
		echo "source blob checksum mismatch: $path $actual_sha" >&2
		exit 1
	fi
	echo "source_blob_sha256=$actual_sha path=$path"
}

check_source_blob drivers/i2c/busses/i2c-mtk.c \
	7624af7e123ab907ee6e649e09b6d3e2a1c06c34e91755145faf4065ce3fa3d8
check_source_blob drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid.c \
	2aeab8496b9ba7a107e380ff211fe7f08d76e69ad63ece7f0e099762dcf50712
check_source_blob drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c \
	3f69c3b3a331a70336f7a4010cd4482f6743b0b69cef6df4c641d5be259eccd3
check_source_blob drivers/misc/mediatek/base/power/include/mt_cpufreq_hybrid.h \
	0ff84b9275cfec2d3a09c84b32f89d7823ede4085aa9fde6e1bfd384ca849da2

symbols=$(nm -n "$vmlinux")

check_symbol()
{
	local expected_address=$1
	local name=$2
	local actual_address

	actual_address=$(awk -v symbol="$name" '$3 == symbol { print $1; exit }' <<<"$symbols")
	if [[ $actual_address != "$expected_address" ]]; then
		echo "symbol mismatch: $name expected=$expected_address actual=${actual_address:-missing}" >&2
		exit 1
	fi
	echo "symbol=$name address=$actual_address"
}

check_symbol ffffffc000418330 _mt_cpufreq_syscore_resume
check_symbol ffffffc000418650 __switch_cpuhvfs_on_off
check_symbol ffffffc00041ee68 __cspm_unpause_pcm_to_run.isra.7
check_symbol ffffffc00041eff8 cspm_unpause_pcm_to_run
check_symbol ffffffc00041f0c0 cspm_release_semaphore
check_symbol ffffffc00041f3f0 __cspm_pause_pcm_running
check_symbol ffffffc00041f820 cspm_pause_pcm_running
check_symbol ffffffc00041f8e8 cspm_get_semaphore
check_symbol ffffffc00041fa30 cspm_stop_pcm_running
check_symbol ffffffc00041fd90 cpuhvfs_dvfsp_resume
check_symbol ffffffc00041fe70 cpuhvfs_stop_dvfsp_running
check_symbol ffffffc00041fea8 cpuhvfs_restart_dvfsp_running
check_symbol ffffffc00041ffd8 cpuhvfs_get_dvfsp_semaphore
check_symbol ffffffc000420010 cpuhvfs_release_dvfsp_semaphore
check_symbol ffffffc000420308 cpuhvfs_kick_dvfsp_to_run
check_symbol ffffffc000908b40 __mt_i2c_transfer
check_symbol ffffffc000909a28 mt_i2c_transfer

disassemble()
{
	"$objdump_tool" -d --disassemble="$1" "$vmlinux"
}

check_call_count()
{
	local caller=$1
	local callee=$2
	local expected=$3
	local count

	count=$(
		disassemble "$caller" |
			awk -v callee="$callee" '
				/[[:space:]]bl[[:space:]]/ &&
				index($0, "<" callee ">") {
					count++
				}
				END {
					print count + 0
				}
			'
	)
	if [[ $count -ne $expected ]]; then
		echo "direct BL call count mismatch: $caller -> $callee expected=$expected actual=$count" >&2
		exit 1
	fi
	echo "direct_bl_call_count=$count caller=$caller callee=$callee"
}

check_call_count cspm_get_semaphore cspm_pause_pcm_running 1
check_call_count cspm_release_semaphore cspm_unpause_pcm_to_run 1
check_call_count cspm_stop_pcm_running __cspm_pause_pcm_running 1
check_call_count cspm_stop_pcm_running __cspm_pcm_sw_reset 1
check_call_count __mt_i2c_transfer cpuhvfs_get_dvfsp_semaphore 2
check_call_count __mt_i2c_transfer cpuhvfs_release_dvfsp_semaphore 1
check_call_count __switch_cpuhvfs_on_off cpuhvfs_restart_dvfsp_running 1
check_call_count __switch_cpuhvfs_on_off cpuhvfs_stop_dvfsp_running 1
check_call_count _mt_cpufreq_syscore_resume cpuhvfs_dvfsp_resume 1

wrapper_disassembly=$(disassemble mt_i2c_transfer)
clock_enable_line=$(grep -n '<mt_i2c_clock_enable>' <<<"$wrapper_disassembly" | cut -d: -f1)
transfer_line=$(grep -n '<__mt_i2c_transfer>' <<<"$wrapper_disassembly" | cut -d: -f1)
clock_disable_line=$(grep -n '<mt_i2c_clock_disable>' <<<"$wrapper_disassembly" | cut -d: -f1)

if [[ -z $clock_enable_line || -z $transfer_line || -z $clock_disable_line ]] ||
	(( clock_enable_line >= transfer_line || transfer_line >= clock_disable_line )); then
	echo "outer I2C clock/transfer ordering mismatch" >&2
	exit 1
fi

echo "outer_order=clock-enable:$clock_enable_line,transfer:$transfer_line,clock-disable:$clock_disable_line"
echo "result=PASS"
