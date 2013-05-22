#!/usr/bin/perl

my %p;
%p = @ARGV; s/,\z// foreach values %p; # DEPLOYMENT SCRIPT EDITS THIS LINE

use feature 'say';
use warnings;
use strict;
use Mail::Sender; $Mail::Sender::NO_X_MAILER = 1;
use JSON::XS;
use File::Slurp 'read_file';
use DBIx::Simple;
use Date::Simple 'today';

# ---------------------------------------------------------------

use constant NOTIFICATION_TYPE_WELCOME => 1;
use constant NOTIFICATION_TYPE_FIRSTWARNING => 2;
use constant NOTIFICATION_TYPE_KICKOUT => 3;

my $welcome_fmt = do {local $/; <DATA>};
my $today = today->as_d8;

my $sender;
sub email
   {$sender ||= Mail::Sender->new({on_errors => 'die',
       %{decode_json read_file $p{sender_config_json_path}}});
    my $h = {@_};
    say STDERR sprintf '%s: Brass notifier: Sending: %s',
        scalar(localtime),
        encode_json($h);
    $h->{msg} .= "\n\n---\nThis is an automated message. However, you can reply to it to write to the experimenter.";
    $sender->MailMsg($h);}

sub notify;

# ---------------------------------------------------------------

my $db = DBIx::Simple->connect("dbi:SQLite:dbname=$p{database_path}",
       '', '', {RaiseError => 1});
$db->{sqlite_unicode} = 1;
$db->{sqlite_see_if_its_a_number} = 1;
$db->query('pragma foreign_keys = on');

foreach ($db->query('select * from
        (select sn, email, checkin_code, first_d8, last_d8 from Subjects where
            sn in (select sn from Subjects where active
               except
               select sn from Notifications where d8 = ?))
        left natural join
        (select sn, max(d8) as prev_wakeup_d8
            from WakeupTimes where submitted_t not null group by sn)',
        $today)->hashes)
   {my %s = %$_;
    *notify = sub
       {my ($type, $subject, $msg) = @_;
        email to => $s{email}, subject => $subject, msg => $msg;
        $db->insert('Notifications', {sn => $s{sn}, d8 => $today,
            notification_type => $type})};
    if ($s{first_d8} > $today)
       {notify NOTIFICATION_TYPE_WELCOME,
            'Decision-Making and Habits',
            sprintf $welcome_fmt, sprintf $p{checkin_url_fmt}, $s{checkin_code};}
    elsif (!defined $s{prev_wakeup_d8} or $s{prev_wakeup_d8} < $today)
       {# Mark today as a missed day.
        $db->insert('WakeupTimes',
           {sn => $s{sn},
            d8 => $today,
            submitted_t => undef});
        # Get the subject's number of misses so far.
        my ($misses) = $db->select('WakeupTimes', 'count(*)',
           {sn => $s{sn},
            submitted_t => undef})->flat;
        # Kick the subject out of the study, or just give them a
        # warning.
        if ($misses == 1)
           {if ($today == $s{last_d8})
               {$db->update('Subjects', {active => 0}, {sn => $s{sn}});
                notify NOTIFICATION_TYPE_FIRSTWARNING,
                    'Decision-Making and Habits is complete',
                    q(You seem to have forgotten to check in for the Decision-Making and Habits study today. No worries, though: it was the last day anyway. You'll receive full credit.);}
            else
               {notify NOTIFICATION_TYPE_FIRSTWARNING,
                    'Did you forget to check in today?',
                    q(You seem to have forgotten to check in for the Decision-Making and Habits study today. That's okay, but if you forget again, you'll be ejected from the study.);}}
        else # $misses > 1
           {$db->update('Subjects', {active => 0}, {sn => $s{sn}});
            notify NOTIFICATION_TYPE_KICKOUT,
                'Did you forget to check in today?',
                q(You seem to have forgotten to check in for the Decision-Making and Habits study today. That's the second time, so I'm afraid you're out of the study. Sorry. You'll still receive credit for the parts of the study you've completed.);}}}

__DATA__
Welcome to the Decision-Making and Habits study. Each day, immediately after you wake up, go to

%s

and submit the form.

Bookmark this page. You can help yourself remember to check in by loading up the page on your phone or computer before going to bed each night. Or, you can set up email reminders by sending an email to every2am@followupthen.com or by making events on Google Calendar. Google Calendar also has SMS reminders.
