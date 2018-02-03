import time

class Timeit:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start


if __name__ == "__main__":
    with Timeit() as t:
        for i in range(1000):
            i**1000000
    print("took {:.3f} seconds".format(t.interval))
