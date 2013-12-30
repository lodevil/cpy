from io import BytesIO, StringIO
import tokenize
import os


class SourceFile(object):
    def __init__(self, path=None, src=None):
        if path:
            self.name = os.path.split(path)[-1]
            src = open(path, 'rb').read()
        elif not src:
            raise Exception('path or src can\'t be None')
        else:
            self.name = '<string>'
        self.path = path

        self.source = src
        if isinstance(src, str):
            if src and src[-1] != '\n':
                src += '\n'
            self._gen = tokenize.generate_tokens(StringIO(src).readline)
        else:
            if src and src[-1] != b'\n':
                src += b'\n'
            self._gen = tokenize.tokenize(BytesIO(src).readline)
        self.encoding = 'utf8'
        self.parse_tree = None
        self._lines = None

    def get_line(self, lineno):
        if self._lines is None:
            if not isinstance(self.source, str):
                self.source = self.source.decode(self.encoding)
            self._lines = self.source.split('\n')
        if lineno >= len(self._lines):
            return None
        return self._lines[lineno]

    def tokens(self):
        tk = next(self._gen)
        if tk.type == tokenize.ENCODING:
            self.encoding = tk.string
        elif tk.type not in (tokenize.NL, tokenize.COMMENT):
            yield tk

        while True:
            tk = next(self._gen)
            if tk.type not in (tokenize.NL, tokenize.COMMENT):
                yield tk
