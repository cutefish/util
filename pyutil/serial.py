import inspect
import imp
import logging

from pyutil.fio import FileUtil

class ImportUtil(object):
    LOG = logging.getLogger('ImportUtil')
    @classmethod
    def find_class(cls, path, base):
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
            LOG.exception('Error import class')
            return

class SerializeUtil(object):
    pass
