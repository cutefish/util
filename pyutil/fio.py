import io
import os
import shutil


class FileUtil(object):
    @classmethod
    def normalize_path(cls, path):
        return os.path.abspath(os.path.expanduser(path))

    @classmethod
    def tail_stream(cls, fh, nlines=10, ave_length=80):
        old_pos = fh.tell()
        while True:
            try:
                fh.seek(-int(nlines * ave_length), io.SEEK_END)
            except IOError:
                fh.seek(0)
            pos = fh.tell()
            lines = fh.read().split('\n')
            oneorzero = 1 if lines[-1] == '' else 0
            currno = len(lines) - oneorzero
            if (currno >= nlines) or (pos == 0):
                fh.seek(old_pos, io.SEEK_SET)
                nlines += oneorzero
                return '\n'.join(lines[-nlines:])
            ave_length *= nlines / float(len(lines))

    @classmethod
    def tail(cls, filename, nlines=10):
        with open(filename, 'r') as fh:
            fh.seek(0, io.SEEK_END)
            return FileUtil.tail_stream(fh, nlines)

    @classmethod
    def mkdirp(cls, dirname):
        dirname = FileUtil.normalize_path(dirname)
        if os.path.isdir(dirname):
            return
        if os.path.isfile(dirname):
            raise ValueError('Path %s exists and is a file.')
        os.makedirs(dirname)

    @classmethod
    def rmf(cls, path):
        """Forcefully remove path and ignore error."""
        path = FileUtil.normalize_path(path)
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            else:
                return
        except:
            pass

    @classmethod
    def ensure_file(cls, path):
        path = FileUtil.normalize_path(path)
        if not os.path.isfile(path):
            raise IOError('%s is not a file' % (path))

    @classmethod
    def ensure_dir(cls, path):
        path = FileUtil.normalize_path(path)
        if not os.path.isdir(path):
            raise IOError('%s is not a directory' % (path))


class FileWriter(io.FileIO):
    def __init__(self, filename):
        super(FileWriter, self).__init__(filename, 'w+')

    def tail(self, nlines=10):
        return FileUtil.tail_stream(self, nlines)


class StdFileWriter(object):
    def __init__(self, dirname):
        dirname = FileUtil.normalize_path(dirname)
        FileUtil.mkdirp(dirname)
        outfile = '%s/stdout' % (dirname)
        FileUtil.rmf(outfile)
        errfile = '%s/stderr' % (dirname)
        FileUtil.rmf(errfile)
        self.out_writer = FileWriter(outfile)
        self.err_writer = FileWriter(errfile)

    def stdout(self):
        return self.out_writer

    def stderr(self):
        return self.err_writer
