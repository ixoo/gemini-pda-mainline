# SPDX-License-Identifier: MIT
#
# Cost of the schedutil frequency changes on the A53 DVFS station (V12).
# Input: ftrace text with sched_switch (filtered to the sugov threads),
# clk_set_rate and regulator_set_voltage. A sugov kthread sleeps in S only
# while it has no work; it waits in D for I2C, locks and ramps. Each run
# from one S sleep to the next is reported as a "change": with work queued
# it can hold several frequency changes, so divide by stats/total_trans
# for per-change figures. Per thread: runs, wall and CPU time per run, PLL
# and rail sets per run, and CPU time as a share of one CPU.
# Use: awk -f v-switch-cost.awk trace

function hist_pct(t, p,   n, i, c) {
	n = nw[t] * p / 100
	for (i = 0; i <= NB; i++) { c += h[t, i]; if (c >= n) return (i + 1) * BUS }
	return (NB + 1) * BUS
}
BEGIN { BUS = 50; NB = 400 }
{
	ts = ""
	for (i = 1; i <= NF; i++) if ($i ~ /^[0-9]+\.[0-9]+:$/) { ts = substr($i, 1, length($i) - 1) + 0; e = $(i + 1); break }
	if ($0 ~ /LOST [0-9]+ EVENTS/) lost++
	if (ts == "") next
	if (first == "") first = ts
	last = ts
	if (e == "sched_switch:") {
		pc = ps = nc = ""
		for (j = i + 2; j <= NF; j++) {
			k = $j; v = $j; sub(/=.*/, "", k); sub(/^[^=]*=/, "", v)
			if (k == "prev_comm") pc = v
			else if (k == "prev_state") ps = v
			else if (k == "next_comm") nc = v
		}
		if (pc ~ /^sugov:/) {
			t = pc; T[t] = 1
			if (busy[t] && (t in runat)) { c = ts - runat[t]; cpu[t] += c; wcpu[t] += c; delete runat[t] }
			if (ps ~ /^S/) {
				if (busy[t]) {
					w = (ts - start[t]) * 1e6; nw[t]++; wall[t] += w
					if (w > wmax[t]) wmax[t] = w
					b = int(w / BUS); if (b > NB) b = NB; h[t, b]++
					c = wcpu[t] * 1e6; if (c > cmax[t]) cmax[t] = c
					busy[t] = 0
				}
				armed[t] = 1
			}
		}
		if (nc ~ /^sugov:/) {
			t = nc; T[t] = 1
			if (armed[t] && !busy[t]) { busy[t] = 1; start[t] = ts; wcpu[t] = 0 }
			if (busy[t]) runat[t] = ts
		}
		next
	}
	if (e == "clk_set_rate:" || e == "regulator_set_voltage:") {
		t = $1; sub(/-[0-9]+$/, "", t)
		if (!busy[t]) next
		if (e == "clk_set_rate:") nclk[t]++; else nreg[t]++
	}
}
END {
	span = last - first
	printf "trace %.3f s, lost-event lines %d\n", span, lost
	for (t in T) {
		if (!nw[t]) { printf "%s: no complete change\n", t; continue }
		printf "%s: changes %d (%.1f/s); wall us mean %.0f p50 %d p90 %d max %.0f; cpu us mean %.0f max %.0f; PLL sets/change %.2f; rail sets/change %.2f; cpu %.2f%% of one CPU\n", \
			t, nw[t], nw[t] / span, wall[t] / nw[t], hist_pct(t, 50), hist_pct(t, 90), wmax[t], \
			cpu[t] * 1e6 / nw[t], cmax[t], nclk[t] / nw[t], nreg[t] / nw[t], 100 * cpu[t] / span
	}
}
