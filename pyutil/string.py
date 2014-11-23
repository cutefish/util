class StringUtil(object):
    @classmethod
    def has_chars(cls, string, chars):
        for ch in chars:
            if ch in string:
                return True
        return False

    @classmethod
    def normalize_path(cls, string):
        if not string.startswith('/'):
            raise ValueError("Name must starts with /: %s" % string)
        paths = string.split('/')
        result = []
        for path in paths[1:]:
            if path == '':
                continue
            elif path == '.':
                continue
            elif path == '..':
                if len(result) == 0:
                    continue
                else:
                    result.pop()
            else:
                result.append(path)
        return '/' + '/'.join(result)


class NLinesStringWriter(object):
    """A file-like objects that write to a string buffer and kept maximum N
    lines.
    """
    def __init__(self, nlines, maxlinesize=1024):
        if nlines <= 0:
            raise ValueError('nlines must larger than 0.')
        self.nlines = nlines
        self.linebuf = []
        self.lbstart = 0
        self.buf = []
        self.pos = 0
        self.closed = False
        self.softspace = 0
        self.maxlinesize = maxlinesize

    def __iter__(self):
        self._complain_notimplemented('__iter__')

    def next(self):
        self._complain_notimplemented('next')

    def close(self):
        self.linebuf.append(''.join(self.buf))
        self.buf = []
        if not self.closed:
            self.closed = True

    def isatty(self):
        self._complain_ifclosed()
        return False

    def seek(self, pos, mode=0):
        self._complain_notimplemented('seek')

    def tell(self):
        """Return the file's current position."""
        return self.pos

    def lineno(self):
        oneorzero = 1 if len(self.buf) != 0 else 0
        return len(self.linebuf) - self.lbstart + oneorzero

    def read(self, n=-1):
        self._complain_notimplemented('read')

    def readline(self, length=None):
        self._complain_notimplemented('readline')

    def readlines(self, sizehint=0):
        self._complain_notimplemented('readlines')

    def truncate(self, size=None):
        self._complain_notimplemented('truncate')

    def write(self, s):
        """Write a string to the file. """
        self._complain_ifclosed()
        if not s: return
        if not isinstance(s, basestring):
            s = str(s)
        left = 0
        right = 0
        while right < len(s):
            if right - left + 1 >= self.maxlinesize:
                raise RuntimeError('Line too long.')
            if s[right] == '\n':
                if len(self.buf) != 0:
                    self.buf.append(s[left : right + 1])
                    newline = ''.join(self.buf)
                    self.buf = []
                else:
                    newline = s[left : right + 1]
                self.linebuf.append(newline)
                left = right + 1
            right += 1
        if left < len(s):
            self.buf.append(s[left:])
        self.pos += len(s)
        self.ensure_size()

    def ensure_size(self):
        if self.lineno() > self.nlines:
            oneorzero = 1 if len(self.buf) != 0 else 0
            if len(self.linebuf) >= 2 * self.nlines:
                linebuf = self.linebuf
                self.linebuf = []
                self.pos = 0
                lbstart = len(linebuf) - self.nlines + oneorzero
                for i in range(lbstart, len(linebuf)):
                    line = linebuf[i]
                    self.linebuf.append(line)
                    self.pos += len(line)
                self.pos += len(''.join(self.buf))
            else:
                lbstart = self.lbstart
                self.lbstart = len(self.linebuf) - self.nlines + oneorzero
                for line in self.linebuf[lbstart : self.lbstart]:
                    self.pos -= len(line)

    def writelines(self, iterable):
        for line in iterable:
            self.write(line)

    def flush(self):
        """Flush the internal buffer. Do nothing actually."""
        self._complain_ifclosed()

    def getvalue(self):
        """Retrieve the entire contents of the "file". """
        return ''.join(self.linebuf[self.lbstart:]) + ''.join(self.buf)

    def lines(self):
        result = self.linebuf[self.lbstart:]
        if len(buf) != 0:
            result.append(''.join(self.buf))
        return result

    def tail(self, nlines=10):
        oneorzero = 1 if len(self.buf) != 0 else 0
        start = max(self.lbstart, len(self.linebuf) - nlines + oneorzero)
        return ''.join(self.linebuf[start:]) + ''.join(self.buf)

    def _complain_notimplemented(self, name):
        raise NotImplementedError('%s not supported for NLinesStringWriter.')

    def _complain_ifclosed(self):
        if self.closed:
            raise ValueError, 'I/O operation on closed file'

class NLinesStdStringWriter(object):
    def __init__(self, nlines_out, nlines_err):
        self.out_writer = NLinesStringWriter(nlines_out)
        self.err_writer = NLinesStringWriter(nlines_err)

    def stdout(self):
        return self.out_writer

    def stderr(self):
        return self.err_writer
