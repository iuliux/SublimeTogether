'''
Together Sublime-Text-2 plugin - Collaborative editing
'''

__license__ = 'MIT http://www.opensource.org/licenses/mit-license.php'
__author__ = "Iulius Curt <iulius.curt@gmail.com>, http://iuliux.ro"

import sys

import sublime
import sublime_plugin

import time
import threading
from threading import Thread, Lock


st_version = 2 if sys.version_info < (3,) else 3

if st_version == 3:
    from .lib.communication import *
    from .lib.changerequests import *
    from .message_monitor import *
elif st_version == 2:
    from lib.communication import *
    from lib.changerequests import *
    from message_monitor import *


# Dict to keep track of view-session associations
sessions_by_view = {}

# Lock for regulating message sending to server
channel_lock = Lock()
count = 0

# Read settings
settings = sublime.load_settings(__name__ + '.sublime-settings')

# Create a global ConversationStarter
# (which generates request-response conversations)
try:
    conv_starter = ConversationStarter(settings.get('server_url'))
    print('ConversationStarter CREATED!')
except Exception:
    sublime.error_message("Can't establish the connection to server")


class Session(object):
    '''Structure specific for each session. Each pad has it's own session'''
    def __init__(self, view, pad):
        super(Session, self).__init__()
        global settings
        self.pad = pad
        self.author = settings.get('author')  # Read it from settings file
        self.cr_n = -1  # Change request number (logical clock)
        self.view = view
        self.active = False
        self.buffer = ''
        # Producers-Consumers queue
        self.msgmonitor = MessageProdConsMonitor()
        self.cr_consumer = ChangesConsumer(self.msgmonitor, self)
        self.remote_checker = UpdateCheckerThread(self)

    def initiate(self):
        conv = conv_starter.new(method='PUT', resource='')
        conv.send(self.pad)
        # Handle response
        code = EncodingHandler.resp_ttoc
        if conv.response_code == code['ok']:
            # Get the local copy of the pad
            bufferRegion = sublime.Region(0, self.view.size())
            self.buffer = self.view.substr(bufferRegion)

            # TODO: commit the current buffer

            self.active = True
        elif conv.response_code == code['pad_already_exists']:
            self.error = 'The name ' + self.pad + ' is already in use.' + \
                ' Please pick another name, or use <Join pad> command.'
        elif conv.response_code == code['generic_error']:
            self.error = 'Connection error.'
        else:
            self.error = 'Error.'

        if self.active:
            # Start the changes-consumer thread
            self.cr_consumer.start()
            print('Consumer thread started')
            self.remote_checker.start()
            print('RemoteChecker thread started')

    def join(self):
        # Check if pad exists
        conv = conv_starter.new(method='GET', resource='')
        conv.send(self.pad)
        # Handle response
        code = EncodingHandler.resp_ttoc
        if conv.response_code == code['yes']:
            # Good, proceed
            pass
        elif conv.response_code == code['no']:
            self.error = 'Pad "' + self.pad + '" does not exist. You may ' +\
                'start a new pad with this name with <Start pad> command.'
            return
        elif conv.response_code == code['generic_error']:
            self.error = 'Connection error.'
            return
        else:
            self.error = 'Error.'
            return

        # Send update request
        conv = conv_starter.new(method='GET', resource=self.pad)
        conv.send(self.cr_n)
        # Handle response
        if conv.response_code == code['ok']:
            # Activate session
            self.active = True
        elif conv.response_code == code['update_needed']:
            # Commit updates, then current change
            self.cr_n = int(conv.response_headers['new_cr_n'])
            # Apply list
            self._apply_crs(conv.response_data)
            # Activate session
            self.active = True
        elif conv.response_code == code['nan']:
            self.error = 'Error'
        elif conv.response_code == code['generic_error']:
            self.error = 'Connection error.'
        else:
            self.error = 'Error.'

        if self.active:
            # Start the changes-consumer thread
            self.cr_consumer.start()
            print('Consumer thread started')
            self.remote_checker.start()
            print('RemoteChecker thread started')

    def handle_change(self, cr):
        # Assign a number to this CR and increment current count
        cr.cr_n = self.cr_n
        # Send change request
        conv = conv_starter.new(method='PUT', resource=self.pad)
        global count
        channel_lock.acquire()  # One message at a time
        count += 1
        print('------------- SIMULTANEOUS THREADS:', count)
        print('         \---', threading.enumerate())
        channel_lock.release()

        msg_tuple = (MessageProdConsMonitor.COMMIT_MSG, conv, cr)
        self.msgmonitor.add(msg_tuple)

        channel_lock.acquire()
        count -= 1
        channel_lock.release()

    def handle_response(self, conv, cr):
        # Handle response
        code = EncodingHandler.resp_ttoc
        if conv.response_code == code['ok']:
            # Commit the change (if any)
            if cr:
                self.cr_n += 1
                new_buffer = cr.apply_over(self.buffer)
                if new_buffer:
                    self.buffer = new_buffer
            # Else, remote has no changes
        elif conv.response_code == code['update_needed']:
            # Commit updates, then current change (if any)
            self.cr_n = int(conv.response_headers['new_cr_n'])
            # Apply list
            self._apply_crs(conv.response_data)
        elif conv.response_code == code['generic_error']:
            self.error = 'Connection error! The pad may become inconsistent.'
        else:
            self.error = 'Error.'

    def check_remote(self):
        # Put an update request on the queue
        conv = conv_starter.new(method='GET', resource=self.pad)
        msg_tuple = (MessageProdConsMonitor.UPDATE_MSG, conv, self.cr_n)
        self.msgmonitor.add(msg_tuple)

    def _apply_crs(self, crs_list):
        crs_to_update = EncodingHandler.deserialize_list(crs_list)
        for c in crs_to_update:
            c_cr = ChangeRequest()
            c_cr.deserialize(c)
            self.buffer = c_cr.apply_over(self.buffer)
        self.update_view()

    def update_view(self):
        '''Update current buffer'''
        edit = self.view.begin_edit('tog_update')
        whole = sublime.Region(0, self.view.size())
        self.view.erase(edit, whole)
        self.view.insert(edit, 0, self.buffer)
        self.view.end_edit(edit)


