#!/usr/bin/env python
# encoding: UTF-8

from sys import argv
from datetime import date
import urllib, urllib2
import hmac, json
import wx
from wxPython.lib.dialogs import messageDialog
import schizoidpy
from schizoidpy import init_wx, box, wrapped_text
import commitments

par = dict(zip(argv[1::2], argv[2::2])) # DEPLOYMENT SCRIPT EDITS THIS LINE

o = schizoidpy.Task(
    enable_pyglet = False,
    button_radius = .12,
    okay_button_pos = (0, -.7))
o.save('task_version', par['task_version'])

small_dialog_width = 300

# ------------------------------------------------------------
# Subroutines
# ------------------------------------------------------------

def d8(d):
    return d.year * 10000  + d.month * 100 + d.day

def message(msg):
    messageDialog(message = msg, title = '', aStyle = wx.OK)

class EmailDialog(wx.Dialog):
    """Like textEntryDialog, but the text is wrapped and there is
    no "Cancel" button."""
    def __init__(self, prompt):
        wx.Dialog.__init__(self, None)
        self.input1 = wx.TextCtrl(self)
        #self.input.Bind(wx.EVT_CHAR, generic_keypress(self))
        self.input1.SetFocus()
        self.input2 = wx.TextCtrl(self)
        box(self, wx.VERTICAL,
            wx.Size(small_dialog_width, 10),
            (wrapped_text(self, prompt), 0, wx.ALIGN_CENTER_HORIZONTAL),
            wx.Size(0, 10),
            (self.input1, 0, wx.EXPAND),
            wx.Size(0, 5),
            (self.input2, 0, wx.EXPAND),
            wx.Size(0, 10),
            (wx.Button(self, wx.ID_OK), 0, wx.ALIGN_CENTER_HORIZONTAL)).Fit(self)

def stringInputDialog(prompt):
    d = StringInputDialog(prompt)
    d.CenterOnScreen(wx.BOTH)
    d.ShowModal()
    d.Destroy()
    return d.input.GetValue()

def server_send(subject, email, activity_names):
    'Send email addresses and activites to the server.'

    export_json = json.dumps(dict(
        subject = subject,
        email = email,
        first_d8 = d8(commitments.dateplus(date.today(), 1)),
        last_d8 = d8(commitments.dateplus(date.today(), commitments.checkin_range)),
        activities = activity_names))

    f = urllib2.urlopen(par['receiver_url'], data = urllib.urlencode(dict(
        hmac = hmac.new(par['hmac_key'], export_json).hexdigest(),
        json = export_json)))
    if par['debug']: print f.read()
    f.close()

# ------------------------------------------------------------
# Preliminaries
# ------------------------------------------------------------

# TODO: Check for a network connection first

if par['debug_serverside']:
    server_send('test1', par['debug_email'], ['Studying', 'Jogging', 'Eating'])
    exit()

init_wx()

if par['debug']:
    o.data['subject'] = 'test'
else:
    o.get_subject_id('Decision-Making')

o.start_clock()

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

with o.timestamps('email'):
    while True:
        dlg = EmailDialog("After you leave the lab, we'll communicate with you by email for the rest of the study.\n\nEnter your email address twice.")
        dlg.CenterOnScreen(wx.BOTH)
        dlg.ShowModal()
        dlg.Destroy()
        s = dlg.input1.GetValue().strip()
        if s != dlg.input2.GetValue().strip():
            message("The addresses you entered don't match.")
        elif ' ' in s:
            message("Spaces aren't allowed in email addresses.")
        elif '@' not in s:
            message('Your email address is missing an "@".')
        else:
            o.save('email', s)
            break

with o.timestamps('commitments'):
    o.save('commitments', commitments.get())

# ------------------------------------------------------------
# Done!
# ------------------------------------------------------------

server_send(data['subject'], data['email'],
    [d['name'] for d in data['commitments']['activities']])

o.done(par['output_path_fmt'].format(**o.data))

o.wait_screen(1,
    o.text(0, 0, 'Done!\n\nPlease let the experimenter know you are done.'))
