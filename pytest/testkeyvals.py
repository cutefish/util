import array
import unittest
import struct
from StringIO import StringIO

from pyutil.keyvals import Keyvals, XmlKeyvalsUtil, PropKeyvalsUtil
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


class TestKeyvals(unittest.TestCase):
    def testAccessors(self):
        keyvals = Keyvals()
        keyvals.set('user', 'xyu40')
        keyvals.set('home', '/home/${user}')
        keyvals.set('year', 2004)
        keyvals.set('data', '/data/${year}')
        keyvals.update({'month' : 12})
        kv = Keyvals()
        kv.set('day', 11)
        keyvals.update(kv)
        self.assertEqual('xyu40', keyvals.get('user'))
        self.assertEqual('/home/xyu40', keyvals.get('home'))
        self.assertEqual(2004, keyvals.get('year'))
        self.assertEqual('/data/2004', keyvals.get('data'))
        self.assertEqual(12, keyvals.get('month'))
        self.assertEqual(11, keyvals.get('day'))

    def testSerialize(self):
        keyvals = Keyvals()
        keyvals.set('int', 1)
        keyvals.set('float', 2.0)
        keyvals.set('string', 'serialize')
        keyvals.set('array', array.array('i', [1, 2, 3, 4, 5]))
        keyvals.set('list', ['a', 'b', 'c'])
        keyvals.set('tuple', (1, 2, 3))
        keyvals.set('dict', {1 : 'a', 2 : 'b'})
        keyvals.set('object', SerObject('serobject'))
        keyvals.set('bundle', [SerObject('a'), SerObject('b'),
                    {'a' : 1, 'b' : 2, 'c' : 3},
                    [1, 2, 3, 4, 5], ('a', 'b', 'c', 'd', 'e'),
                    1, 2.0, 'serialize',
                    ])
        writer = StringIO()
        sertool = SerializeTool()
        sertool.reset_class({'SerObject' : SerObject})
        Keyvals.serialize(keyvals, writer, sertool)
        reader = StringIO(writer.getvalue())
        self.assertEqual(keyvals, Keyvals.deserialize(reader, sertool))

    def testXmlUtil(self):
        keyvals = Keyvals()
        keyvals.set('user', 'xyu40')
        keyvals.set('home', '/home/${user}')
        keyvals.set('year', 2004)
        keyvals.set('data', 1.2)
        keyvals.set('list', [1, 2, 3])
        keyvals.set('dict', {'a' : 1, 'b' : 2})
        XmlKeyvalsUtil.write_file(keyvals, '/tmp/keyvals.xml')
        self.assertEqual(keyvals, XmlKeyvalsUtil.read_file('/tmp/keyvals.xml'))

    def testPropUtil(self):
        keyvals = Keyvals()
        keyvals.set('user', 'xyu40')
        keyvals.set('home', '/home/${user}')
        keyvals.set('year', 2004)
        keyvals.set('data', 1.2)
        keyvals.set('list', [1, 2, 3])
        keyvals.set('dict', {'a' : 1, 'b' : 2})
        PropKeyvalsUtil.write_file(keyvals, '/tmp/keyvals.prop')
        self.assertEqual(keyvals, PropKeyvalsUtil.read_file('/tmp/keyvals.prop'))


if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestKeyvals),
    ])
    unittest.TextTestRunner().run(suite)
