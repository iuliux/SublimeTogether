'''
Together - Collaborative editing

@author: Iulius Curt <iulius.curt@gmail.com>, http://iuliux.ro
@license: MIT (http://www.opensource.org/licenses/mit-license.php)
'''

import sublime
import sublime_plugin


class CaptureEditing(sublime_plugin.EventListener):

    def on_modified(self, view):
        i = 0
        for sel in view.sel():
            print '>>> SELECTION NUMBER', i
            i += 1
            curr_line, _ = view.rowcol(sel.begin())
            print 'Curr line', curr_line
            print 'View ID', view.id()
            print 'Sel.begin', sel.begin()
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
