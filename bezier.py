from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple
import itertools
import random

from tqdm import tqdm


@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0

    def tuple(self):
        return self.x, self.y

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)


class Direction(Enum):
    FORWARD = 0
    BACKWARD = 1


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
            )
        )

    def translate(self, p):
        return Bezier(
            self.p1 + p,
            self.p2 + p,
            self.p3 + p,
            self.p4 + p
        )

    def rotate(self):
        return Bezier(
            Point(self.p1.y, self.p1.x),
            Point(self.p2.y, self.p2.x),
            Point(self.p3.y, self.p3.x),
            Point(self.p4.y, self.p4.x)
        )

    def reverse(self):
        return Bezier(self.p4, self.p3, self.p2, self.p1)

    def stretch(self, p):
        return Bezier(
            Point(p.x * self.p1.x / 200, p.y * self.p1.y / 200),
            Point(p.x * self.p2.x / 200, p.y * self.p2.y / 200),
            Point(p.x * self.p3.x / 200, p.y * self.p3.y / 200),
            Point(p.x * self.p4.x / 200, p.y * self.p4.y / 200)
        )

    def flip(self, y):
        return Bezier(
            Point(self.p1.x, y - self.p1.y),
            Point(self.p2.x, y - self.p2.y),
            Point(self.p3.x, y - self.p3.y),
            Point(self.p4.x, y - self.p4.y),
        )


class Edge:
    def evaluate(self, n=10):
        return []

    def rotate(self):
        # Rotate the edge 90 degrees counter-clockwise around the origin
        pass

    def translate(self, p: Point):
        pass

    def stretch(self, p: Point):
        pass

    def reverse(self):
        pass

    def flip(self, y):
        pass


@dataclass
class FlatEdge(Edge):
    p1: Point
    p2: Point

    def evaluate(self, n=10):
        return [self.p1, self.p2]

    def reverse(self):
        return FlatEdge(self.p2, self.p1)

    def rotate(self):
        return FlatEdge(
            self.p1,
            Point(self.p2.y, self.p2.x)
        )

    def translate(self, p):
        return FlatEdge(
            self.p1 + p,
            self.p2 + p
        )

    def stretch(self, p):
        return FlatEdge(
            Point(p.x * self.p1.x / 200, p.y * self.p1.y / 200),
            Point(p.x * self.p2.x / 200, p.y * self.p2.y / 200)
        )

    def flip(self, y):
        return FlatEdge(
            Point(self.p1.x, y - self.p1.y),
            Point(self.p2.x, y - self.p2.y)
        )


@dataclass
class CurvedEdge(Edge):
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

    def reverse(self):
        return CurvedEdge(
            self.b4.reverse(),
            self.b3.reverse(),
            self.b2.reverse(),
            self.b1.reverse()
        )

    def rotate(self):
        # Rotate the edge 90 degrees counter-clockwise around the origin
        return CurvedEdge(
            self.b1.rotate(),
            self.b2.rotate(),
            self.b3.rotate(),
            self.b4.rotate()
        )

    def translate(self, p):
        return CurvedEdge(
            self.b1.translate(p),
            self.b2.translate(p),
            self.b3.translate(p),
            self.b4.translate(p)
        )

    def stretch(self, p):
        return CurvedEdge(
            self.b1.stretch(p),
            self.b2.stretch(p),
            self.b3.stretch(p),
            self.b4.stretch(p)
        )

    def flip(self, y):
        # Parry for PIL's inverted coordinate system
        return CurvedEdge(
            self.b1.flip(y),
            self.b2.flip(y),
            self.b3.flip(y),
            self.b4.flip(y),
        )

    @classmethod
    def from_minimal(cls, pts):
        return cls(
            Bezier(Point(0, 0), pts[0], pts[1], pts[2]),
            Bezier(pts[2], Point(2*pts[2].x - pts[1].x, 2*pts[2].y - pts[1].y), pts[3], pts[4]),
            Bezier(pts[4], Point(2*pts[4].x - pts[3].x, 2*pts[4].y - pts[3].y), pts[5], pts[6]),
            Bezier(pts[6], Point(2*pts[6].x - pts[5].x, 2*pts[6].y - pts[5].y), pts[7], Point(200, 0))
        )

    @classmethod
    def random(cls):
        default_points = [
            (50, 20),
            (100, 25),
            (80, 0),
            (70, -40),
            (100, -40),
            (140, -25),
            (120, 0),
            (150, 20)
        ]
        random_points = [
            Point(
                x + random.randint(-5, 5),
                y + random.randint(-5, 5))
            for (x, y) in default_points]

        # 50% chance to flip the edge around the x-axis, effectively making the
        # "ear" point the other direction.
        if random.random() < 0.5:
            random_points = [Point(p.x, -p.y) for p in random_points]

        return cls.from_minimal(random_points)


@dataclass
class Contour:
    outer: List[Edge]
    inner: List[Edge]

    def evaluate(self, n=10):
        return list(itertools.chain.from_iterable([
            edge.evaluate(n)
            for edge in self.outer
        ]))


@dataclass
class Piece:
    contour: Contour
    origin: Point


def make_jigsaw_cut(width, height, nx, ny):
    num_edges = 2 * nx * ny - nx - ny
    num_pieces = nx * ny
    nv = (nx - 1) * ny

    edges = {i: CurvedEdge.random() for i in range(num_edges)}
    edges[-1] = FlatEdge(Point(0, 0), Point(200, 0))

    def get_epid(pid, orientation):
        if orientation == "N" and pid >= nx:
            return pid - nx + nv
        elif orientation == "W" and pid % nx:
            return pid - (pid // nx) - 1
        elif orientation == "S" and pid < num_pieces - nx:
            return pid + nv
        elif orientation == "E" and pid % nx != nx - 1:
            return pid - (pid // nx)
        return -1

    def piece_contour(pid):
        offset = Point(width/2, height/2)
        return Contour(
            outer=[
                edges[get_epid(pid, "N")].stretch(Point(width, height)).translate(offset),
                edges[get_epid(pid, "E")].stretch(Point(height, width)).rotate().translate(offset + Point(width, 0)),
                edges[get_epid(pid, "S")].stretch(Point(width, height)).translate(offset + Point(0, height)).reverse(),
                edges[get_epid(pid, "W")].stretch(Point(height, width)).rotate().translate(offset).reverse()

            ],
            inner=[]
        )

    pieces = {pid: Piece(
        contour=piece_contour(pid),
        origin=Point(width * (pid % nx), height * (1 - pid // nx))
    ) for pid in tqdm(range(num_pieces), desc="Designing pieces")}

    return pieces