class CaptureEditing(sublime_plugin.EventListener):
    '''Event listener to watch for changes in the local buffer'''
    def on_modified(self, view):
        if view.id() not in sessions_by_view:
            return
        i = 0
        for sel in view.sel():
            i += 1
            curr_line, _ = view.rowcol(sel.begin())

            # Get operation
            action, content, _ = view.command_history(0, False)
            if action == 'tog_update':
                # Sync update, do nothing
                return

            op = None
            value = ''
            pos = sel.begin()
            delta = 1
            if action == 'insert':
                pos -= 1
                # print('  INSERT: pos=<', pos, '> delta=<', 1, '> value=<', content['characters'][-1], '>')
                op = ChangeRequest.ADD_EDIT
                value = content['characters'][-1]
            elif action == 'left_delete' or action == 'right_delete':
                # print('  DELETE: pos=<', pos, '> delta=<', 1, '>')
                op = ChangeRequest.DEL_EDIT
            else:
                print('[!] Unrecognized action:', action)
                return

            cr = ChangeRequest(pos=pos,
                               delta=delta,
                               op=op,
                               value=value)

            thread = SyncThread(view.id(), cr)
            thread.start()
            ThreadProgress(thread, 'Synchronizing', '')

    def on_close(self, view):
        print('*Closed*')

    def on_new(self, view):
        print('*New*')

    def on_pre_save(self, view):
        print('*PreSave*')

    def on_activated(self, view):
        # print('*Activated*')
        pass

    def on_deactivated(self, view):
        # print('*Deactivated*')
        pass


class SyncThread(Thread):
    def __init__(self, view_id, cr):
        super(SyncThread, self).__init__(name='SyncThread')
        self.view_id = view_id
        self.cr = cr
        self.session = sessions_by_view[view_id]
        # Augments CR with author info
        self.cr.author = self.session.author

    def run(self):
        if self.session.active:
            self.session.handle_change(self.cr)
        else:
            self.result = False  # Notify ThreadProgress of failure
            sublime.error_message(self.session.error)


class StartPadCommand(sublime_plugin.WindowCommand):
    '''Command to initiate a new pad from current view'''

    def run(self):
        self.window.show_input_panel('Pad name',
                                     '',
                                     self.on_done,
                                     self.on_change,
                                     self.on_cancel)

    def on_done(self, input):
        '''Input panel handler - initiates a new pad with the specified name'''
        print('New Session created for', self.window.active_view().id())
        session = Session(self.window.active_view(), input)
        thread = StartPadThread(session)
        thread.start()
        ThreadProgress(thread, 'Creating the "' + input + '" pad', 'Pad successfully created')

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass


class StartPadThread(Thread):
    def __init__(self, session):
        super(StartPadThread, self).__init__(name='StartPadThread-'+session.pad)
        self.session = session

    def run(self):
        self.session.initiate()
        if self.session.active:
            sessions_by_view[self.session.view.id()] = self.session
        else:
            self.result = False  # Notify ThreadProgress of failure
            sublime.error_message(self.session.error)


class JoinPadCommand(sublime_plugin.WindowCommand):
    '''Command to join an existing pad from current view'''

    def run(self):
        self.window.show_input_panel('Pad name',
                                     '',
                                     self.on_done,
                                     self.on_change,
                                     self.on_cancel)

    def on_done(self, input):
        print('New Session (join) created for', self.window.active_view().id())
        session = Session(self.window.active_view(), input)
        thread = JoinPadThread(session)
        thread.start()
        ThreadProgress(thread, 'Joining the "' + input + '" pad', 'Join successful')

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass


class JoinPadThread(Thread):
    def __init__(self, session):
        super(JoinPadThread, self).__init__(name='JoinPadThread-'+session.pad)
        self.session = session

    def run(self):
        self.session.join()
        if self.session.active:
            sessions_by_view[self.session.view.id()] = self.session
        else:
            self.result = False  # Notify ThreadProgress of failure
            sublime.error_message(self.session.error)


class UpdateCheckerThread(Thread):
    def __init__(self, session):
        super(UpdateCheckerThread, self).__init__(
            name='UpdateCheckerThread-'+session.pad)
        self.session = session
        self._silent = False

    def run(self):
        while True:
            if self.session.active:
                self.session.check_remote()
                self._silent = False
            else:
                self.result = False  # Notify ThreadProgress of failure
                if not self._silent:
                    sublime.error_message(self.session.error)
                    self._silent = True
            time.sleep(15)


class ThreadProgress():
    '''
    Animates an indicator, [=   ], in the status area while a thread runs
    Copied from the PackageControl project
    @thread:
        The thread to track for activity
    @message:
        The message to display next to the activity indicator
    @success_message:
        The message to display once the thread is complete
    '''

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

        sublime.status_message('%s [%s=%s]' %
                               (self.message, ' ' * before, ' ' * after))

        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        i += self.addend

        sublime.set_timeout(lambda: self.run(i), 100)
