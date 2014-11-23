import unittest

from pyutil.fio import FileUtil, FileWriter
from pyutil.string import StringUtil, NLinesStringWriter

class TestFileUtil(unittest.TestCase):
    def testTailStream(self):
        FileUtil.mkdirp('/tmp')
        FileUtil.rmf('/tmp/t')
        with open('/tmp/t', 'w+') as fh:
            fh.write('abc\n')
            self.assertEqual('abc\n', FileUtil.tail_stream(fh, 3, 8))
            fh.write('abc')
            self.assertEqual('abc\nabc', FileUtil.tail_stream(fh, 3, 8))
            fh.write('defghi')
            self.assertEqual('abc\nabcdefghi', FileUtil.tail_stream(fh, 3, 8))
            fh.write('\n')
            self.assertEqual('abc\nabcdefghi\n', FileUtil.tail_stream(fh, 3, 8))
            fh.write('a\n')
            self.assertEqual('abc\nabcdefghi\na\n', FileUtil.tail_stream(fh, 3, 8))
            fh.write('abc')
            self.assertEqual('abcdefghi\na\nabc', FileUtil.tail_stream(fh, 3, 8))
            fh.write('\n')
            self.assertEqual('abcdefghi\na\nabc\n', FileUtil.tail_stream(fh, 3, 8))

    def testTail(self):
        FileUtil.mkdirp('/tmp')
        FileUtil.rmf('/tmp/t')
        with open('/tmp/t', 'w') as fh:
            fh.write('a\nb\nc\nd\n')
        filename = '/tmp/t'
        self.assertEqual('c\nd\n', FileUtil.tail(filename, 2))
        self.assertEqual('a\nb\nc\nd\n', FileUtil.tail(filename, 5))


class TestFileWriter(unittest.TestCase):
    def testTail(self):
        FileUtil.mkdirp('/tmp')
        FileUtil.rmf('/tmp/t')
        with FileWriter('/tmp/t') as fh:
            fh.write('abc\n')
            self.assertEqual('abc\n', FileUtil.tail_stream(fh, 3, 8))
            fh.write('abc')
            self.assertEqual('abc\nabc', FileUtil.tail_stream(fh, 3, 8))
            fh.write('defghi')
            self.assertEqual('abc\nabcdefghi', FileUtil.tail_stream(fh, 3, 8))
            fh.write('\n')
            self.assertEqual('abc\nabcdefghi\n', FileUtil.tail_stream(fh, 3, 8))
            fh.write('a\n')
            self.assertEqual('abc\nabcdefghi\na\n', FileUtil.tail_stream(fh, 3, 8))
            fh.write('abc')
            self.assertEqual('abcdefghi\na\nabc', FileUtil.tail_stream(fh, 3, 8))
            fh.write('\n')
            self.assertEqual('abcdefghi\na\nabc\n', FileUtil.tail_stream(fh, 3, 8))


if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestFileUtil),
        unittest.TestLoader().loadTestsFromTestCase(TestFileWriter),
    ])
    unittest.TextTestRunner().run(suite)
