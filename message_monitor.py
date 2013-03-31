
'''
Implementation of a Producers-Consumers queue for handling messages.

Changes Consumer class implementation which takes changes from the queue and
sends change-requests to the server.
'''

__license__ = 'MIT http://www.opensource.org/licenses/mit-license.php'
__author__ = "Iulius Curt <iulius.curt@gmail.com>, http://iuliux.ro"


from threading import Condition, Thread


class MessageProdConsMonitor:
    '''Monitor for Producers-Consumers type of message queue'''

    UPDATE_MSG = 0
    COMMIT_MSG = 1

    def __init__(self):
        self.itemCount = 0
        self.empty = Condition()
        self.queue = list()

    def add(self, item):
        '''Add produced item to the queue'''
        self.empty.acquire()

        print '[ADD]', item
        # TODO: (optimization) Before append COMMIT_MSG, remove all UPDATE_MSGs
        #       that preceed because they are useless.
        self.queue.append(item)
        self.itemCount += 1
        self.empty.notify()

        self.empty.release()

    def remove(self):
        '''Retrieve and remove from queue an item for consumption'''
        self.empty.acquire()

        while self.itemCount < 1:
            self.empty.wait()

        item = self.queue.pop(0)
        self.itemCount -= 1
        print '[RM]', item

        self.empty.release()

        return item


class ChangesConsumer(Thread):
    def __init__(self, monitor, session):
        super(ChangesConsumer, self).__init__(name='ChangesConsumer')
        self.monitor = monitor
        self.session = session

    def run(self):
        while True:
            item = self.monitor.remove()
            msg, conv, cr = item

            if msg == MessageProdConsMonitor.COMMIT_MSG:
                conv.send(cr.serialize())
                self.session.handle_response(conv, cr)
            elif msg == MessageProdConsMonitor.UPDATE_MSG:
                conv.send(cr)

                self.session.handle_response(conv, None)
