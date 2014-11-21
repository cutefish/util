class StringUtil(object):
    @classmethod
    def has_chars(cls, string, chars):
        for ch in chars:
            if ch in string:
                return True
        return False


class StringWriter(object):
    def __init__(self):
        self.result = []

    def write(self, string):
        self.result.append(string)

    def __str__(self):
        return ''.join(self.result)


class StringReader(object):
    def __init__(self, string):
        self.curr = -1
        self.string = str(string)

    def read(self):
        self.curr += 1
        return self.string[self.curr]
