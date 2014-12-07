import logging
import multiprocessing
import shlex
import subprocess
import time
import traceback
from threading import Lock, Thread

from pyutil.fio import StdPipeWriter
from pyutil.string import NLinesStdStringWriter

class Alarm(Thread):
    """A background alarm.

    init arguments:
        function: work to do at each alarm time.
        interval: the interval between two alarms.
        at: at time of the alarm.

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
        fetch_succeeded(): return the list of succeeded commands.
        fetch_failed(): return the list of failed commands.
        ntorun(): return number of commands to run.
        clear(): clear the current to run queue and kill the curr works.
        close(): close the pool.
    """
    class QueueFullError(Exception):
        pass

    def __init__(self, nprocs=None, qlen=1000000):
        if nprocs is None:
            nprocs = multiprocessing.cpu_count()
        self.start_time = time.time()
        self.torun = (Lock(), [])
        self.succeeded = (Lock(), [])
        self.failed = (Lock(), [])
        self.qlen = qlen
        self.threads = []
        self.closed = False
        self.logger = logging.getLogger(self.__class__.__name__)
        for i in range(nprocs):
            thread = TaskRunner(self.start_time,
                                 self.torun, self.succeeded, self.failed)
            thread.daemon = True
            self.threads.append(thread)

    def start(self):
        for thread in self.threads:
            thread.start()

    def ntorun(self):
        return len(self.torun[1])

    def add(self, task):
        """Add a task to the queue for processing. """
        if len(self.torun[1]) >= self.qlen:
            raise Pool.QueueFullError()
        with self.torun[0]:
            self.torun[1].append(task)

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
                time.sleep(0.1)
            else:
                break

    def fetch_succeeded(self):
        result = []
        with self.succeeded[0]:
            while len(self.succeeded) != 0:
                result.append(self.succeeded.pop())
        return result.reverse()

    def fetch_failed(self):
        result = []
        with self.failed[0]:
            while len(self.failed) != 0:
                result.append(self.failed.pop())
        return result.reverse()

    def clear(self):
        with self.torun[0]:
            self.torun[1] = []
        for thread in self.threads:
            thread.clear()

    def close(self):
        for thread in self.threads:
            thread.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class Task(object):
    TORUN, RUNNING, FINISHED = range(3)
    def __init__(self):
        self.state = Task.TORUN
        self.start_time = -1
        self.end_time = -1
        self.success = False
        self.errmsg = None

    def run(self):
        pass


class TaskRunner(Thread):
    def __init__(self, start_time, torun, succeeded, failed):
        super(TaskRunner, self).__init__()
        self.start_time = start_time
        self.torun = torun
        self.succeeded = succeeded
        self.failed = failed
        self.closed = False
        self.check_interval = 0.1
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        while not self.closed:
            if len(self.torun[1]) == 0:
                time.sleep(self.check_interval)
                continue
            with self.torun[0]:
                if len(self.torun[1] == 0):
                    continue
                curr = self.torun[1].pop(0)
            try:
                if curr.state != Task.TORUN:
                    raise ValueError('Incorrect task state %s, expected %s'
                                     % (curr.state, Task.TORUN))
                curr.start_time = time.time() - self.start_time
                curr.state = Task.RUNNING
                curr.run()
            except Exception as e:
                self.logger.exception(e)
            finally:
                if not curr.success:
                    self.logger.error('Task %s failed. Error message: %s'
                                      % (curr, curr.errmsg))
                    with self.failed[0]:
                        self.failed.append(curr)
                else:
                    self.logger.info('Task %s succeeded.' % (curr))
                    with self.succeeded[0]:
                        self.succeeded.append(curr)
                curr.end_time = time.time() - self.end_time
                curr.state = Task.FINISHED


class OSCmd(Task):
    def __init__(self, cmd, out_writer, timeout=None):
        super(Task, self).__init__()
        self.cmd = cmd
        self.out_writer = out_writer
        self.timeout = timeout
        self.proc = None
        self.check_interval = 0.1
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        try:
            self.launch()
            self.wait()
        finally:
            self.clear()

    def launch(self):
        if len(self.torun[1]) == 0:
            return
        with self.torun[0]:
            if len(self.torun[1]) == 0:
                return
            cmd, writer, timeout = self.torun[1].pop(0)
            try:
                if writer is None:
                    proc = subprocess.Popen(shlex.split(cmd),
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                    writer = StdPipeWriter(
                        proc, NLinesStdStringWriter(100, 50))
                else:
                    proc = subprocess.Popen(shlex.split(cmd),
                                            stdout=writer.stdout(),
                                            stderr=writer.stderr())
                self.logger.info(
                    'Command [%s > %s] start.' % (cmd, writer.name))
                self.curr = proc, cmd, writer
                self.begin = time.time()
                self.timeout = timeout
            except Exception:
                self.logger.warn('Start command exception.\n%s'
                                 % (traceback.format_exc()))

    def wait(self):
        # check timeout
        if self.timeout is not None:
            curr = time.time() - self.start_time
            if curr > self.timeout:
                self.logger.warn(
                    'Command [%s] time out (%s sec). Kill.' % (cmd, curr))
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
                   ''.join(writer.stdout().tail(50)),
                   ''.join(writer.stderr().tail(50))))
            with self.failed[0]:
                self.failed[1].append((cmd, retcode, writer))
        else:
            self.logger.info(
                'Command [%s] exit with code 0.' % (cmd))
            with self.succeeded[0]:
                self.succeeded[1].append((cmd, retcode, writer))
        self.curr = None
        self.begin = None
        self.timeout = None
        try:
            writer.close()
        except Exception:
            self.logger.warn('Writer close exception.\n%s'
                             % (traceback.format_exc()))

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
        self.begin = None
        self.timeout = None

    def close(self):
        self.closed = True
