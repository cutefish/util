import math
import random
import sys

class RandUtil(object):
    @classmethod
    def pick(cls, pool, exclude=None):
        """Pick a random element from pool other than exclude.

        Forever loop may occur if pool == exclude.
        """
        if exclude is None:
            exclude = set([])
        else:
            exclude = set(exclude)
        while True:
            index = random.randint(0, len(pool) - 1)
            result = pool[index]
            if result not in exclude:
                return result

    @classmethod
    def cdf(cls, points):
        points = sorted(points)
        x = []
        y = []
        for i, point in enumerate(points):
            x.append(point)
            y.append(float(i + 1) / len(points))
        return (x, y)


class RollingStats(object):
    def __init__(self):
        self.n = 0
        self.meanx = 0.0
        self.meanx2 = 0.0

    def update(self, value):
        self.n += 1
        self.meanx += float(value - self.meanx) / self.n
        self.meanx2 += float(value * value - self.meanx2) / self.n

    def mean(self):
        return self.meanx

    def var(self):
        return self.meanx2 - (self.meanx)**2

    def std(self, unbiased=False):
        if unbiased:
            return math.sqrt(self.var() * self.n / (self.n - 1))
        else:
            return math.sqrt(self.var())

    def clear(self):
        self.n = 0
        self.meanx = 0.0
        self.meanx2 = 0.0


class RandVar(object):
    class Exponential(RollingStats):
        def __init__(self, lambd, lb=-sys.maxint, ub=sys.maxint):
            super(RandVar.Exponential, self).__init__()
            self.lambd = lambd
            self.lb = lb
            self.ub = ub

        def next(self):
            while True:
                result = random.expovariate(self.lambd)
                if (result >= self.lb ) and (result <= self.ub):
                    self.update(result)
                    return result

    class Normal(RollingStats):
        def __init__(self, mu, sigma, lb=-sys.maxint, ub=sys.maxint):
            super(RandVar.Normal, self).__init__()
            self.mu = mu
            self.sigma = sigma
            self.lb = lb
            self.ub = ub

        def next(self):
            while True:
                result = random.normalvariate(self.mu, self.sigma)
                if (result >= self.lb ) and (result <= self.ub):
                    self.update(result)
                    return result

    class Fixed(RollingStats):
        def __init__(self, value):
            super(RandVar.Fixed, self).__init__()
            self.value = value

        def next(self):
            self.update(self.value)
            return self.value

    class Uniform(RollingStats):
        def __init__(self, lb=0, ub=1.0):
            super(RandVar.Uniform, self).__init__()
            self.lb = lb
            self.ub = ub

        def next(self):
            result = self.lb + random.random() * (self.ub - self.lb)
            self.update(result)
            return result

    class LogNormal(RollingStats):
        def __init__(self, mu, sigma, lb=-sys.maxint, ub=sys.maxint):
            super(RandVar.LogNormal, self).__init__()
            self.mu = mu
            self.sigma = sigma
            self.lb = lb
            self.ub = ub

        def next(self):
            while True:
                result = random.lognormvariate(self.mu, self.sigma)
                if (result >= self.lb ) and (result <= self.ub):
                    self.update(result)
                    return result

        @classmethod
        def ms2mv(cls, mu, sigma):
            mean = math.exp(mu + sigma**2 / 2)
            var = (math.exp(sigma**2) - 1) * math.exp(2 * mu + sigma**2)
            return mean, var

        @classmethod
        def mv2ms(cls, mean, var):
            sigma = math.sqrt(math.log(var / (mean**2) + 1))
            mu = math.log(mean) - sigma**2 / 2
            return mu, sigma

    class Pareto(RollingStats):
        """Shifted type I pareto.

        f(x) = x**(-alpha)
        mean = alpha / (alpha - 1)
        """
        def __init__(self, alpha, lb=-sys.maxint, ub=sys.maxint):
            super(RandVar.Pareto, self).__init__()
            self.alpha = alpha
            self.lb = lb
            self.ub = ub

        def next(self):
            while True:
                result = random.paretovariate(self.alpha)
                if (result >= self.lb ) and (result <= self.ub):
                    self.update(result)
                    return result
        @classmethod
        def m2a(cls, m):
            return float(m) / (m - 1)

        @classmethod
        def a2m(self, alpha):
            return float(alpha) / (alpha - 1)

    class Pdf(RollingStats):
        def __init__(self, freqs, numbers=None):
            if len(freqs) != len(numbers):
                raise ValueError(
                    'length not match, len(freqs)=%s, len(numbers)=%s'
                    % (len(freqs), len(numbers)))
            super(RandVar.Pdf, self).__init__()
            self.probs = self._normalize(freqs)
            self.numbers = numbers

        def next(self):
            r = random.random()
            for i, prob in enumerate(self.probs):
                if r <= prob:
                    if self.numbers is None:
                        self.update(i)
                        return i
                    else:
                        self.update(self.numbers[i])
                        return self.numbers[i]
                r -= prob
            #should not be here
            raise ValueError

        def _normalize(self, freqs):
            probs = []
            s = sum(freqs)
            for freq in freqs:
                probs.append(freq / float(s))
            return probs
