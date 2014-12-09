import logging
import multiprocessing
import shlex
import subprocess
import time
import Queue
from threading import Thread

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
        wait(): wait until all the commands are proccessed.
        fetch_succeeded(): return the list of succeeded commands.
        fetch_failed(): return the list of failed commands.
        qlen(): return number of commands to run.
        close(): close the pool.
    """
    def __init__(self, nthreads=None, qlen=1000000):
        if nthreads is None:
            nthreads = multiprocessing.cpu_count()
        self.start_time = time.time()
        self.torun = Queue.Queue(qlen)
        self.succeeded = Queue.Queue()
        self.failed = Queue.Queue()
        self.threads = []
        self.closed = False
        self.logger = logging.getLogger(self.__class__.__name__)
        for i in range(nthreads):
            thread = TaskRunner(self.start_time,
                                 self.torun, self.succeeded, self.failed)
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
        return self.torun.qsize()

    def add(self, task, block=True, timeout=None):
        """Add a task to the queue for processing. """
        self.torun.put(task, block, timeout)

    def wait(self):
        self.torun.join()

    def fetch_succeeded(self):
        result = []
        try:
            while True:
                result.append(self.succeeded.get(False))
                self.succeeded.task_done()
        except Queue.Empty:
            pass
        return result

    def fetch_failed(self):
        result = []
        try:
            while True:
                result.append(self.failed.get(False))
                self.failed.task_done()
        except Queue.Empty:
            pass
        return result

    def close(self):
        for thread in self.threads:
            thread.close()


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

    def kill(self):
        pass


class TaskRunner(Thread):
    def __init__(self, start_time, torun, succeeded, failed):
        super(TaskRunner, self).__init__()
        self.start_time = start_time
        self.torun = torun
        self.succeeded = succeeded
        self.failed = failed
        self.curr = None
        self.closed = False
        self.check_interval = 0.1
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        while not self.closed:
            try:
                while (self.curr is None) and (not self.closed):
                    try:
                        self.curr = self.torun.get(block=True, timeout=1)
                    except Queue.Empty:
                        pass
                if self.closed:
                    break
                if self.curr.state != Task.TORUN:
                    raise ValueError('Task state not Task.TORUN: state=%s'
                                     % (self.curr.state))
                self.curr.start_time = time.time() - self.start_time
                self.curr.state = Task.RUNNING
                self.logger.info('Task [%s] starts at %s.'
                                 % (self.curr, self.curr.start_time))
                self.curr.run()
            except Exception as e:
                self.logger.exception(e)
            finally:
                if self.curr is not None:
                    if self.curr.state == Task.RUNNING:
                        self.torun.task_done()
                    self.curr.end_time = time.time() - self.start_time
                    self.curr.state = Task.FINISHED
                    if not self.curr.success:
                        self.logger.error(
                            'Task [%s] failed at %s. Error message: %s.'
                            % (self.curr, self.curr.end_time,
                               self.curr.errmsg))
                        self.failed.put(self.curr)
                    else:
                        self.logger.info(
                            'Task [%s] succeeded at %s.'
                            % (self.curr, self.curr.end_time))
                        self.succeeded.put(self.curr)
                self.curr = None

    def close(self):
        if self.curr is not None:
            self.curr.kill()
        self.closed = True
        print 'closed'


class OSCmd(Task):
    def __init__(self, cmd, out_writer, timeout=None):
        super(Task, self).__init__()
        self.cmd = cmd
        self.writer = out_writer
        self.timeout = timeout
        self.proc = None
        self.check_interval = 0.1
        self.killed = False
        self.logger = logging.getLogger(self.__class__.__name__)

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
        retcode = self.proc.poll()
        if retcode is None:
            return True
        if retcode != 0:
            self.success = False
            self.errmsg=(
                'Command [%s] exit with code %s.\n'
                '\tSTDOUT:\n%s\n\tSTDERR:\n%s\n'
                % (self.cmd, retcode,
                   ''.join(self.writer.stdout().tail(50)),
                   ''.join(self.writer.stderr().tail(50))))
        else:
            self.success = True
        return False
