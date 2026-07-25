#!/usr/bin/env perl

use strict;
use warnings;

use POSIX qw(WNOHANG _exit);
use Time::HiRes qw(CLOCK_MONOTONIC clock_gettime sleep);

sub usage_error {
	my ($message) = @_;
	print STDERR "error: $message\n";
	exit 2;
}

@ARGV >= 3 or usage_error('usage: bounded-exec.pl SECONDS -- COMMAND [ARG ...]');
my $timeout = shift @ARGV;
$timeout =~ /\A[1-9][0-9]*\z/ or usage_error('SECONDS must be a positive integer');
shift(@ARGV) eq '--' or usage_error('missing -- before COMMAND');
@ARGV or usage_error('COMMAND is required');

my $child = fork();
defined $child or usage_error('fork failed');
if ($child == 0) {
	exec { $ARGV[0] } @ARGV or do {
		print STDERR "error: bounded child exec failed\n";
		_exit(127);
	};
}

my $deadline = clock_gettime(CLOCK_MONOTONIC) + $timeout;
my $status;
while (1) {
	my $waited = waitpid($child, WNOHANG);
	if ($waited == $child) {
		$status = $?;
		last;
	}
	$waited == 0 or usage_error('waitpid failed');

	my $remaining = $deadline - clock_gettime(CLOCK_MONOTONIC);
	if ($remaining <= 0) {
		# The unreaped child still owns this PID, so this signal cannot target
		# a recycled or unrelated process.  Do not signal a process group.
		kill 'KILL', $child;
		waitpid($child, 0);
		exit 124;
	}
	sleep($remaining < 0.02 ? $remaining : 0.02);
}

if (($status & 127) != 0) {
	exit(128 + ($status & 127));
}
exit($status >> 8);
