from .grammar_parser import GrammarParser
from collections import defaultdict
import tokenize
import re
import six


class Tokens(object):
    def __init__(self, src):
        self.gen = tokenize.generate_tokens(six.StringIO(src).readline)
        self.stack = []

    def next(self):
        try:
            tk = self.stack.pop()
        except IndexError:
            tk = next(self.gen)
        return tk

    def put(self, t):
        self.stack.append(t)


class GrammarError(Exception):
    pass


class Grammar(object):
    op_r = re.compile(tokenize.Operator)

    def __init__(self, gramsrc):
        self.states = GrammarParser(gramsrc).states

    def eval_check(self, src):
        tks = Tokens(src)
        return self.states['eval_input'].check(tks)

    def file_check(self, src):
        tks = Tokens(src)
        #pdb.set_trace()
        return self.states['file_input'].check(tks)
