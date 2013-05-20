#!/usr/bin/perl -T

my %p;
%p = @ARGV; s/,\z// foreach values %p; # DEPLOYMENT SCRIPT EDITS THIS LINE

use feature 'say';
use warnings;
use strict;
use CGI::Minimal;
use DBIx::Simple;
use Digest::HMAC_MD5 'hmac_md5_hex';
use JSON::XS 'decode_json';

# --------------------------------------------------

my %cgi = do
   {my $x = new CGI::Minimal;
    map {$_ => $x->param($_)} $x->param};

unless ($ENV{REQUEST_METHOD} eq 'POST'
        and exists $cgi{hmac}
        and exists $cgi{json}
        and hmac_md5_hex($cgi{json}, $p{hmac_key}) eq $cgi{hmac})
   {say 'Status: 403 Forbidden';
    say 'Content-Type: text/plain; charset=utf-8';
    say '';
    say 'Access denied.';
    exit;}

my %r = %{decode_json $cgi{json}};

# --------------------------------------------------

eval

   {my $db = DBIx::Simple->connect("dbi:SQLite:dbname=$p{database_path}",
        '', '', {RaiseError => 1});

    $db->{sqlite_unicode} = 1;
    $db->{sqlite_see_if_its_a_number} = 1;
    $db->query('pragma foreign_keys = on');

    $db->begin;

    $db->insert('Subjects',
       {subject_id => $r{subject},
        email => $r{email},
        first_d8 => $r{first_d8},
        last_d8 => $r{last_d8}});
      # Since 'subject_id' has a 'unique' constraint, requests are
      # idempotent.
    my ($sn) = $db->select('Subjects', 'sn', {subject_id => $r{subject}})->flat;
    $db->update('Subjects',
        {checkin_code => (($sn << 16) | (substr(rand, 2) % (1 << 16)))},
          # This is a number that's unique for each subject but hard
          # to guess given the subject number.
        {sn => $sn});

    foreach (0 .. $#{$r{activities}})
       {$db->insert('Activities',
            {sn => $sn, actn => $_, activityname => $r{activities}[$_]});}

    $db->commit;};

# --------------------------------------------------

if ($@)
   {warn sprintf '%s: Brass receiver, subject "%s": %s',
        scalar(localtime),
        $r{subject},
        $@;
    say 'Status: 422 Unprocessable Entity';
    say 'Content-Type: text/plain; charset=utf-8';
    say '';
    say 'Bad request.';
    exit;}
else
   {say 'Content-Type: text/plain; charset=utf-8';
    say '';
    say 'Done.';}
