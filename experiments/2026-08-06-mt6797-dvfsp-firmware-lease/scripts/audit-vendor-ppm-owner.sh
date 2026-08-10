#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Recover the vendor MT6797 PPM/cpufreq ownership boundary from Git objects.
# This is source-only: it never copies vendor code, reads device state, or
# writes a kernel/device artifact.

set -euo pipefail
export LC_ALL=C

VENDOR_TREE=${VENDOR_TREE:-"${HOME}/reverse-engineering/work/gemini-linux-kernel-3.18"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"

[[ -d "${VENDOR_TREE}/.git" ]] || die "vendor source tree is not a Git checkout: ${VENDOR_TREE}"

vendor_show() {
	local path=$1
	git -C "${VENDOR_TREE}" show "HEAD:${path}"
}

vendor_hash() {
	local path=$1
	vendor_show "${path}" | sha256sum | awk '{print $1}'
}

vendor_contains() {
	local path=$1
	local pattern=$2
	vendor_show "${path}" | rg -F -- "${pattern}" >/dev/null
}

ppm_header=drivers/misc/mediatek/base/power/ppm_v1/inc/mt_ppm_internal.h
ppm_api=drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_ppm_api.h
ppm_core=drivers/misc/mediatek/base/power/ppm_v1/src/mt_ppm_main.c
ppm_platform=drivers/misc/mediatek/base/power/ppm_v1/src/mach/mt6797/mt_ppm_platform.h
cpufreq=drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid.c
cpufreq_tables=drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c
eem=drivers/misc/mediatek/base/power/mt6797/mt_eem.c

for path in "${ppm_header}" "${ppm_api}" "${ppm_core}" "${ppm_platform}" \
	"${cpufreq}" "${cpufreq_tables}" "${eem}"; do
	git -C "${VENDOR_TREE}" cat-file -e "HEAD:${path}" \
		|| die "missing vendor source path: ${path}"
done

for pair in \
	"${ppm_header}|struct ppm_cluster_info" \
	"${ppm_header}|struct mutex lock" \
	"${ppm_header}|struct ppm_client_req client_req" \
	"${ppm_header}|struct ppm_cluster_info *cluster_info" \
	"${ppm_header}|ppm_lock(lock)" \
	"${ppm_header}|mutex_lock(lock)" \
	"${ppm_header}|mutex_unlock(lock)" \
	"${ppm_core}|struct ppm_data ppm_main_info" \
	"${ppm_core}|.lock = __MUTEX_INITIALIZER(ppm_main_info.lock)" \
	"${ppm_header}|ppm_main_info.cluster_info[id].dvfs_tbl" \
	"${ppm_core}|ppm_main_info.client_req" \
	"${ppm_api}|struct ppm_client_req" \
	"${ppm_api}|struct ppm_client_limit" \
	"${ppm_api}|mt_ppm_set_dvfs_table" \
	"${cpufreq}|DEFINE_SPINLOCK(dvfs_lock)" \
	"${cpufreq}|spin_lock(&dvfs_lock)" \
	"${cpufreq}|cspm_set_opp_limit" \
	"${cpufreq_tables}|CPU_DVFS_FREQ0_CCI_FY" \
	"${cpufreq_tables}|CPU_DVFS_FREQ15_CCI_FY" \
	"${eem}|DEFINE_SPINLOCK(eem_spinlock)" \
	"${eem}|DEFINE_MUTEX(record_mutex)" \
	"${eem}|mt_ptp_lock"; do
	path=${pair%%|*}
	pattern=${pair#*|}
	vendor_contains "${path}" "${pattern}" \
		|| die "source boundary not confirmed: ${path}: ${pattern}"
done

echo "claim=SOURCE_ONLY_MT6797_VENDOR_PPM_OWNER_BOUNDARY"
echo "vendor_tree=${VENDOR_TREE}"
echo "vendor_revision=$(git -C "${VENDOR_TREE}" rev-parse --verify HEAD)"
echo "ppm_header=${ppm_header};sha256=$(vendor_hash "${ppm_header}")"
echo "ppm_api=${ppm_api};sha256=$(vendor_hash "${ppm_api}")"
echo "ppm_core=${ppm_core};sha256=$(vendor_hash "${ppm_core}")"
echo "cpufreq=${cpufreq};sha256=$(vendor_hash "${cpufreq}")"
echo "cpufreq_tables=${cpufreq_tables};sha256=$(vendor_hash "${cpufreq_tables}")"
echo "eem=${eem};sha256=$(vendor_hash "${eem}")"
echo "ppm_policy_lock=ppm_main_info.lock;type=mutex;scope=ppm_data"
echo "ppm_cluster_table=ppm_main_info.cluster_info[].dvfs_tbl;clusters=3;entries=16;order=vendor-descending"
echo "ppm_policy_limits=ppm_main_info.client_req.cpu_limit[];fields=min_max_cpufreq_idx,min_max_cpu_core,advise_fields"
echo "ppm_table_registration=mt_ppm_set_dvfs_table;source=cpufreq_frequency_table"
echo "cci_frequency_table=cpu_dvfs[MT_CPU_DVFS_CCI].freq_tbl;fields=freq_tbl,freq_tbl_for_cpufreq;not_in_ppm_cluster_info"
echo "cpufreq_owner_lock=dvfs_lock;type=spinlock;scope=cspm_dvfsp_and_pll_state"
echo "eem_owner_locks=eem_spinlock;record_mutex;mt_ptp_lock;independent_from_ppm_and_dvfs"
echo "shared_generation_field=absent_in_vendor_ppm_cpufreq_eem_structs"
echo "single_transition_lock=absent;mainline_owner_must_introduce_one"
echo "required_bridge=ppm_policy+cci_rows+eem_ptp+live_vproc_vsram+clock_state+generation"
echo "vendor_code_copied=none"
echo "hardware_write=none"
echo "device_action=none"
echo "provider=none"
echo "cpu8_cpu9_admission=closed;boot_candidate=false"
