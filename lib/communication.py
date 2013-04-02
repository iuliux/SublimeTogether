from restful_lib import Connection
from changerequests import *


class ConversationStarter:
    '''Factory class for Conversation objects'''

    def __init__(self, target_uri):
        self.uri = target_uri
        self.conn = Connection(target_uri)

    def new(self, method, resource=''):
        return Conversation(self.conn, method, resource)


class Conversation:
    '''
    A conversation is a sequence of one request followed by one response.
    To be produced from a ConversationStarter factory.
    '''

    def __init__(self, conn, method, resource):
        self._conn = conn
        self._method = method.upper()
        self._resource = resource
        self.response_code = 0
        self.response_data = ''
        self.response_headers = {}

    def send(self, data='', headers={}):
        '''
        Sends the request and receives the response
        After this method finishes, response data will be available
        '''
        data = str(data)
        resp = None
        if self._method == 'GET':
            resp = self._conn.request_get(resource=self._resource,
                                          args={'data': data},
                                          headers=headers)
        elif self._method == 'DELETE':
            resp = self._conn.request_delete(resource=self._resource,
                                             body=data,
                                             headers=headers)
        elif self._method == 'HEAD':
            resp = self._conn.request_head(resource=self._resource,
                                           headers=headers)
        elif self._method == 'POST':
            resp = self._conn.request_post(resource=self._resource,
                                           body=data,
                                           headers=headers)
        elif self._method == 'PUT':
            resp = self._conn.request_put(resource=self._resource,
                                          body=data,
                                          headers=headers)
        else:
            raise UndefinedMethodError()

        # Set response data
        self.response_headers = resp['headers']

        if self._method == 'HEAD':
            try:
                self.response_data = resp['headers']['data']
            except KeyError:
                pass
        else:
            self.response_data = resp['body']

        try:
            self.response_code = int(resp['headers']['code'])
        except KeyError:
            pass

    def __repr__(self):
        return 'Conversation(' + self._method + ', ' + self._resource + ')'

    def __str__(self):
        return self.__repr__()


class UndefinedMethodError(Exception):
    def __str__(self):
        return "Undefined HTTP method. Try on of: GET, POST, PUT, HEAD, DELETE"
