#!/usr/bin/env python
# encoding: UTF-8

from sys import argv
from random import uniform, expovariate
from datetime import date
from time import time
import urllib, urllib2
import hmac, json
import wx
from wxPython.lib.dialogs import messageDialog
from psychopy.visual import Rect
import schizoidpy
from schizoidpy import init_wx, box, okay, wrapped_text
import commitments

par = dict(zip(argv[1::2], argv[2::2])) # DEPLOYMENT SCRIPT EDITS THIS LINE

o = schizoidpy.Task(
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
            (okay(self, True), 0, wx.ALIGN_CENTER_HORIZONTAL)).Fit(self)

def stringInputDialog(prompt):
    d = StringInputDialog(prompt)
    d.CenterOnScreen(wx.BOTH)
    d.ShowModal()
    d.Destroy()
    return d.input.GetValue()

def server_send(subject, email, activity_names):
    'Send email addresses and activites to the server.'

    export_json = json.dumps(dict(
        time = int(time()),
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

# Check for a network connection.
if not par['debug']:
    assert '<title>Example Domain</title>' in urllib2.urlopen('http://example.org').read()

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
# Get an email address and commitments
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

server_send(o.data['subject'], o.data['email'],
    [d['name'] for d in o.data['commitments']['activities']])

# ------------------------------------------------------------
# Administer econometric tests
# ------------------------------------------------------------

divider_bar = Rect(o.win,
    fillColor = 'black', lineColor = 'black',
    width = 1.5, height = .01)

dec_rate = 1 / 0.25
inc_rate = 1 / 0.523852201187
trials = 20

def econ_test(dkey_prefix, instructions, text_top, text_bottom):
    with o.dkey_prefix(('econ', dkey_prefix)):
        o.instructions('instructions', instructions)
        with o.showing(divider_bar):
            discount = .5
            for trial in range(trials):

                o.save(('discount', trial), discount)
                big = uniform(5, 95)
                small = big * discount
                big = round(big, 2)
                small = round(small, 2)
                if small <= .01:
                    small = .01
                if big <= small:
                    big = small + .01
                o.save(('big', trial), big)
                o.save(('small', trial), small)
                big = '${:.2f}'.format(big)
                small = '${:,.2f}'.format(small)

                o.wait_screen(.5)
                choice = o.keypress_screen(('took_big', trial),
                    dict(up = False, down = True),
                    o.text(0, .25, text_top(big, small)),
                    o.text(0, -.25, text_bottom(big, small)))

                v = discount / (1 - discount)
                if choice:
                    v *= 1 + expovariate(inc_rate)
                else:
                    v /= 1 + expovariate(dec_rate)
                discount = v / (v + 1)

econ_test('patience',
    'In this task, you will make a series of hypothetical choices.\n\n'
        'Each trial will present you with a hypothetical choice between two amounts of money delivered to you at a given time in the future. Press the up arrow key if you would prefer the upper option and the down arrow key if you would prefer the lower option.\n\n'
        'Even though these are completely hypothetical decisions, try your best to imagine what you would choose if you were really offered these choices.',
    text_top = lambda llr, ssr: '{} today'.format(ssr),
    text_bottom = lambda llr, ssr: '{} in one month'.format(llr))

econ_test('shifted_patience',
    'The next task is like the previous one, except the top option is delayed by one month and the bottom option is delayed by two months.',
    text_top = lambda llr, ssr: '{} in one month'.format(ssr),
    text_bottom = lambda llr, ssr: '{} in two months'.format(llr))

econ_test('risk_aversion',
    'In this task, you will choose between a gamble and a sure gain.\n\n'
        'The gamble has a a 95% chance of giving you money and a 5% chance of yielding nothing. The other option has a 100% chance of yielding the indicated amount.',
    text_top = lambda risky, sure: '{} (100% chance)'.format(sure),
    text_bottom = lambda risky, sure: '{} (95% chance) or\nnothing (5% chance)'.format(risky))

econ_test('loss_aversion',
    'In this task, you will choose whether or not to take a gamble.\n\n'
        'The gamble is equally likely to make you gain or lose money, but the amount to be gained and the amount to be lost may differ.',
    text_top = lambda gain, loss: 'Nothing (100% chance)',
    text_bottom = lambda gain, loss: 'Gain {} (50% chance) or\nlose {} (50% chance)'.format(gain, loss))

# ------------------------------------------------------------
# Administer questionnaires
# ------------------------------------------------------------

o.questionnaire_screen('cfc',
    'How characteristic of you are each of these statements?',
    scale_levels = ('Extremely\nuncharacteristic', 'Somewhat\nuncharacteristic', 'Uncertain', 'Somewhat\ncharacteristic', 'Extremely\ncharacteristic'),
    questions = [
        'I consider how things might be in the future, and try to influence those things with my day to day behavior.',
        'Often I engage in a particular behavior in order to achieve outcomes that may not result for many years.',
        'I only act to satisfy immediate concerns, figuring the future will take care of itself.',
        'My behavior is only influenced by the immediate (i.e., a matter of days or weeks) outcomes of my actions.',
        'My convenience is a big factor in the decisions I make or the actions I take.',
        'I am willing to sacrifice my immediate happiness or well-being in order to achieve future outcomes.',
        'I think it is important to take warnings about negative outcomes seriously even if the negative outcome will not occur for many years.',
        'I think it is more important to perform a behavior with important distant consequences than a behavior with less-important immediate consequences.',
        'I generally ignore warnings about possible future problems because I think the problems will be resolved before they reach crisis level.',
        'I think that sacrificing now is usually unnecessary since future outcomes can be dealt with at a later time.',
        'I only act to satisfy immediate concerns, figuring that I will take care of future problems that may occur at a later date.',
        'Since my day to day work has specific outcomes, it is more important to me than behavior that has distant outcomes.'])

o.questionnaire_screen('bfi',
    u'How much would you agree that you are someone who…?',
    scale_levels = ('Disagree\nstrongly', 'Disagree\na little', 'Neither agree\nnor disagree', 'Agree\na little', 'Agree\nstrongly'),
    questions = [
        'Is talkative',
        'Tends to find fault with others',
        'Does a thorough job',
        'Is depressed, blue',
        'Is original, comes up with new ideas',
        'Is reserved',
        'Is helpful and unselfish with others',
        'Can be somewhat careless',
        'Is relaxed, handles stress well',
        'Is curious about many different things',
        'Is full of energy',
        'Starts quarrels with others',
        'Is a reliable worker',
        'Can be tense',
        'Is ingenious, a deep thinker',
        'Generates a lot of enthusiasm',
        'Has a forgiving nature',
        'Tends to be disorganized',
        'Worries a lot',
        'Has an active imagination',
        'Tends to be quiet',
        'Is generally trusting',
        'Tends to be lazy',
        'Is emotionally stable, not easily upset',
        'Is inventive',
        'Has an assertive personality',
        'Can be cold and aloof',
        'Perseveres until the task is finished',
        'Can be moody',
        'Values artistic, aesthetic experiences',
        'Is sometimes shy, inhibited',
        'Is considerate and kind to almost everyone',
        'Does things efficiently',
        'Remains calm in tense situations',
        'Prefers work that is routine',
        'Is outgoing, sociable',
        'Is sometimes rude to others',
        'Makes plans and follows through with them',
        'Gets nervous easily',
        'Likes to reflect, play with ideas',
        'Has few artistic interests',
        'Likes to cooperate with others',
        'Is easily distracted',
        'Is sophisticated in art, music, or literature'])

# ------------------------------------------------------------
# Done!
# ------------------------------------------------------------

o.done(par['output_path_fmt'].format(**o.data))

o.wait_screen(1,
    o.text(0, 0, 'Done!\n\nPlease let the experimenter know you are done.'))
