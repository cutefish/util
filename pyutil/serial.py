import array
import inspect
import imp
import logging
import struct
from collections import namedtuple

from pyutil.fio import FileUtil

class ImportUtil(object):
    LOG = logging.getLogger('ImportUtil')
    @classmethod
    def findclass_ofbase(cls, path, base):
        path = FileUtil.normalize_path(path)
        dirname = FileUtil.dirname(path)
        filename = FileUtil.basename(path)
        FileUtil.ensure_file(path)
        if not (filename.endswith('.py')):
            raise SyntaxError('input %s must be a python file.' % (path))
        try:
            modulename = filename[0 : len(filename) - 3]
            modulefile, pathname, description = \
                imp.find_module(modulename, [dirname])
            module = imp.load_module(
                modulename, modulefile, pathname, description)
            members = inspect.getmembers(module)
            subclz = None
            for clzname, clz in members:
                if (inspect.isclass(clz)):
                    if clz is base:
                        continue
                    if issubclass(clz, base):
                        subclz = clz
            if subclz is None:
                raise SyntaxError('must define a subclass of %s'
                                  % (base.__name__))
            return subclz
        except:
            ImportUtil.LOG.exception('Error import class')
            return


class SerializeTool(object):
    # To do: detect cycles.
    def __init__(self):
        ClzSymbols = namedtuple('ClzSymbols', ['clz', 'name'])
        self.clznames = ClzSymbols(clz=dict(), name=dict())
        self.visited = set([])

    def clear_visited(self):
        self.visited.clear()

    def reset_class(self, names):
        self.clznames.name.clear()
        self.clznames.clz.clear()
        for n, c in names.iteritems():
            self.clznames.name[n] = c
            self.clznames.clz[c] = n

    def serialize(self, item, writer):
        if isinstance(item, int):
            self.write_int(item, writer)
        elif isinstance(item, float):
            self.write_float(item, writer)
        elif isinstance(item, str):
            self.write_string(item, writer)
        elif isinstance(item, array.array):
            self.write_array(item, writer)
        elif isinstance(item, list):
            self.write_list(item, writer)
        elif isinstance(item, tuple):
            self.write_tuple(item, writer)
        elif isinstance(item, dict):
            self.write_dict(item, writer)
        else:
            self.write_object(item, writer)

    def write_int(self, item, writer):
        writer.write('q')
        writer.write(struct.pack('q', item))

    def write_float(self, item, writer):
        writer.write('d')
        writer.write(struct.pack('d', item))

    def write_string(self, item, writer):
        writer.write('s')
        writer.write(struct.pack('i', len(item)))
        writer.write(item)

    def write_array(self, item, writer):
        self.ensure_notvisited(item)
        writer.write('A')
        writer.write(item.typecode)
        string = item.tostring()
        writer.write(struct.pack('i', len(string)))
        writer.write(string)

    def write_list(self, item, writer):
        self.ensure_notvisited(item)
        writer.write('L')
        writer.write(struct.pack('i', len(item)))
        for e in item:
            self.serialize(e, writer)

    def write_tuple(self, item, writer):
        self.ensure_notvisited(item)
        writer.write('T')
        writer.write(struct.pack('i', len(item)))
        for e in item:
            self.serialize(e, writer)

    def write_dict(self, item, writer):
        self.ensure_notvisited(item)
        writer.write('D')
        writer.write(struct.pack('i', len(item)))
        for k, v in item.iteritems():
            self.serialize(k, writer)
            self.serialize(v, writer)

    def write_object(self, item, writer):
        self.ensure_notvisited(item)
        writer.write('O')
        iclass = item.__class__
        cname = iclass.__name__
        if iclass in self.clznames.clz:
            cname = self.clznames.clz[iclass]
        writer.write(struct.pack('i', len(cname)))
        writer.write(cname)
        if not hasattr(iclass, 'serialize'):
            raise RuntimeError('class %s of item %s has no serialize method'
                               % (iclass, item))
        iclass.serialize(item, writer)

    def ensure_notvisited(self, item):
        if id(item) in self.visited:
            raise RuntimeError('Already visited item: %s' % (item))
        self.visited.add(id(item))

    def deserialize(self, reader):
        fmt = reader.read(1)
        if fmt == 'q':
            return self.read_int(reader)
        elif fmt == 'd':
            return self.read_float(reader)
        elif fmt == 's':
            return self.read_string(reader)
        elif fmt == 'A':
            return self.read_array(reader)
        elif fmt == 'L':
            return self.read_list(reader)
        elif fmt == 'T':
            return self.read_tuple(reader)
        elif fmt == 'D':
            return self.read_dict(reader)
        elif fmt == 'O':
            return self.read_object(reader)
        else:
            raise ValueError('Invalid format char: %s' % (fmt))

    def read_int(self, reader):
        return struct.unpack('q', reader.read(8))[0]

    def read_float(self, reader):
        return struct.unpack('d', reader.read(8))[0]

    def read_string(self, reader):
        length = struct.unpack('i', reader.read(4))[0]
        return reader.read(length)

    def read_array(self, reader):
        typecode = reader.read(1)
        item = array.array(typecode)
        length = struct.unpack('i', reader.read(4))[0]
        string = reader.read(length)
        item.fromstring(string)
        return item

    def read_list(self, reader):
        length = struct.unpack('i', reader.read(4))[0]
        item = []
        for i in range(length):
            item.append(self.deserialize(reader))
        return item

    def read_tuple(self, reader):
        length = struct.unpack('i', reader.read(4))[0]
        item = []
        for i in range(length):
            item.append(self.deserialize(reader))
        return tuple(item)

    def read_dict(self, reader):
        length = struct.unpack('i', reader.read(4))[0]
        item = {}
        for i in range(length):
            key = self.deserialize(reader)
            val = self.deserialize(reader)
            item[key] = val
        return item

    def read_object(self, reader):
        cname_len = struct.unpack('i', reader.read(4))[0]
        cname = reader.read(cname_len)
        if cname in self.clznames.name:
            iclass = self.clznames.name[cname]
        else:
            iclass = eval(cname)
        return iclass.deserialize(reader)

