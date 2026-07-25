#!/usr/bin/env perl

use strict;
use warnings;

use Errno qw(EINTR);
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

my $received_signal = 0;
$SIG{HUP} = sub { $received_signal = 1; };
$SIG{INT} = sub { $received_signal = 2; };
$SIG{PIPE} = sub { $received_signal = 13; };
$SIG{TERM} = sub { $received_signal = 15; };

my $child = fork();
defined $child or usage_error('fork failed');
if ($child == 0) {
	exec { $ARGV[0] } @ARGV or do {
		print STDERR "error: bounded child exec failed\n";
		_exit(127);
	};
}

sub waitpid_retry {
	my ($options) = @_;
	while (1) {
		my $waited = waitpid($child, $options);
		return $waited if $waited >= 0;
		next if $! == EINTR;
		usage_error('waitpid failed');
	}
}

sub terminate_exact_child {
	my ($exit_status) = @_;
	my $waited = waitpid_retry(WNOHANG);
	if ($waited == 0) {
		kill 'TERM', $child;
		my $grace_deadline = clock_gettime(CLOCK_MONOTONIC) + 2;
		while (clock_gettime(CLOCK_MONOTONIC) < $grace_deadline) {
			$waited = waitpid_retry(WNOHANG);
			last if $waited == $child;
			sleep(0.02);
		}
		if ($waited == 0) {
			kill 'KILL', $child;
			waitpid_retry(0);
		}
	}
	exit $exit_status;
}

my $deadline = clock_gettime(CLOCK_MONOTONIC) + $timeout;
my $status;
while (1) {
	if ($received_signal) {
		terminate_exact_child(128 + $received_signal);
	}
	my $waited = waitpid_retry(WNOHANG);
	if ($waited == $child) {
		$status = $?;
		last;
	}
	my $remaining = $deadline - clock_gettime(CLOCK_MONOTONIC);
	if ($remaining <= 0) {
		terminate_exact_child(124);
	}
	sleep($remaining < 0.02 ? $remaining : 0.02);
}

if (($status & 127) != 0) {
	exit(128 + ($status & 127));
}
exit($status >> 8);
