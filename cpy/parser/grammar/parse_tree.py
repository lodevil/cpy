import tokenize
from .state import STATE_LABEL


class Node(object):
    __slots__ = 'type', 'val', 'subs', 'start', 'end'
    def __init__(self, type, val, start=None, end=None):
        self.type = type
        self.val = val
        self.subs = []
        self.start = start
        self.end = end

    def filter(self, type, **kwargv):
        if 'val' in kwargv:
            val = kwargv['val']
            for node in self.subs:
                if node.type == type and node.val == val:
                    yield node
        else:
            for node in self.subs:
                if node.type == type:
                    yield node

    def __eq__(self, type):
        return self.type == type

    def __ne__(self, type):
        return self.type != type

    def __iter__(self):
        yield from self.subs

    def __getitem__(self, k):
        return self.subs[k]

    def __len__(self):
        return len(self.subs)

    def __repr__(self):
        return '<Node %d(%r)>' % (self.type, self.val)


class ParseTree(object):
    def __init__(self, symbols, name):
        self.symbols = symbols
        self.entry = Node(symbols[name], None)
        self.stack = []
        self.cur = self.entry

    def add(self, node):
        self.cur.subs.append(node)

    def up(self):
        if len(self.stack) == 0:
            raise Exception('up fail')
        self.cur, self.stack = self.stack[-1], self.stack[:-1]

    def add_down(self, node):
        self.cur.subs.append(node)
        self.stack.append(self.cur)
        self.cur = node

    def printtree(self):
        def printnode(node, indent):
            if node.type > STATE_LABEL:
                print(indent + 'Node(%s)' % self.symbols[node.type])
            else:
                print(indent + 'Node(%s(%r))' % (
                    tokenize.tok_name[node.type], node.val))
            for n in node.subs:
                printnode(n, indent + '  ')
        printnode(self.entry, '')
