import unittest

from pyutil.string import StringUtil, NLinesStringWriter

class TestStringUtil(unittest.TestCase):
    def testNormalizePath(self):
        string = '/../'
        self.assertEqual(StringUtil.normalize_path(string), '/')
        string = '/home//foo/'
        self.assertEqual(StringUtil.normalize_path(string), '/home/foo')
        string = '/a/./b/../../c/'
        self.assertEqual(StringUtil.normalize_path(string), '/c')


class TestNLinesStringWriter(unittest.TestCase):
    def testWrite(self):
        writer = NLinesStringWriter(1)
        writer.write('abc')
        self.assertEqual('abc', writer.getvalue())
        writer = NLinesStringWriter(1)
        writer.write('abc\n')
        self.assertEqual('abc\n', writer.getvalue())
        writer = NLinesStringWriter(1)
        writer.write('\nabc')
        self.assertEqual('abc', writer.getvalue())
        writer = NLinesStringWriter(1)
        writer.write('abc\nefg')
        self.assertEqual('efg', writer.getvalue())
        writer = NLinesStringWriter(1)
        writer.write('abc\nefg\n')
        self.assertEqual('efg\n', writer.getvalue())
        writer = NLinesStringWriter(3)
        writer.write('\nabc\nefg\nhij\nklm\n')
        self.assertEqual('efg\nhij\nklm\n', writer.getvalue())

    def testTail(self):
        writer = NLinesStringWriter(3)
        writer.write('\nabc\nefg\nhij\nklm')
        self.assertEqual('klm', writer.tail(1))
        self.assertEqual('efg\nhij\nklm', writer.tail(5))
        writer = NLinesStringWriter(3)
        writer.write('\nabc\nefg\nhij\nklm\n')
        self.assertEqual('klm\n', writer.tail(1))
        self.assertEqual('efg\nhij\nklm\n', writer.tail(5))

    def testWriteLines(self):
        writer = NLinesStringWriter(3)
        lines = [
            '\n',
            'ab',
            'c',
            '\n',
            'efg\n'
            'hij\nklmnop'
        ]
        writer.writelines(lines)
        self.assertEqual('efg\nhij\nklmnop', writer.getvalue())

    def testStats(self):
        writer = NLinesStringWriter(3)
        lines = [
            '\n',
            'abcd\n',
            'efg\n',
            'hij\n',
            'klmnop'
        ]
        writer.writelines(lines)
        start = max(0, len(lines) - 3)
        self.assertEqual(len(''.join(lines[start:])), writer.tell())
        self.assertEqual(3, writer.lineno())
        writer = NLinesStringWriter(3)
        lines = [
            '\n',
            'ab',
        ]
        writer.writelines(lines)
        start = max(0, len(lines) - 3)
        self.assertEqual(len(''.join(lines[start:])), writer.tell())
        self.assertEqual(2, writer.lineno())


if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestStringUtil),
        unittest.TestLoader().loadTestsFromTestCase(TestNLinesStringWriter),
    ])
    unittest.TextTestRunner().run(suite)
