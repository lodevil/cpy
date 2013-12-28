from .tc import ASTTestCase


class ImportTest(ASTTestCase):
    def test_simple(self):
        self.pycheck('import a')
        self.pycheck('import a.b')
        self.pycheck('import a.b.c')

    def test_import_as(self):
        self.pycheck('import a.b as c')

    def test_import_multi_as(self):
        self.pycheck('import a.b as c, e as f, g.h as i')


class ImportFromTest(ASTTestCase):
    def test_simple(self):
        self.pycheck('from a import b')
        self.pycheck('from a.b import c')

    def test_from_level(self):
        self.pycheck('from .. import a')
        self.pycheck('from ..a.b.c import d')

    def test_from_as(self):
        self.pycheck('from a import b as c')
        self.pycheck('from a import c as d, e as f')
