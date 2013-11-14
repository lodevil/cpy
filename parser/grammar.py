from .grammar_parser import GrammarParser


class Grammar(object):
    def __init__(self, gramsrc):
        parser = GrammarParser(gramsrc)
        self.dfas = parser.dfas
