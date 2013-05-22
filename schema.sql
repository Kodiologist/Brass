create table Subjects
   (sn                              integer primary key,
    subject_id        text          not null unique,
    email             text          not null,
    active            integer       not null
        check (active in (0, 1))
        default 1,
    opted_out         integer       not null
        check (opted_out in (0, 1))
        default 0
        check (not (opted_out and active)),
    checkin_code      integer       unique,
    first_d8          integer       not null,
    last_d8           integer       not null);

create table Activities
   (sn                integer       not null
        references Subjects(sn),
    actn              integer       not null,
    activityname      text          not null,
    primary key (sn, actn));

create table ActivityDurations
   (sn                integer       not null,
    d8                integer       not null,
    actn              integer       not null,
    minutes           integer,
    primary key (sn, d8, actn),
    foreign key (sn, actn) references Activities(sn, actn));

create table WakeupTimes
   (sn                integer       not null
        references Subjects(sn),
    d8                integer       not null,
    submitted_t       integer,
    primary key (sn, d8));

create table Notifications
   (sn                integer       not null
        references Subjects(sn),
    d8                integer       not null,
    notification_type integer       not null
        check (notification_type in (
            1,    -- Welcome message
            2,    -- First warning for a miss
            3)),  -- Kickout message for a second miss
    primary key (sn, d8));
