import logging
import multiprocessing
import shlex
import subprocess
import time
from collections import deque
from threading import Thread, Condition

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
    """A pool of threads to run the tasks.

    init arguments:
        nthreads: number of threads.
        qlen: max number of tasks in the queue.

    methods:
        start(): start the pool.
        add(): add a command to the queue for processing.
            raise Pool.Full exception if queue is full.
        wait(): wait until all the commands are proccessed.
        fetch_succeeded(): return the list of succeeded commands.
        fetch_failed(): return the list of failed commands.
        qlen(): return number of commands to run.
        close(): close the pool.
    """
    class Full(Exception):
        pass

    def __init__(self, nthreads=None, qlen=1000000):
        if nthreads is None:
            nthreads = multiprocessing.cpu_count()
        self.t_start = time.time()
        self.torun = deque()
        self.succeeded = deque()
        self.failed = deque()
        self.threads = []
        self.maxqlen = qlen
        self.new = Condition()
        self.done = Condition()
        self.closed = False
        self.logger = logging.getLogger(self.__class__.__name__)
        for i in range(nthreads):
            thread = TaskRunner(self)
            thread.daemon = True
            self.threads.append(thread)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def start(self):
        for thread in self.threads:
            thread.start()

    def qlen(self):
        return len(self.torun)

    def add(self, task):
        """Add a task to the queue for processing. """
        with self.new:
            if self.qlen() > self.maxqlen:
                raise Pool.Full
            self.torun.append(task)
            self.new.notify()

    def wait(self):
        """Wait until all the tasks are proccessed."""
        while True:
            with self.new:
                blocking = False
                if self.qlen() != 0:
                    blocking = True
                for thread in self.threads:
                    if thread.isworking():
                        blocking = True
                if not blocking:
                    break
                with self.done:
                    self.done.wait(1)

    def fetch_succeeded(self):
        """Pop out all tasks that have succeeded."""
        result = []
        with self.done:
            try:
                while True:
                    result.append(self.succeeded.popleft())
            except IndexError:
                pass
        return result

    def fetch_failed(self):
        """Pop out all tasks that have failed."""
        result = []
        with self.done:
            try:
                while True:
                    result.append(self.failed.popleft())
            except IndexError:
                pass
        return result

    def close(self):
        for thread in self.threads:
            thread.close()

class Task(object):
    TORUN, RUNNING, FINISHED = range(3)
    def __init__(self):
        self.state = Task.TORUN
        self.t_start = -1
        self.t_end = -1
        self.success = False
        self.errmsg = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        pass

    def kill(self):
        pass


class TaskRunner(Thread):
    def __init__(self, pool):
        super(TaskRunner, self).__init__()
        self.pool = pool
        self.curr = None
        self.closed = False
        self.check_interval = 0.1
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        while not self.closed:
            try:
                with self.pool.new:
                    if self.pool.qlen() == 0:
                        self.pool.new.wait(1)
                        continue
                    self.curr = self.pool.torun.popleft()
                if self.curr.state != Task.TORUN:
                    raise ValueError('Task state not Task.TORUN: state=%s'
                                     % (self.curr.state))
                self.curr.t_start = time.time() - self.pool.t_start
                self.curr.state = Task.RUNNING
                self.logger.info('Task [%s] starts at %s.'
                                 % (self.curr, self.curr.t_start))
                self.curr.run()
            except Exception as e:
                self.logger.exception(e)
            finally:
                if self.curr is not None:
                    if self.curr.state != Task.RUNNING:
                        self.logger.warn(
                            'Task state not Task.RUNNING: state=%s'
                            % (self.curr.state))
                    self.curr.t_end = time.time() - self.pool.t_start
                    self.curr.state = Task.FINISHED
                    if not self.curr.success:
                        self.logger.error(
                            'Task [%s] failed at %s. Error message: %s.'
                            % (self.curr, self.curr.t_end,
                               self.curr.errmsg))
                        with self.pool.done:
                            self.pool.failed.append(self.curr)
                            self.pool.done.notify()
                    else:
                        self.logger.info(
                            'Task [%s] succeeded at %s.'
                            % (self.curr, self.curr.t_end))
                        with self.pool.done:
                            self.pool.succeeded.append(self.curr)
                            self.pool.done.notify()
                self.curr = None

    def close(self):
        if self.curr is not None:
            self.curr.kill()
        self.closed = True

    def isworking(self):
        return self.curr is not None


class OSCmd(Task):
    def __init__(self, cmd, out_writer=None, timeout=None):
        super(OSCmd, self).__init__()
        self.cmd = cmd
        self.writer = out_writer
        self.timeout = timeout
        self.proc = None
        self.check_interval = 0.1
        self.killed = False
        self.start_time = -1
        self.retcode = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def __str__(self):
        return ('%s > %s' % (self.cmd, self.writer))

    def run(self):
        try:
            self.launch()
            while self.wait():
                time.sleep(self.check_interval)
        finally:
            if self.proc is not None:
                self.proc.kill()
            if self.writer is not None:
                self.writer.close()

    def launch(self):
        if self.killed:
            return
        if self.writer is None:
            self.proc = subprocess.Popen(shlex.split(self.cmd),
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
            self.writer = StdPipeWriter(
                self.proc, NLinesStdStringWriter(100, 50))
        else:
            self.proc = subprocess.Popen(shlex.split(self.cmd),
                                         stdout=self.writer.stdout(),
                                         stderr=self.writer.stderr())
        self.start_time = time.time()

    def wait(self):
        # check timeout
        if self.timeout is not None:
            curr = time.time() - self.start_time
            if curr > self.timeout:
                self.logger.warn(
                    'Command [%s] time out (%s sec). Kill.'
                    % (self.cmd, curr))
                self.proc.kill()
                self.proc.wait()
        # check execution
        self.retcode = self.proc.poll()
        if self.retcode is None:
            return True
        if self.retcode != 0:
            self.success = False
            self.errmsg=(
                'Command [%s] exit with code %s.\n'
                '\tSTDOUT:\n%s\n\tSTDERR:\n%s\n'
                % (self.cmd, self.retcode,
                   ''.join(self.writer.stdout().tail(50)),
                   ''.join(self.writer.stderr().tail(50))))
        else:
            self.success = True
        return False

    def kill(self):
        if self.proc is not None:
            self.proc.kill()
