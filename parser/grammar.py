from .grammar_parser import GrammarParser
from .state import STATE_LABEL
from .parse_tree import Node, ParseTree
import tokenize
import six


class Tokens(object):
    def __init__(self, src):
        self.gen = tokenize.generate_tokens(six.StringIO(src).readline)
        self.cur = self.next()

    def next(self):
        while True:
            tk = next(self.gen)
            if tk[0] != tokenize.NL:
                self.cur = tk
                return tk


class Grammar(object):
    def __init__(self, gramsrc):
        self.states = GrammarParser(gramsrc).states

    def parse(self, src, init='file_input'):
        tokens = Tokens(src)
        tree = ParseTree(init, STATE_LABEL, None)
        stack = [self.states[init]]

        while stack:
            state = stack[-1]
            tk = tokens.cur
            if tk.type not in state.bootstrap:
                if state.is_final:
                    stack = stack[:-1]
                    if stack:
                        tree.up()
                    continue
                raise SyntaxError('invalid grammar0',
                    ('<src>', tk.start[0], tk.start[1], tk.line))
            arc = state.bootstrap[tk.type].get(tk.string, None) or \
                    state.bootstrap[tk.type].get(None, None)
            if arc is None:
                if state.is_final:
                    stack = stack[:-1]
                    if stack:
                        tree.up()
                    continue
                raise SyntaxError('invalid grammar1',
                    ('<src>', tk.start[0], tk.start[1], tk.line))
            stack[-1] = arc[1]
            if arc[0] is not None:
                stack.append(arc[0])
                tree.add_down(Node(arc[0].name, tk.type, tk.string, tk.start))
            else:
                tree.add(Node(None, tk.type, tk.string, tk.start, tk.end))
                while True:
                    try:
                        tokens.next()
                    except StopIteration:
                        if arc[1].is_final:
                            stack = stack[:-1]
                            if stack:
                                tree.up()
                            break
                        raise SyntaxError('unexpected end',
                            ('<src>', tk.start[0], tk.start[1], tk.line))
                    else:
                        if tokens.cur.type == tokenize.COMMENT:
                            tree.add(Node(
                                None, tokens.cur.type, tokens.cur.string,
                                tokens.cur.start, tokens.cur.end))
                        else:
                            break
        try:
            tokens.next()
            raise SyntaxError('too more tokens: %r', tokens.cur)
        except StopIteration:
            pass

        return tree
