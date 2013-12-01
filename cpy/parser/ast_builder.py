from . import ast


class ASTBuilder(object):
    def __init__(self, root_node):
        self.root = root_node
        self.build()

    def build(self):
        pass
