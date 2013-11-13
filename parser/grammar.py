from .grammar_parser import GrammarParser


class Grammer(object):
    def __init__(self, gramsrc):
        parser = GrammarParser(gramsrc)
        self.dfas = parser.dfas
