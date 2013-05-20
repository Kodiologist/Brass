# encoding: UTF-8

from datetime import date
import re
import wx
import wx.lib.masked as masked
from schizoidpy import box, wrapped_text, init_wx, SchizoidDlg
import operator; mcall = operator.methodcaller

# ---------------------------------------------------------------
# Public
# ---------------------------------------------------------------

checkin_range = 14
max_committed_hours = 8
max_activities = 5

def dateplus(d, n):
    return date.fromordinal(d.toordinal() + n)

def get():

    # Ask the subject which activities they want to tell us
    # their commitments about.
    dlg = SchizoidDlg(title = 'Entry')
    for i in range(max_activities):
        dlg.addField('Activity {}'.format(i + 1), width = 200)
    dlg.show()
    activities = [s[0].upper() + s[1:]
        for s in [s.strip() for s in dlg.data] if s]
    
    # Solicit the actual commitments for activity and day, as well
    # as wakeup times.
    dlg = CommitmentDialog(activities = activities)
    dlg.CenterOnScreen(wx.BOTH)
    dlg.ShowModal()
    dlg.Destroy()
    return dict(
        dates = map(str, dlg.dates),
        notes = [s if s else None
            for s in map(mcall('strip'), map(mcall('GetValue'), dlg.notes))],
        activities = [
            dict(name = act['name'], times = map(digest_activity_time, act['fields']))
            for act in dlg.activities],
        wakeups = map(digest_wakeup, dlg.wakeups))

# ---------------------------------------------------------------
# Private
# ---------------------------------------------------------------

class CommitmentDialog(wx.Dialog):

    choices = (['---'] +
        ['{} h {} min'.format(h, m)
            for h in range(max_committed_hours) for m in (0, 15, 30, 45)][1:] +
        ["{} h 0 min".format(max_committed_hours)])

    def __init__(self, parent = None, title = '', activities = None):
        wx.Dialog.__init__(self, parent, -1, title, wx.DefaultPosition)

        panel = wx.Panel(self)

        self.activities = [
            dict(name = x, fields = map(
                lambda _: wx.Choice(panel, -1, choices = self.choices),
                range(checkin_range)))
            for x in activities]
        rowlabel_cols = 3
           # Day of the week, day of the month, month
        extra_cols = 2
           # Wakeup times and notes
        fgs = wx.FlexGridSizer(
            cols = rowlabel_cols + len(self.activities) + extra_cols,
            vgap = 5, hgap = 5)
        # Add horizontal spaces to make all the response
        # columns the same width.
#        for _ in range(rowlabel_cols): fgs.Add(wx.Size(0, 0))
#        fgs.AddMany(len(self.activities) * [wx.Size(100, 0)])
#        fgs.Add(wx.Size(0, 0))
        # Add the column headers.
        for _ in range(rowlabel_cols): fgs.Add(wx.Size(0, 0))
        for act in self.activities:
            fgs.Add(wrapped_text(panel, act['name']), 0, wx.ALIGN_CENTER)
        fgs.Add(wrapped_text(panel, 'Wake-up time'))
        fgs.Add(wrapped_text(panel, 'Notes'))
        # Add the rows for each day.
        self.dates = []
        self.notes = []
        self.wakeups = []
        for row in range(checkin_range):
            # Date column
            d = dateplus(date.today(), row + 1)
            self.dates.append(d)
            fgs.Add(wrapped_text(panel, d.strftime("%a")), flag = wx.LEFT, border = 5)
            fgs.Add(wrapped_text(panel, str(d.day)), flag = wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT, border = 7)
            fgs.Add(wrapped_text(panel, d.strftime("%b")))
            # Activity columns
            for act in self.activities:
                fgs.Add(act['fields'][row], 0, wx.ALIGN_CENTER)
            # Wakeup-time column
            timepan = wx.Panel(panel)
            self.wakeups.append(dict(
                h = wx.Choice(timepan, choices = ['---'] + map(str, range(1, 13))),
                m = wx.Choice(timepan, choices = ['%02d' % n for n in range(60)]),
                ampm = wx.Choice(timepan, choices = ['AM', 'PM'])))
            fgs.Add(timepan)
            box(timepan, wx.HORIZONTAL,
                self.wakeups[-1]['h'],
                self.wakeups[-1]['m'],
                self.wakeups[-1]['ampm'])
            # Notes column
            self.notes.append(wx.TextCtrl(panel, size = (300, 25)))
            fgs.Add(self.notes[-1])
        # Add some trailing vertical space.
        fgs.Add(wx.Size(0, 5))
        panel.SetSizer(fgs)

        box(self, wx.VERTICAL,
            panel,
            (wx.Button(self, wx.ID_OK), 0, wx.ALIGN_CENTER_HORIZONTAL)).Fit(self)

def digest_wakeup(wakeup):
    h, m, ampm = wakeup['h'].GetStringSelection(), wakeup['m'].GetStringSelection(), wakeup['ampm'].GetStringSelection()
    if h == '---': return
    return (
       60 * (
           0  if h == '12' and ampm == 'AM' else
           12 if h == '12' and ampm == 'PM' else
           int(h) + (ampm == 'PM')) +
           int(m))

def digest_activity_time(atime):
    s = atime.GetStringSelection()
    if s == '---': return
    h, m = re.findall(r'\d+', s)
    return 60 * int(h) + int(m)
