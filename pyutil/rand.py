import random

class RandUtil(object):
    @classmethod
    def pick(cls, pool, exclude=None):
        """Pick a random element from pool other than exclude.

        Forever loop may occur if pool == exclude.
        """
        if exclude is None:
            exclude = set([])
        else:
            exclude = set([exclude])
        while True:
            index = random.randint(0, len(pool) - 1)
            result = pool[index]
            if result not in exclude:
                return result
