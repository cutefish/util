import logging
import time
import unittest

from pyutil.run import Alarm, Pool, OSCmd
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


class TestPool(unittest.TestCase):
    def testRun(self):
        start = time.time()
        with Pool(1) as pool:
            pool.add(OSCmd('python -c "import time; time.sleep(1)"'))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(1, end - start, delta = 0.4)
        start = time.time()
        with Pool(1) as pool:
            pool.add(OSCmd('python -c "import time; time.sleep(1.5)"'))
            pool.add(OSCmd('python -c "import time; time.sleep(1.5)"'))
            pool.add(OSCmd('python -c "import time; time.sleep(1.5)"'))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(4.5, end - start, delta = 1.0)
        start = time.time()
        with Pool(3) as pool:
            pool.add(OSCmd('python -c "import time; time.sleep(1.5)"'))
            pool.add(OSCmd('python -c "import time; time.sleep(1.5)"'))
            pool.add(OSCmd('python -c "import time; time.sleep(1.5)"'))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(1.5, end - start, delta = 0.4)

    def testStress(self):
        with Pool(10) as pool:
            for i in range(99):
                if i % 3 == 0:
                    pool.add(OSCmd('python -c "import sys; sys.exit(3)"'))
                else:
                    pool.add(OSCmd('python -c "import sys; sys.exit(0)"'))
            pool.wait()
        self.assertEqual(66, len(pool.getfinished()))
        self.assertEqual(33, len(pool.getfailed()))

    def testTimeout(self):
        start = time.time()
        with Pool(1) as pool:
            pool.add(OSCmd('python -c "import time; time.sleep(100)"',
                           timeout=1))
            pool.add(OSCmd('python -c "import time; time.sleep(100)"',
                           timeout=3))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(4, end - start, delta = 0.5)
        start = time.time()
        with Pool(2) as pool:
            pool.add(OSCmd('python -c "import time; time.sleep(100)"',
                           timeout=2))
            pool.add(OSCmd('python -c "import time; time.sleep(100)"',
                           timeout=2))
            pool.wait()
        end = time.time()
        self.assertAlmostEqual(2, end - start, delta = 0.5)

    def testOutput(self):
        with Pool(2) as pool:
            pool.add(OSCmd(
                'python -c "import sys; sys.stdout.write(\'stdout\')"'))
            pool.add(OSCmd(
                'python -c "import sys; sys.stderr.write(\'stderr\')"'))
            pool.wait()
        for cmd, retcode, writer in pool.getfinished():
            self.assertEqual(0, retcode)
            if 'stdout' in cmd:
                self.assertEqual('', writer.stderr().getvalue())
                self.assertEqual('stdout', writer.stdout().getvalue())
            else:
                self.assertEqual('', writer.stdout().getvalue())
                self.assertEqual('stderr', writer.stderr().getvalue())

    def testError(self):
        with Pool(2) as pool:
            pool.add(OSCmd('python -c '
                           '"import sys; '
                           'sys.stderr.write(\'Error\'); '
                           'sys.exit(5)"'))
            pool.add(OSCmd('python -c "import sys; '
                           'sys.stdout.write(\'Success\')"'))
            pool.wait()
        cmd, retcode, writer = pool.getfinished()[0]
        self.assertEqual(0, retcode)
        self.assertEqual('Success', writer.stdout().getvalue())
        cmd, retcode, writer = pool.getfailed()[0]
        self.assertEqual(5, retcode)
        self.assertEqual('Error', writer.stderr().getvalue())

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
    ])
    unittest.TextTestRunner().run(suite)
