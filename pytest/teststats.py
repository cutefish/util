import unittest

from pyutil.stats import RollingStats, RandUtil, RandVar

class TestRollingStats(unittest.TestCase):
    def testRolling(self):
        stats = RollingStats()
        for i in range(10):
            stats.update(i)
        self.assertEqual(4.5, stats.mean())
        self.assertEqual(8.25, stats.var())
        self.assertAlmostEqual(2.87, stats.std(), delta = 0.03)


class TestRandUtil(unittest.TestCase):
    def testPick(self):
        stats = RollingStats()
        pool = range(10)
        for i in range(10000):
            stats.update(RandUtil.pick(pool))
        self.assertAlmostEqual(4.5, stats.mean(), delta = 0.1)
        exclude = [9]
        stats.clear()
        for i in range(10000):
            stats.update(RandUtil.pick(pool, exclude))
        self.assertAlmostEqual(4, stats.mean(), delta = 0.1)

    def testCdf(self):
        points = [3, 2, 3, 2, 3, 2, 3, 2, 3, 1]
        x, y = RandUtil.cdf(points)
        self.assertItemsEqual(points, x)
        self.assertItemsEqual(map(lambda x : float(x) / 10, range(1, 11)), y)


class TestRandVar(unittest.TestCase):
    def testRandVar(self):
        v = RandVar.Exponential(1.0)
        for i in range(10000):
            v.next()
        self.assertAlmostEqual(1.0, v.mean(), delta = 0.1)
        self.assertAlmostEqual(1.0, v.var(), delta = 0.1)
        v = RandVar.Normal(1.0, 1.0)
        for i in range(10000):
            v.next()
        self.assertAlmostEqual(1.0, v.mean(), delta = 0.1)
        self.assertAlmostEqual(1.0, v.var(), delta = 0.1)
        v = RandVar.Fixed(1.0)
        for i in range(10000):
            v.next()
        self.assertAlmostEqual(1.0, v.mean(), delta = 0.1)
        self.assertAlmostEqual(0.0, v.var(), delta = 0.1)
        v = RandVar.Uniform(6, 12)
        for i in range(10000):
            v.next()
        self.assertAlmostEqual(9.0, v.mean(), delta = 0.1)
        self.assertAlmostEqual(3.0, v.var(), delta = 0.1)
        v = RandVar.LogNormal(1.0, 1.0)
        for i in range(50000):
            v.next()
        mean, var = RandVar.LogNormal.ms2mv(1.0, 1.0)
        mu, sigma = RandVar.LogNormal.mv2ms(mean, var)
        self.assertAlmostEqual(mean, v.mean(), delta = 5)
        self.assertAlmostEqual(var, v.var(), delta = 5)
        self.assertAlmostEqual(mu, 1.0, delta = 0.1)
        self.assertAlmostEqual(sigma, 1.0, delta = 0.1)
        v = RandVar.Pareto(6.0)
        for i in range(10000):
            v.next()
        self.assertAlmostEqual(RandVar.Pareto.a2m(6.0), v.mean(), delta = 0.1)
        self.assertAlmostEqual(6.0 / 5.0, RandVar.Pareto.a2m(6.0), delta = 0.1)
        self.assertAlmostEqual(1.5, v.var() + (v.mean())**2, delta = 0.1)
        v = RandVar.Pdf([50, 20, 30], [10, 20, 30])
        for i in range(10000):
            v.next()
        self.assertAlmostEqual(18, v.mean(), delta = 0.5)
        self.assertAlmostEqual(50 + 80 + 270 - 18**2, v.var(), delta = 0.5)


if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestRollingStats),
        unittest.TestLoader().loadTestsFromTestCase(TestRandUtil),
        unittest.TestLoader().loadTestsFromTestCase(TestRandVar),
    ])
    unittest.TextTestRunner().run(suite)
