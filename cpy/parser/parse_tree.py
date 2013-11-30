import tokenize


class Node(object):
    __slots__ = 'name', 'type', 'val', 'subs', 'start', 'end'
    def __init__(self, name, type, val, start=None, end=None):
        self.name = name
        self.type = type
        self.val = val
        self.subs = []
        self.start = start
        self.end = end

    def append(self, node):
        if not isinstance(node, Node):
            if isinstance(node, tokenize.TokenInfo):
                node = Node(Node, node.type, node.string, node.start, node.end)
            else:
                raise Exception('invalid node: %r' % node)
        self.subs.append(node)

    def __iter__(self):
        yield from self.subs

    def __getitem__(self, k):
        return self.subs[k]

    def __len__(self):
        return len(self.subs)

    def __repr__(self):
        if self.name is not None:
            return '<Node %s>' % self.name
        return '<Node @%d(%r)>' % (id(self), self.val)

    def printall(self, indent=''):
        if self.name is not None:
            print(indent + '<Node %s>' % self.name)
        else:
            print(indent + '<Node (%r)>' % self.val)
        for sub in self.subs:
            sub.printall(indent + '  ')


class ParseTree(object):
    def __init__(self, name, type, val, start=None, end=None):
        self.entry = Node(name, type, val, start, end)
        self.stack = []
        self.cur = self.entry

    def add(self, node):
        self.cur.append(node)

    def up(self):
        if len(self.stack) == 0:
            raise Exception('up fail')
        self.cur, self.stack = self.stack[-1], self.stack[:-1]

    def add_down(self, node):
        self.cur.append(node)
        self.stack.append(self.cur)
        self.cur = node
