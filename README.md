Sublime Together - collaborative editing
========================================

About this plugin
-----------------

The client side of the Together collaborative editing system.

It's purpose is to enable real-time collaborative coding in a centralized
fashion. This is nice because there is no need for getting the address of the
owner of the file, you can still work on some file even if the owner is not
online. Configs need to be set only the first time.


Current status
--------------

This plugin is still in a state of infancy, but it's on the right track. The
current blocker is the bad implementation choice of the server which must be
changed.

There are a lot to be implemented or fixed in this plugin, like handling pads
after a large number of commits, undo-redo handling and much more, so any
contribution is highly appreciated.


Usage
-----

First, the address of the server must be configured in the configurations file,
then restart Sublime. This must be done only on the first run.

`Ctrl`+`Shift`+`P` and type 'Together'. Two options are available:

* `Start new pad` - to publish the current buffer to a pad on the server
* `Join pad` - to connect the current buffer to a remote pad


Implementation details
----------------------

The only entity this client communicates with is the central server. In the
current implementation of the server, the protocol is over an HTTP RESTful
interface, but this must change.

The action happens on multiple threads, beside the Sublime interface thread.
*(TODO: thread-pools)* When an edit is made to the local buffer, a new thread
takes care of creating a message and pushing it in a message queue, as producer.
The consumer is a thread that pops messages, sends them to server, gathers the
response and commits the change to the local buffer.

Because between my last update and my next commit, some more commits might have
been pushed to the server, when I submit my commit, the server lets me know
about all those other edits I should've add to my buffer before pushing mine. So
I must first locally commit their edits, and only then do mine.

Since my edit is practically commited when the user types (to avoid reverting
it), an additional local buffer is kept. All the edits are commited to this
buffer in the correct order, and then the view is replaced with it.


---

Iulius Curt 2013