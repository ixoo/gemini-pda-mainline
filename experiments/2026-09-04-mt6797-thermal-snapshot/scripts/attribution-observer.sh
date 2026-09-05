# SPDX-License-Identifier: MIT
# shellcheck disable=SC2016 # Awk field expressions are intentionally literal.
# Function fragment inserted by the offline builder, never executed on its own.
attribution_observe()
{
	label=$1
	case "$label" in before) attempt=1;; during) attempt=2;; after) attempt=3;; *) frequency_reject snapshot-stage;; esac
	[ "$($BB cat "${SNAPSHOT}_status")" = "abi=1 attempts=$((attempt - 1)) limit=3" ] ||
		frequency_reject snapshot-pre-accounting
	observation=$($BB cat "$FREQUENCY_OBSERVER" 2>/dev/null) || frequency_reject "frequency-${label}"
	$BB printf 'frequency_%s=%s\n' "$label" "$observation"
	$BB printf '__THERMAL_ATTRIBUTION_%s_BEGIN__\n' "$label"
	snapshot_record=$($BB cat "$SNAPSHOT")
	snapshot_read_status=$?
	$BB printf '%s\n' "$snapshot_record"
	$BB printf '__THERMAL_ATTRIBUTION_%s_END__\n' "$label"
	[ "$snapshot_read_status" = 0 ] || frequency_reject snapshot-read
	[ "$($BB cat "${SNAPSHOT}_status")" = "abi=1 attempts=$attempt limit=3" ] ||
		frequency_reject snapshot-post-accounting
	temperature=$($BB printf '%s\n' "$snapshot_record" | $BB awk -v attempt="$attempt" '
	function field(token, key, a) {
		if (split(token,a,"=") != 2 || a[1] != key || a[2] !~ /^(0|[1-9][0-9]*)$/) {bad=1; return -1}
		return a[2]+0
	}
	NR==1 {
		if (NF!=10) bad=1
		if (field($1,"abi")!=1 || field($2,"attempt")!=attempt || field($3,"error")!=0 ||
		    field($4,"complete")!=1 || field($5,"count")!=7 || field($6,"valid_mask")!=127) bad=1
		winner=field($7,"winner"); reported=field($8,"maximum")
		start=field($9,"start_ns"); end=field($10,"end_ns")
		if (start<=0 || end<start) bad=1
		split("0 1 2 2 3 4 5",banks," "); split("0 3 1 2 1 1 1",sensors," ")
		next
	}
	{
		i=NR-1
		if (NF!=5 || i>7) bad=1
		if (field($1,"slot")!=i-1 || field($2,"bank")!=banks[i] || field($3,"sensor")!=sensors[i] || field($5,"valid")!=1) bad=1
		value=field($4,"temperature")
		if (value<0 || value>58500) bad=1
		if (i==1 || value>maximum) {maximum=value; first=i-1}
	}
	END {
		if (NR!=8 || reported!=maximum || winner!=first || bad) exit 3
		print maximum
	}') || frequency_reject snapshot-record-or-temperature
	$BB printf 'thermal_%s_millicelsius=%s\n' "$label" "$temperature"
	$BB printf 'snapshot_%s_attempt=%s\n' "$label" "$attempt"
}
