# SPDX-License-Identifier: MIT
#
# Ordering check for the A53 DVFS schedutil phases (V7 load, V8, V9).
# Input: ftrace text with clk_set_rate{,_complete} and
# regulator_set_voltage{,_complete}, starting with a "seed" trace_marker line
# written while the rails and clocks were steady, ending with an "end" marker.
#
# While a change is in flight, a clock counts at the higher of its old and new
# rate and a rail at the lower of its old and requested voltage. At every
# event the check requires VPROC1 at or above the table voltage of each
# cluster and CCI PLL rate, and VSRAM_L at or above both VPROC1 and 1100 mV.
# Use: awk [-v raw=FILE] -f v-trace-check.awk trace   (exit 1 on a violation)

function tab(k, hz,   mhz, n, i, p, d, a) {
	mhz = hz / 1000000
	n = split(T[k], a, " ")
	for (i = 1; i < n; i += 2) {
		p = a[i]; d = mhz - p; if (d < 0) d = -d
		if (d * 200 <= p) return a[i + 1] * 1000
	}
	return -1
}
function lo(r) { return (r in req) ? (req[r] < v[r] ? req[r] : v[r]) : v[r] }
function hi(r) { return (r in req) ? (req[r] > v[r] ? req[r] : v[r]) : v[r] }
function bad(msg) {
	nbad++
	if (nbad <= 20) print "VIOLATION " ts ": " msg
}
function check(   k, need, t, eff, what) {
	if (!seeded) return
	need = 0; what = ""
	for (k in K) {
		eff = (k in nr) ? (nr[k] > rate[k] ? nr[k] : rate[k]) : rate[k]
		t = tab(k, eff)
		if (t < 0) { bad(k " at " eff " Hz, not a table point"); continue }
		if (t > need) need = t
		what = what " " k "=" eff
	}
	if (lo("vproc1") < need) bad("VPROC1 " lo("vproc1") " uV below " need " for" what)
	if (lo("vsram_l") < hi("vproc1")) bad("VSRAM_L " lo("vsram_l") " uV below VPROC1 " hi("vproc1"))
	if (lo("vsram_l") < 1100000) bad("VSRAM_L " lo("vsram_l") " uV below 1100000")
}
BEGIN {
	T["ll"] = "1547 1200 1495 1200 1443 1200 1391 1180 1339 1160 1274 1140 1222 1120 1118 1070 1014 1040 897 1000 806 970 715 940 624 900 481 870 338 860 221 840"
	T["l"] = "2002 1200 1950 1200 1885 1190 1820 1170 1755 1160 1703 1130 1625 1110 1495 1070 1352 1040 1209 1000 1092 970 962 940 832 900 650 860 468 860 325 840"
	T["cci"] = "988 1200 975 1200 936 1200 910 1190 884 1170 845 1150 819 1140 754 1100 676 1060 611 1020 533 970 481 940 416 910 325 890 234 860"
	C["mcu-armpll-ll"] = "ll"; C["mcu-armpll-l"] = "l"; C["mcu-armpll-cci"] = "cci"
	K["ll"] = 1; K["l"] = 1; K["cci"] = 1
}
{
	if (raw != "") print > raw
	ts = ""
	for (i = 1; i <= NF; i++) if ($i ~ /^[0-9]+\.[0-9]+:$/) { ts = substr($i, 1, length($i) - 1); e = $(i + 1); break }
	if ($0 ~ /LOST [0-9]+ EVENTS/) { bad("trace lost events: " $0); next }
	if (ts == "") next
	nev++
	if (e == "tracing_mark_write:") {
		if ($(i + 2) == "end") { ended = 1; exit }
		if ($(i + 2) != "seed") next
		for (j = i + 3; j <= NF; j++) {
			split($j, kv, "=")
			if (kv[1] in K) rate[kv[1]] = kv[2] + 0; else v[kv[1]] = kv[2] + 0
		}
		seeded = 1
		for (k in K) if (!(k in rate) || rate[k] <= 0) { bad("seed has no rate for " k); seeded = 0 }
		if (!(v["vproc1"] > 0 && v["vsram_l"] > 0)) { bad("seed has no rail voltages"); seeded = 0 }
		check(); next
	}
	if (e == "clk_set_rate:" || e == "clk_set_rate_complete:") {
		if (!($(i + 2) in C)) next
		k = C[$(i + 2)]; r = $(i + 3) + 0
		if (!seeded) { pre++; next }
		if (e == "clk_set_rate:") {
			nr[k] = r
			if (tab(k, r) < 0) bad(k " set to " r " Hz, not a table point")
			if (r > rate[k]) up[k]++; else if (r < rate[k]) down[k]++
		} else { rate[k] = r; delete nr[k] }
		check(); next
	}
	if (e == "regulator_set_voltage:" || e == "regulator_set_voltage_complete:") {
		n = $(i + 2); sub(/^name=/, "", n); sub(/,$/, "", n)
		if (n != "vproc1" && n != "vsram_l") next
		if (!seeded) { pre++; next }
		if (e == "regulator_set_voltage:") { r = $(i + 3); sub(/^\(/, "", r); sub(/-.*/, "", r); req[n] = r + 0; nset[n]++ }
		else { r = $(i + 3); sub(/^val=/, "", r); v[n] = r + 0; delete req[n] }
		check(); next
	}
}
END {
	if (!seeded) bad("no seed marker")
	if (!ended) bad("no end marker")
	if (pre) bad(pre " clock or rail events before the seed")
	printf "trace events %d; ll up %d down %d; l up %d down %d; cci up %d down %d; vproc1 sets %d; vsram_l sets %d; violations %d\n", \
		nev, up["ll"], down["ll"], up["l"], down["l"], up["cci"], down["cci"], nset["vproc1"], nset["vsram_l"], nbad
	exit (nbad > 0)
}
