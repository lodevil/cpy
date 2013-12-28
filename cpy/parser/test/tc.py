import unittest
from cpy.parser.ast_builder import ASTBuilder
from cpy.parser.pygrammar import grammar
from .. import ast as AST
import ast as pyast


class ASTTestCase(unittest.TestCase):
    def src_from_doc(self, doc):
        lines = doc.split('\n')
        if len(lines) < 2:
            return '\n'.join(lines)
        lines = lines[1:-1]
        pren = len(lines[0]) - len(lines[0].lstrip())
        for i, line in enumerate(lines):
            lines[i] = line[pren:]
        return '\n'.join(lines)

    def ast_from_doc(self, doc):
        src = self.src_from_doc(doc)
        src = grammar.parse(src)
        ast  = ASTBuilder(src).ast
        self.assertEqual(ast, AST.Module(AST.Equal))
        return ast

    def pycheck(self, doc):
        src = self.src_from_doc(doc)
        ast  = ASTBuilder(grammar.parse(src)).ast
        pyresult = pyast.parse(src)
        self.assertEqual(ast, pyresult)


import logging
l = logging.getLogger()
l.setLevel(logging.DEBUG)
