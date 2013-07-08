# encoding: UTF-8

from datetime import date
import re
import wx
import wx.lib.masked as masked
from wxPython.lib.dialogs import messageDialog
from schizoidpy import box, wrapped_text, okay, init_wx, SchizoidDlg
import operator; mcall = operator.methodcaller

# ---------------------------------------------------------------
# Public
# ---------------------------------------------------------------

checkin_range = 14
max_committed_hours = 8
max_activities = 5

def dateplus(d, n):
    return date.fromordinal(d.toordinal() + n)

def long_wrapped_text(parent, string, wrap = 300, font_size = 12):
    x = wx.StaticText(parent, -1, string)
    font = x.GetFont()
    font.SetPointSize(font_size)
    x.SetFont(font)
    x.Wrap(wrap)
    return x

def message(msg):
    messageDialog(message = msg, title = '', aStyle = wx.OK)

short_wrap_width = 100
def short_wrapped_text(parent, string, wrap = short_wrap_width, exact = False):
    x = wx.StaticText(parent, -1, string, size =
       (short_wrap_width if exact else -1, -1))
    x.Wrap(wrap)
    return x

def get_activities():
    """Ask the subject which activities they want to tell us
    their commitments about."""
    dlg = ActivityListDialog(
        """Over the next fourteen days (two weeks), are there any activities that you plan to spend certain amounts of time on on certain days? For example, perhaps you want to exercise for an hour tomorrow, or study for half an hour every day. List any such activities below (e.g., "Exercise", "Study history"). On the next screen, we'll ask how much time you intend to spend on each activity each day. When choosing what to write here, however:\n\n"""
        u'• Leave fields blank rather than writing "N/A" or the like.\n\n'
        u"• Don't include activities if you don't have plans for particular days. For example, don't list exercise if you plan to exercise five days a week but you haven't yet decided which days.\n\n"
        u"• Don't include activities you're obliged to do and don't especially want to accomplish. For example, you might spend an hour every day commuting, but you probably aren't interested in commuting for its own sake.\n\n"
        u"• Don't include sleep habits. We'll ask about those separately.\n\n")
    dlg.CenterOnScreen(wx.BOTH)
    while True:
        dlg.ShowModal()
        activities = [s[0].upper() + s[1:]
            for s in [x.GetValue().strip() for x in dlg.inputs] if s]
        if any(na_like(s) for s in activities):
            message('Leave fields blank rather than writing "N/A" or the like.')
        else:
            break
    dlg.Destroy()
    return activities

def get_commitments(activities):
    """Solicit the actual commitments for activity and day, as
    well as wakeup times."""
    activity_help_text = (
        '''Now tell us how much time you plan to spend on each activity on each day. Round your answers to the nearest 15 minutes. If you have no plans for a given day and activity, leave that cell of the grid set to "---".\n\n''')
    core_help_text = (
        '''Tell us what time you plan to wake up each day. If for a given day you don't plan to get up at a particular time (on a Saturday, for example), leave the hour set to "---".\n\n'''
        '''The "Notes" column is optional. Use it if there are special circumstances you'd like to mention (e.g., a class will be canceled, so you don't need to get up early).\n\n'''
        '''Press the "Help" button at the top of the window to see this message again.''')
    dlg = CommitmentDialog(activities = activities, help_text =
        activity_help_text + 'Please also ' + core_help_text[0].lower() + core_help_text[1:]
            if activities
            else core_help_text)
    dlg.CenterOnScreen(wx.BOTH)
    dlg.Show()
    dlg.help(None)
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

def choice(*a, **kw):
   x = wx.Choice(*a, **kw)
   x.SetSelection(0)
   return x

class ActivityListDialog(wx.Dialog):
    def __init__(self, prompt):
        wx.Dialog.__init__(self, None, style =
            wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX)

        panel = wx.Panel(self)
        fgs = wx.FlexGridSizer(cols = 2, vgap = 5, hgap = 5)
        self.inputs = []
        for i in range(max_activities):
            fgs.Add(wrapped_text(panel, 'Activity {}'.format(i + 1)),
                border = 10, flag = wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
            self.inputs.append(wx.TextCtrl(panel, size = (300, -1)))
            fgs.Add(self.inputs[-1])
        panel.SetSizer(fgs)

        pwrap = 500
        prompt = long_wrapped_text(self, prompt, wrap = pwrap)

        self.inputs[0].SetFocus()
        box(self, wx.VERTICAL,
            (prompt, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10),
            panel,
            wx.Size(0, 10),
            (okay(self), 0, wx.ALIGN_CENTER_HORIZONTAL)).Fit(self)

class CommitmentDialog(wx.Dialog):

    choices = (['---'] +
        ['{} h {} min'.format(h, m)
            for h in range(max_committed_hours) for m in (0, 15, 30, 45)][1:] +
        ["{} h 0 min".format(max_committed_hours)])

    def __init__(self, parent = None, title = '', activities = None, help_text = ''):
        wx.Dialog.__init__(self, parent, -1, title, wx.DefaultPosition, style =
            wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX)

        panel = wx.Panel(self)

        self.activities = [
            dict(name = x, fields = map(
                lambda _: choice(panel, -1, choices = self.choices),
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
            fgs.Add(short_wrapped_text(panel, act['name'], exact = True), 0, wx.ALIGN_CENTER)
        fgs.Add(short_wrapped_text(panel, 'Wake-up time'), 0, wx.ALIGN_BOTTOM)
        fgs.Add(short_wrapped_text(panel, 'Notes'), 0, wx.ALIGN_BOTTOM)
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
                h = choice(timepan, choices = ['---'] + map(str, range(1, 13))),
                m = choice(timepan, choices = ['%02d' % n for n in range(60)]),
                ampm = choice(timepan, choices = ['AM', 'PM'])))
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

        hbutton = wx.Button(self, wx.ID_HELP)
        self.help_text = help_text
        hbutton.Bind(wx.EVT_BUTTON, self.help)

        box(self, wx.VERTICAL,
            hbutton,
            panel,
            (okay(self), 0, wx.ALIGN_CENTER_HORIZONTAL)).Fit(self)

    def help(self, event):
        d = MyMessageDialog(title = 'Help', string = self.help_text)
        d.ShowModal()
        d.Destroy()

class MyMessageDialog(wx.Dialog):

    def __init__(self, parent = None, title = '', string = ''):
        wx.Dialog.__init__(self, parent, -1, title, wx.DefaultPosition)

        self.panel = wx.Panel(self)
        self.label = long_wrapped_text(self.panel, string, 500)
        box(self.panel, wx.HORIZONTAL,
            (self.label, 0, wx.LEFT | wx.RIGHT, 10))

        box(self, wx.VERTICAL,
            wx.Size(0, 10),
            self.panel,
            wx.Size(0, 10),
            (okay(self, True), 0, wx.ALIGN_CENTER_HORIZONTAL)).Fit(self)        

def na_like(s):
    s = ''.join(c.lower() for c in s if c.isalpha())
    return s in ('na', 'notapplicable', 'nil', 'no', 'noplan', 'noplans', 'nothing')

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
