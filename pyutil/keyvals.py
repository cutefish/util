import re
import struct
import xml.etree.ElementTree as ET


from pyutil.fio import FileUtil
from pyutil.serial import SerializeTool

class Keyvals(object):
    """An object for key value store.

    Note:
        - key is always a string.
        - val can be any serializable object.
        - expansion is supported for string values, pattern is ${[^{}$\s]+}
        - support serialization for this object.
    """
    EXPAND_REGEX = re.compile('\$\{(?P<expand>[^{}$\s]+)\}')
    def __init__(self):
        self._dict = {}

    def __eq__(self, other):
        return self._dict == other._dict

    def get(self, key, default=None):
        val = self._dict.get(key, default)
        # support string expand
        if isinstance(val, str):
            val = self.expand(val)
        return val

    def set(self, key, val):
        self._dict[key] = val

    def expand(self, string):
        pos = 0
        while True:
            match = Keyvals.EXPAND_REGEX.search(string, pos)
            if match is None:
                return string
            pos = match.span()[1]
            key = match.group('expand')
            if key not in self._dict:
                continue
            val = self._dict[key]
            string = re.sub('\$\{%s\}' % (key), str(val), string)
            pos -= (len(key) + 3) + len(str(val))
        return string

    def update(self, keyvals):
        if isinstance(keyvals, dict):
            self._dict.update(keyvals)
        elif isinstance(keyvals, Keyvals):
            self._dict.update(keyvals._dict)
        else:
            raise TypeError('incorrect type for update: %s' % (keyvals))

    def iteritems(self):
        return self._dict.iteritems()

    def __iter__(self):
        return self._dict.__iter__()

    @classmethod
    def serialize(cls, keyvals, writer, sertool=None):
        writer.write('keyvals{')
        writer.write(struct.pack('i', len(keyvals._dict)))
        for key, val in keyvals._dict.iteritems():
            writer.write(struct.pack('i', len(key)))
            writer.write(key)
            if sertool is None:
                sertool = SerializeTool()
            sertool.serialize(val, writer)
        writer.write('}')

    @classmethod
    def deserialize(cls, reader, sertool=None):
        string = reader.read(8)
        if string != 'keyvals{':
            raise ValueError(
                'Incorrect start string: %s, should be keyvals{' % (string))
        nkeys = struct.unpack('i', reader.read(4))[0]
        keyvals = Keyvals()
        if sertool is None:
            sertool = SerializeTool()
        for i in range(nkeys):
            klen = struct.unpack('i', reader.read(4))[0]
            key = reader.read(klen)
            val = sertool.deserialize(reader)
            keyvals.set(key, val)
        string = reader.read(1)
        if string != '}':
            raise ValueError(
                'Incorrect end string: %s, should be }' % (string))
        return keyvals


#Human readable readers and writers
class XmlKeyvalsUtil(object):
    @classmethod
    def read_file(cls, filename,
                  roottag='configuration', proptag='property',
                  keytag='name', valtag='value'):
        keyvals = Keyvals()
        tree = ET.parse(FileUtil.normalize_path(filename))
        root = tree.getroot()
        if roottag != root.tag:
            raise ValueError('invalid root tag: ' + root.tag)
        for prop in root:
            if roottag == prop.tag:
                keyvals.update(cls.read_file(prop.text))
                continue
            if proptag != prop.tag:
                raise ValueError('invalid property tag: ' + prop.tag)
            key = None
            val = None
            for field in prop:
                if keytag == field.tag:
                    #name should not have child
                    if len(list(field)) != 0:
                        raise SyntaxError(
                            '%s should not have child: %s'
                            % (keytag, ET.dump(field)))
                    key = field.text
                if valtag == field.tag:
                    #value should not have child
                    if len(list(field)) != 0:
                        raise SyntaxError(
                            '%s should not have child:%s'
                            % (valtag, ET.dump(field)))
                    val = field.text
            if (key is None) or (val is None):
                raise SyntaxError(
                    'no key or value for prop: %s' % (ET.dump(prop)))
            try:
                val = eval(val)
            except:
                pass
            keyvals.set(key, val)
        return keyvals

    @classmethod
    def write_file(cls, keyvals, filename,
                   roottag='configuration', proptag='property',
                   keytag='name', valtag='value'):
        root = ET.Element(roottag)
        root.text = '\n  \n  '
        lastProp = None
        for key in keyvals:
            prop = ET.SubElement(root, proptag)
            prop.text = '\n    '
            prop.tail = '\n  \n  '
            name = ET.SubElement(prop, keytag)
            name.text = key
            name.tail = '\n    '
            value = ET.SubElement(prop, valtag)
            value.text = str(keyvals._dict[key])
            value.tail = '\n  '
            lastProp = prop
        if lastProp is not None:
            lastProp.tail = '\n\n'
        root.tail = '\n'
        tree = ET.ElementTree(root)
        tree.write(FileUtil.normalize_path(filename))


class PropKeyvalsUtil(object):
    @classmethod
    def read_file(cls, filename):
        keyvals = Keyvals()
        with open(FileUtil.normalize_path(filename)) as reader:
            for line in reader:
                if line.startswith('#'):
                    continue
                key, val = re.split('\s*=\s*', line, 1)
                key = key.strip()
                val = val.strip()
                try:
                    val = eval(val)
                except:
                    pass
                keyvals.set(key, val)
        return keyvals

    @classmethod
    def write_file(cls, keyvals, filename):
        with open(FileUtil.normalize_path(filename), 'w') as writer:
            for key, value in keyvals.iteritems():
                writer.write('%s = %r\n' % (key, value))
