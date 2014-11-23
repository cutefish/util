import logging
import multiprocessing
import shlex
import subprocess
import time
import traceback
from threading import Lock, Thread

from pyutil.string import NLinesStdStringWriter

class Alarm(Thread):
    """A background alarm.

    init arguments:
        function: work to do at each alarm time.
        interval: the interval between two alarms.
        start: start time of the alarm.

    methods:
        start(): start the alarm.
        stop(): stop the alarm.
    """
    def __init__(self, function, interval, at=0):
        super(Alarm, self).__init__()
        self.daemon = True
        self.function = function
        self.interval = interval
        self.at = at
        self.stopped = False

    def run(self):
        time.sleep(self.at)
        while not self.stopped:
            self.function()
            time.sleep(self.interval)

    def stop(self):
        self.stopped = True


class Pool(object):
    """A pool of processes to run the commands.

    init arguments:
        nprocs: number of processes.
        qlen: max number of commands in queue.

    methods:
        start(): start the pool.
        add(): add a command to the queue for processing.
        wait(): wait until all the commands are proccessed.
        getfinished(): return the list of finished commands.
        getfailed(): return the list of failed commands.
        ntorun(): return number of commands to run.
        clear(): clear the current to run queue and kill the curr works.
        close(): close the pool.
    """
    class QueueFullError(Exception):
        pass

    def __init__(self, nprocs=None, qlen=1000000):
        if nprocs is None:
            nprocs = multiprocessing.cpu_count()
        self.torun = (Lock(), [])
        self.finished = (Lock(), [])
        self.failed = (Lock(), [])
        self.qlen = qlen
        self.threads = []
        self.closed = False
        self.logger = logging.getLogger(self.__class__.__name__)
        for i in range(nprocs):
            thread = PoolWorker(self.torun, self.finished, self.failed)
            thread.daemon = True
            self.threads.append(thread)

    def start(self):
        for thread in self.threads:
            thread.start()

    def ntorun(self):
        return len(self.torun[1])

    def add(self, cmd, out_writer=None, timeout=None):
        """Add a command to the queue for processing.

        arguments:
            cmd: the command.
            out_writer: the writer of the stdout and stderr.
            timeout: max time for the command before kill.
        """
        if len(self.torun[1]) >= self.qlen:
            raise Pool.QueueFullError()
        with self.torun[0]:
            self.torun[1].append((cmd, out_writer, timeout))

    def wait(self):
        while True:
            blocking = False
            with self.torun[0]:
                if len(self.torun[1]) != 0:
                    blocking = True
                for thread in self.threads:
                    if thread.isworking():
                        blocking = True
            if blocking:
                time.sleep(1)
            else:
                break

    def getfinished(self):
        return self.finished[1]

    def getfailed(self):
        return self.failed[1]

    def clear(self):
        with self.torun[0]:
            self.torun[1] = []
        for thread in self.threads:
            thread.clear()

    def close(self):
        for thread in self.threads:
            thread.close()

class PoolWorker(Thread):
    def __init__(self, torun, finished, failed):
        super(PoolWorker, self).__init__()
        self.torun = torun
        self.finished = finished
        self.failed = failed
        self.curr = None
        self.start = None
        self.timeout = None
        self.check_interval = 0.1
        self.closed = False
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        try:
            self.work()
        finally:
            self.clear()

    def work(self):
        while not self.closed:
            if self.curr is not None:
                self.handle_current()
            else:
                self.fetch_command()
            time.sleep(self.check_interval)

    def handle_current(self):
        proc, cmd, writer = self.curr
        # check timeout
        if self.timeout is not None:
            if time.time() - self.start > self.timeout:
                proc.kill()
                proc.wait()
        # check execution
        retcode = proc.poll()
        if retcode is None:
            return
        if retcode != 0:
            self.logger.warn(
                'Command [%s] exit with code %s.\n'
                '\tSTDOUT:\n%s\n\tSTDERR:\n%s\n'
                % (cmd, retcode,
                   ''.join(writer.stdout().tail(10)),
                   ''.join(writer.stderr().tail(10))))
            with self.failed[0]:
                self.failed[1].append((cmd, retcode, writer))
        else:
            self.logger.info(
                'Command [%s] exit with code 0.' % (cmd))
            with self.finished[0]:
                self.finished[1].append((cmd, retcode, writer))
        self.curr = None
        self.start = None
        self.timeout = None
        try:
            writer.close()
        except Exception as e:
            self.logger.warn('Writer close exception.\n%s'
                             % (traceback.format_exc()))

    def fetch_command(self):
        if len(self.torun[1]) == 0:
            return
        with self.torun[0]:
            if len(self.torun[1]) == 0:
                return
            cmd, writer, timeout = self.torun[1].pop(0)
        if writer is None:
            writer = NLinesStdStringWriter()
        proc = subprocess.Popen(
            shlex.split(cmd), stdout=writer.stdout(), stderr=writer.stderr())
        self.curr = proc, cmd, writer
        self.start = time.time()
        self.timeout = timeout

    def isworking(self):
        return self.curr is not None

    def clear(self):
        if self.curr is not None:
            proc, cmd, writer = self.curr
            proc.kill()
            proc.wait()
            try:
                writer.close()
            except:
                pass
        self.curr = None
        self.start = None
        self.timeout = None

    def close(self):
        self.closed = True
