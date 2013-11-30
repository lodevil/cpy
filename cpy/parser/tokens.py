import tokenize
import six


class Tokens(object):
    def __init__(self, src):
        self.gen = tokenize.generate_tokens(six.StringIO(src).readline)
        self.cur = self.next()

    def next(self):
        while True:
            tk = next(self.gen)
            if tk[0] not in (tokenize.NL, tokenize.COMMENT):
                self.cur = tk
                return tk
