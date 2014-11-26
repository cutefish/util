import re
import xml.etree.ElementTree as ET

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

    def get(self, key, default=None):
        val = self._dict.get(key, default)
        # support string expand
        if isinstance(val, str):
            val = self.expand(val)
        else:
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

    @classmethod
    def serialize(cls, keyvals, writer, classes={}):
        pass

    @classmethod
    def deserialize(cls, reader, classes={}):
        pass


# Human readable readers and writers
class XmlConfigParser:
    def parse(self, filename):
        retDict = {}
        tree = ET.parse(normalizePath(filename))
        root = tree.getroot()
        if 'configuration' != root.tag:
            raise ValueError('invalid root tag: ' + root.tag)
        for prop in root:
            if 'configuration' == prop.tag:
                retDict.update(self.parse(prop.text))
                continue
            if 'property' != prop.tag:
                raise ValueError('invalid property tag: ' + prop.tag)
            key = None
            val = None
            for field in prop:
                if 'name' == field.tag:
                    #name should not have child
                    if len(list(field)) != 0:
                        raise SyntaxError('name should not have child:'
                                          '%s' % ET.dump(field))
                    key = field.text
                if 'value' == field.tag:
                    #value should not have child
                    if len(list(field)) != 0:
                        raise SyntaxError('value should not have child:'
                                          '%s' % ET.dump(field))
                    val = field.text
            if (key is None) or (val is None):
                raise SyntaxError('no key or value for prop:'
                                  '%s' % ET.dump(prop))
            retDict[key] = val
        return retDict


class PropConfigParser:
    def parse(self, filename):
        retDict = {}
        with open(normalizePath(filename)) as reader:
            lineno = 1
            for line in reader:
                if line.startswith('#'):
                    continue
                try:
                    key, value = re.split('\s*=\s*', line.strip(), 1)
                except:
                    print ("PropConfigParser Parse Error. [%s] %s"
                           % (lineno, line))
                    continue
                retDict[key] = value
        return retDict


class XmlConfigWriter:
    def write(self, theDict, filename):
        root = ET.Element('configuration')
        root.text = '\n  \n  '
        lastProp = None
        for key in theDict:
            prop = ET.SubElement(root, 'property')
            prop.text = '\n    '
            prop.tail = '\n  \n  '
            name = ET.SubElement(prop, 'name')
            name.text = key
            name.tail = '\n    '
            value = ET.SubElement(prop, 'value')
            value.text = theDict[key]
            value.tail = '\n  '
            lastProp = prop
        if lastProp is not None:
            lastProp.tail = '\n\n'
        root.tail = '\n'
        tree = ET.ElementTree(root)
        tree.write(filename)


class PropConfigWriter:
    def write(self, theDict, filename):
        with open(normalizePath(filename), 'w') as writer:
            for key, value in theDict.iteritems():
                writer.write('%s = %s\n' % (key, value))
