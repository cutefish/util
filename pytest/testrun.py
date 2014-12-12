import logging
import thread
import time
import unittest
from threading import Thread

from pyutil.run import Alarm, Pool, OSCmd, Task
from pyutil.fio import StdFileWriter

logging.basicConfig(level=logging.INFO)

class TestAlarm(unittest.TestCase):
    def testAlarm(self):
        count = [0]
        def add_count():
            count[0] += 1
        alarm = Alarm(add_count, 0.5, at=1)
        alarm.start()
        time.sleep(3.3)
        alarm.stop()
        self.assertEqual(count[0], 5)


class KeyboardInterruptThread(Thread):
    def __init__(self, after=1):
        super(KeyboardInterruptThread, self).__init__()
        self.after = after

    def run(self):
        time.sleep(self.after)
        thread.interrupt_main()


class SleepTask(Task):
    def __init__(self, count):
        super(SleepTask, self).__init__()
        self.count = count
        self.killed = False

    def run(self):
        while (not self.killed) and (self.count > 0):
            time.sleep(1)
            self.count -= 1
        if not self.killed:
            self.success = True
        else:
            self.logger.info('count=%s' % (self.count))

    def kill(self):
        self.logger.info('sleep task killed.')
        self.killed = True

    def __str__(self):
        return 'sleep task'


class AddTask(Task):
    def __init__(self, val1, val2, add):
        super(AddTask, self).__init__()
        self.result = -1
        self.val1 = val1
        self.val2 = val2
        self.add = add

    def run(self):
        if self.add:
            for i in range(1000):
                self.result += self.val1 + self.val2
            self.success = True

    def __str__(self):
        return 'add task'


class TestPool(unittest.TestCase):
    def testKeyboardInterrupt(self):
        after = 3
        thread = KeyboardInterruptThread(after)
        start = time.time()
        try:
            with Pool(1) as pool:
                pool.add(SleepTask(10))
                thread.start()
                pool.wait()
        except KeyboardInterrupt:
            pass
        end = time.time()
        self.assertAlmostEqual(after, end - start, delta = 0.5)
        time.sleep(2) # ensure the task runner is done
        failed = pool.fetch_failed()
        self.assertEqual(1, len(failed))

    def testRun(self):
        start = time.time()
        with Pool(1) as pool:
            for i in range(5):
                pool.add(SleepTask(1))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(5, end - start, delta = 0.5)
        start = time.time()
        with Pool(5) as pool:
            for i in range(5):
                pool.add(SleepTask(1))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(1, end - start, delta = 0.5)

    def testStress(self):
        with Pool(4) as pool:
            for i in range(99):
                if i % 3 == 0:
                    pool.add(AddTask(1, 2, False))
                else:
                    pool.add(AddTask(1, 2, True))
            pool.wait()
        stasks = pool.fetch_succeeded()
        ftasks = pool.fetch_failed()
        self.assertEqual(66, len(stasks))
        self.assertEqual(33, len(ftasks))


class TestOSCmd(unittest.TestCase):
    def testRun(self):
        start = time.time()
        with Pool(1) as pool:
            for i in range(5):
                pool.add(OSCmd('python -c "import time; time.sleep(1)"'))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(5, end - start, delta = 3)
        start = time.time()
        with Pool(5) as pool:
            for i in range(5):
                pool.add(OSCmd('python -c "import time; time.sleep(1)"'))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(1, end - start, delta = 3)

    def testTimeout(self):
        start = time.time()
        with Pool(1) as pool:
            pool.add(OSCmd('python -c "import time; time.sleep(100)"',
                           timeout=1))
            pool.add(OSCmd('python -c "import time; time.sleep(100)"',
                           timeout=3))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(4, end - start, delta = 2.5)
        start = time.time()
        with Pool(2) as pool:
            pool.add(OSCmd('python -c "import time; time.sleep(100)"',
                           timeout=2))
            pool.add(OSCmd('python -c "import time; time.sleep(100)"',
                           timeout=2))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(2, end - start, delta = 2.5)

    def testOutput(self):
        with Pool(2) as pool:
            pool.add(OSCmd(
                'python -c "import sys; sys.stdout.write(\'stdout\')"'))
            pool.add(OSCmd(
                'python -c "import sys; sys.stderr.write(\'stderr\')"'))
            pool.wait()
        for task in pool.fetch_succeeded():
            self.assertEqual(0, task.retcode)
            if 'stdout' in task.cmd:
                self.assertEqual('', task.writer.stderr().getvalue())
                self.assertEqual('stdout', task.writer.stdout().getvalue())
            else:
                self.assertEqual('', task.writer.stdout().getvalue())
                self.assertEqual('stderr', task.writer.stderr().getvalue())

    def testError(self):
        with Pool(2) as pool:
            pool.add(OSCmd('python -c '
                           '"import sys; '
                           'sys.stderr.write(\'Error\'); '
                           'sys.exit(5)"'))
            pool.add(OSCmd('python -c "import sys; '
                           'sys.stdout.write(\'Success\')"'))
            pool.wait()
        task = pool.fetch_succeeded()[0]
        self.assertEqual(0, task.retcode)
        self.assertEqual('Success', task.writer.stdout().getvalue())
        task = pool.fetch_failed()[0]
        self.assertEqual(5, task.retcode)
        self.assertEqual('Error', task.writer.stderr().getvalue())

    def testFile(self):
        with Pool(1) as pool:
            pool.add(OSCmd('python -c "import sys; '
                           'sys.stdout.write(\'Success\'); '
                           'sys.stderr.write(\'Error\'); '
                           'sys.exit(-1)"',
                           StdFileWriter('/tmp/test')))
            pool.wait()
        with open('/tmp/test/stdout', 'r') as fh:
            result = fh.read()
            self.assertEqual('Success', result)
        with open('/tmp/test/stderr', 'r') as fh:
            result = fh.read()
            self.assertEqual('Error', result)


if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestAlarm),
        unittest.TestLoader().loadTestsFromTestCase(TestPool),
        unittest.TestLoader().loadTestsFromTestCase(TestOSCmd),
    ])
    unittest.TextTestRunner().run(suite)
