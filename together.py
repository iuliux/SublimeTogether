'''
Together Sublime-Text-2 plugin - Collaborative editing
'''

__license__ = 'MIT http://www.opensource.org/licenses/mit-license.php'
__author__ = "Iulius Curt <iulius.curt@gmail.com>, http://iuliux.ro"

import sublime
import sublime_plugin

import time
from threading import Thread

from lib.communication import *
from lib.changerequests import *


sessions_by_view = {}

try:
    conv_starter = ConversationStarter("http://localhost:8000")
    print 'ConversationStarter CREATED!'
except ConnectionError:
    sublime.error_message("Can't establish the connection to server")


class Session(object):
    """Structure specific for each session. Each pad has it's own session"""
    def __init__(self, view_id, pad):
        super(Session, self).__init__()
        self.pad = pad
        self.view_id = view_id
        self.active = False

    def initiate(self):
        conv = conv_starter.new(method='PUT', resource='')
        conv.send(self.pad)
        code = EncodingHandler.resp_ttoc
        if conv.response_code == code['ok']:
            self.active = True
        elif conv.response_code == code['pad_already_exists']:
            self.error = 'The name '+self.pad+' is already in use.'+\
                ' Please pick another name, or use <Connect to> command.'
        elif conv.response_code == code['generic_error']:
            self.error = 'Connection error.'
        else:
            self.error = 'Error.'


class CaptureEditing(sublime_plugin.EventListener):

    def on_modified(self, view):
        if view.id() not in sessions_by_view:
            return

        # SyncThread().start()
        i = 0
        for sel in view.sel():
            print '>>> SELECTION NUMBER', i
            i += 1
            curr_line, _ = view.rowcol(sel.begin())
            # print 'Curr line', curr_line
            # print 'View ID', view.id()
            # print 'Sel.begin', sel.begin()
            pos = sel.begin()

            # Get operation
            action, content, _ = view.command_history(0, False)

            # print 'Hist [[', action, ' -> ', content, ']]'
            if action == 'insert':
                print '  INSERT: pos=<', pos - 1, '> delta=<', 1, '> value=<', content['characters'][-1], '>'
            elif action == 'left_delete' or action == 'right_delete':
                print '  DELETE: pos=<', pos, '> delta=<', 1, '>'
            # https://github.com/nlloyd/SubliminalCollaborator/blob/master/commands.py#L486

    def on_close(self, view):
        print '*Closed*'

    def on_new(self, view):
        print '*New*'

    def on_pre_save(self, view):
        print '*PreSave*'

    def on_activated(self, view):
        print '*Activated*'

    def on_deactivated(self, view):
        print '*Deactivated*'


class SyncThread(Thread):
    def __init__(self):
        super(SyncThread, self).__init__()

    def run(self):
        print 'BEFORE >>>'
        time.sleep(2)
        print '<<< AFTER'
        sublime.error_message('error')


class StartPadCommand(sublime_plugin.WindowCommand):
    """Command to initiate a new pad from current view"""

    def run(self):
        self.window.show_input_panel('Pad name', '',
            self.on_done, self.on_change, self.on_cancel)

    def on_done(self, input):
        """
        Input panel handler - initiates a new pad with the specified name
        """
        print 'New Session created for', self.window.active_view().id()
        session = Session(self.window.active_view().id(), input)
        thread = StartPadThread(session)
        thread.start()
        ThreadProgress(thread, 'Creating the "'+input+'" pad', 'Pad successfully created')

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass


class StartPadThread(Thread):
    def __init__(self, session):
        super(StartPadThread, self).__init__()
        self.session = session

    def run(self):
        self.session.initiate()
        if self.session.active:
            sessions_by_view[self.session.view_id] = self.session
        else:
            sublime.error_message(self.session.error)


class ThreadProgress():
    """
    Animates an indicator, [=   ], in the status area while a thread runs
    Copied from the PackageControl project
    @thread:
        The thread to track for activity
    @message:
        The message to display next to the activity indicator
    @success_message:
        The message to display once the thread is complete
    """

    def __init__(self, thread, message, success_message):
        self.thread = thread
        self.message = message
        self.success_message = success_message
        self.addend = 1
        self.size = 8
        sublime.set_timeout(lambda: self.run(0), 100)

    def run(self, i):
        if not self.thread.is_alive():
            if hasattr(self.thread, 'result') and not self.thread.result:
                sublime.status_message('')
                return
            sublime.status_message(self.success_message)
            return

        before = i % self.size
        after = (self.size - 1) - before

        sublime.status_message('%s [%s=%s]' % \
            (self.message, ' ' * before, ' ' * after))

        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        i += self.addend

        sublime.set_timeout(lambda: self.run(i), 100)
