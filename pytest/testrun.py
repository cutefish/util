import time
import unittest

from pyutil.run import Alarm, Pool

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
    pass


if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestAlarm),
        unittest.TestLoader().loadTestsFromTestCase(TestPool),
    ])
    unittest.TextTestRunner().run(suite)
