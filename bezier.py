from dataclasses import dataclass
import itertools


@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0

    def tuple(self):
        return self.x, self.y

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)


@dataclass
class Bezier:
    p1: Point = Point(0, 0)
    p2: Point = Point(0, 0)
    p3: Point = Point(0, 0)
    p4: Point = Point(0, 0)

    def evaluate(self, n=10):
        return [
            self.at(t/(n-1)) for t in range(n)
        ]

    def at(self, t: float):
        return Point(
            (
                (1 - t) ** 3 * self.p1.x +
                3 * (1 - t) ** 2 * t * self.p2.x +
                3 * (1 - t) * t ** 2 * self.p3.x +
                t ** 3 * self.p4.x
            ),
            (
                (1 - t) ** 3 * self.p1.y +
                3 * (1 - t) ** 2 * t * self.p2.y +
                3 * (1 - t) * t ** 2 * self.p3.y +
                t ** 3 * self.p4.y
            ),
        )


@dataclass
class Edge:
    b1: Bezier
    b2: Bezier
    b3: Bezier
    b4: Bezier

    def evaluate(self, n=10):
        return list(itertools.chain.from_iterable([
            self.b1.evaluate(n),
            self.b2.evaluate(n),
            self.b3.evaluate(n),
            self.b4.evaluate(n)
        ]))
