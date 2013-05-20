#!/usr/bin/perl -T

my %p;
%p = @ARGV; s/,\z// foreach values %p; # DEPLOYMENT SCRIPT EDITS THIS LINE

use feature 'say';
use strict;
use CGI::Minimal;
use HTML::Entities 'encode_entities';
use DBIx::Simple;
use Date::Simple 'today';

# ---------------------------------------------------------------

my $time_loaded = time;
my $max_activity_hours = 24;
my @duration_choices =
   ((map {my $h = $_; map {"$h h $_ min"} 0, 15, 30, 45}
          0 .. $max_activity_hours - 1),
    "$max_activity_hours h 0 min");

sub fail
   {die @_, "\n"}

my %cgi = do
   {my $x = new CGI::Minimal;
    map {$_ => $x->param($_)} $x->param};

my $checkin_code = $ENV{PATH_INFO} =~ m!\A/(\d+)\z!
  ? $1
  : 0;

# ---------------------------------------------------------------

my $db = DBIx::Simple->connect("dbi:SQLite:dbname=$p{database_path}",
       '', '', {RaiseError => 1});
$db->{sqlite_unicode} = 1;
$db->{sqlite_see_if_its_a_number} = 1;
$db->query('pragma foreign_keys = on');

local $@;
eval
   {my ($sn, $active, $last_d8) = $db->select('Subjects', ['sn', 'active', 'last_d8'],
        {checkin_code => $checkin_code})->flat;
    $sn or fail "Invalid checkin code $checkin_code.";
    $active or fail 'You are no longer participating in this study.';

    my @activities = $db->select('Activities', 
        'activityname',
        {sn => $sn},
        'actn')->flat;

    say 'Content-Type: text/html; charset=utf-8

    <!DOCTYPE html>
    <html lang="en-US">
    <head><meta charset="UTF-8"><title>Wakeup checkin page</title></head>
    <body>
    <h1 style="text-align: center">Wakeup checkin page</h1>';

    if ($ENV{REQUEST_METHOD} eq 'POST' and $cgi{submitted})
       {my $done = 0;
        local $@;
        eval
           {# We could stop subjects from checking in before
            # they're supposed to ('first_d8'), but why bother?
            my @t = $db->select('WakeupTimes', 'submitted_t',
                   {sn => $sn,
                    d8 => today->as_d8})->flat;
            @t and fail(defined $t[0]
              ? 'It looks like you already checked in today.'
              : q(It's too late to check in for today. Sorry.));
            $db->begin;
            $db->insert('WakeupTimes',
               {sn => $sn,
                d8 => today->as_d8,
                submitted_t => $time_loaded});
            foreach my $actn (0 .. $#activities)
               {my $duration = $cgi{"activity$actn"}
                    or fail "Missing duration for activity $actn.";
                grep {$duration eq $_} @duration_choices
                    or fail "Bad duration for activity $actn.";
                $duration =~ /\A(\d+) h (\d+) min\z/
                    or fail 'Match failed.';
                $db->insert('ActivityDurations',
                   {sn => $sn,
                    d8 => (today() - 1)->as_d8,
                    actn => $actn,
                    minutes => $1 * 60 + $2});}
            if (today->as_d8 == $last_d8)
               {$db->update('Subjects', {active => 0}, {sn => $sn});
                $done = 1;}
            $db->commit;};
        say sprintf '<div style="%s"><span style="%s">%s</span></div>',
            'text-align: center',
            'padding: .25em .5em; background-color: #ff8;',
            encode_entities($@ || 'Checkin succeeded.' . ($done
              ? q( Congratulations; you've completed this study.)
              : ''));}

    say '<p>Submit this form immediately upon waking up each day. (You can fill it out after you wake up or before you go to bed the day before.)</p>';

    say sprintf '<form method="POST" action="%s">',
        encode_entities sprintf $p{checkin_url_fmt}, $checkin_code;

    say sprintf '<p>%s</p>', join '<br>', map
       {sprintf "<label>%s: \n<select name='activity$_'>%s</select>\n</label>",
            encode_entities($activities[$_]),
            join "\n",
               "<option>$duration_choices[0]</option>",
               map {"<option>$_</option>"} @duration_choices[1 .. $#duration_choices]}
       0 .. $#activities;

    say '<p><input type="submit" name="submitted" value="Submit"></p></form>';

    say "\n\n</body></html>";};

if ($@)
   {warn sprintf '%s: Brass checkin: %s',
        scalar(localtime),
        $@;
    say 'Status: 422 Unprocessable Entity';
    say 'Content-Type: text/plain; charset=utf-8';
    say '';
    say encode_entities $@;
    exit;}
