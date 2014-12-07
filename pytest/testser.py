import array
import unittest
import struct
from StringIO import StringIO

from pyutil.serial import SerializeTool

class SerObject(object):
    def __init__(self, string):
        self.string = string

    def __eq__(self, other):
        return self.string == other.string

    @classmethod
    def serialize(cls, item, writer):
        writer.write(struct.pack('i', len(item.string)))
        writer.write(item.string)

    @classmethod
    def deserialize(cls, reader):
        length = struct.unpack('i', reader.read(4))[0]
        return SerObject(reader.read(length))


class TestSerializeTool(unittest.TestCase):
    def commonTest(self, item):
        writer = StringIO()
        sertool = SerializeTool()
        sertool.reset_class({'SerObject' : SerObject})
        sertool.serialize(item, writer)
        reader = StringIO(writer.getvalue())
        self.assertEqual(item, sertool.deserialize(reader))

    def testSer(self):
        self.commonTest(1)
        self.commonTest(2.0)
        self.commonTest('serialize')
        self.commonTest(array.array('i', [1, 2, 3, 4, 5]))
        self.commonTest(['a', 'b', 'c'])
        self.commonTest((1, 2, 3))
        self.commonTest({1 : 'a', 2 : 'b', 3 : 'c'})
        self.commonTest(SerObject('serobject'))
        self.commonTest([SerObject('a'), SerObject('b'),
                         {'a' : 1, 'b' : 2, 'c' : 3},
                         [1, 2, 3, 4, 5], ('a', 'b', 'c', 'd', 'e'),
                         1, 2.0, 'serialize',
                         ])


if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestSerializeTool),
    ])
    unittest.TextTestRunner().run(suite)
