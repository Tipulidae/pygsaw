import itertools
import random
import math
from dataclasses import dataclass
from typing import List
from abc import ABC, abstractmethod


@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0

    def tuple(self):
        return self.x, self.y

    @staticmethod
    def dist(p1, p2):
        return math.sqrt(
            (p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2
        )

    def dot(self, p):
        return Point(self.x * p.x, self.y * p.y)

    def __add__(self, other):
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y)
        elif isinstance(other, (float, int)):
            return Point(self.x + other, self.y + other)
        else:
            raise TypeError()

    def __sub__(self, other):
        if isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y)
        elif isinstance(other, (float, int)):
            return Point(self.x - other, self.y - other)
        else:
            raise TypeError()

    def __mul__(self, other):
        if isinstance(other, (float, int)):
            return Point(self.x * other, self.y * other)
        else:
            raise TypeError()


@dataclass
class Rectangle:
    left: float = 0
    right: float = 0
    top: float = 0
    bottom: float = 0


@dataclass
class Bezier:
    p1: Point = Point(0, 0)
    p2: Point = Point(0, 0)
    p3: Point = Point(0, 0)
    p4: Point = Point(0, 0)

    def evaluate(self, n=10) -> List[Point]:
        """
        Evaluates the Bezier curve n times. Although the parameterization
        parameter is evenly spaced, this doesn't mean that the points along
        the curve will be equidistant.

        Will not include the last point of the curve.
        :param n: Number of points to sample
        :return: List of n Points along the Bezier curve
        """
        return [
            self.at(t/n) for t in range(n)
        ]

    def at(self, t: float) -> Point:
        return (
            self.p1 * (1 - t) ** 3 +
            self.p2 * 3 * (1 - t) ** 2 * t +
            self.p3 * 3 * (1 - t) * t ** 2 +
            self.p4 * t ** 3
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

    def stretch(self, x, y):
        return Bezier(
            Point(x * self.p1.x / 200, y * self.p1.y / 200),
            Point(x * self.p2.x / 200, y * self.p2.y / 200),
            Point(x * self.p3.x / 200, y * self.p3.y / 200),
            Point(x * self.p4.x / 200, y * self.p4.y / 200)
        )

    def flip(self, y):
        return Bezier(
            Point(self.p1.x, y - self.p1.y),
            Point(self.p2.x, y - self.p2.y),
            Point(self.p3.x, y - self.p3.y),
            Point(self.p4.x, y - self.p4.y),
        )


class Edge(ABC):
    @abstractmethod
    def evaluate(self, n=10) -> List[Point]:
        ...

    @abstractmethod
    def rotate(self):
        # Rotate the edge 90 degrees counter-clockwise around the origin
        ...

    @abstractmethod
    def translate(self, p: Point):
        ...

    @abstractmethod
    def stretch(self, x, y):
        ...

    @abstractmethod
    def reverse(self):
        ...

    @abstractmethod
    def flip(self, y):
        # Mirror in the x-axis
        ...


@dataclass
class FlatEdge(Edge):
    p1: Point
    p2: Point

    def evaluate(self, n=10):
        return [self.p1]

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

    def stretch(self, x, y):
        return FlatEdge(
            Point(x * self.p1.x / 200, y * self.p1.y / 200),
            Point(x * self.p2.x / 200, y * self.p2.y / 200)
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

    def stretch(self, x, y):
        return CurvedEdge(
            self.b1.stretch(x, y),
            self.b2.stretch(x, y),
            self.b3.stretch(x, y),
            self.b4.stretch(x, y)
        )

    def flip(self, y):
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
            Bezier(pts[2], Point(2 * pts[2].x - pts[1].x, 2 * pts[2].y - pts[1].y), pts[3], pts[4]),
            Bezier(pts[4], Point(2 * pts[4].x - pts[3].x, 2 * pts[4].y - pts[3].y), pts[5], pts[6]),
            Bezier(pts[6], Point(2 * pts[6].x - pts[5].x, 2 * pts[6].y - pts[5].y), pts[7], Point(200, 0))
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


def make_random_edges(num_edges):
    edges = {i: CurvedEdge.random() for i in range(num_edges)}
    edges[-1] = FlatEdge(Point(0, 0), Point(200, 0))
    return edges


# This is the winding algorithm, adapted from
# http://geomalgorithms.com/a03-_inclusion.html
def point_in_polygon(p, polygon):
    def is_left(p0: Point, p1: Point, p2: Point) -> float:
        return (p1.x - p0.x) * (p2.y - p0.y) - (p2.x - p0.x) * (p1.y - p0.y)

    n = len(polygon) - 1
    winding_number = 0
    for i in range(n):
        if polygon[i].y <= p.y:
            if polygon[i + 1].y > p.y:
                if is_left(polygon[i], polygon[i + 1], p) > 0:
                    winding_number += 1
        elif polygon[i + 1].y <= p.y:
            if is_left(polygon[i], polygon[i + 1], p) < 0:
                winding_number -= 1

    return winding_number != 0


def bounding_box(polygon):
    left = bottom = math.inf
    right = top = -math.inf
    for p in polygon:
        if p.x < left:
            left = p.x
        elif p.x > right:
            right = p.x
        if p.y < bottom:
            bottom = p.y
        elif p.y > top:
            top = p.y

    return Rectangle(
        left=left,
        right=right,
        top=top,
        bottom=bottom
    )


def center_point(points):
    box = bounding_box(points)
    return Point(
        (box.left + box.right) / 2,
        (box.top + box.bottom) / 2
    )


def rotate_points(points, pivot, angle):
    c = math.cos(angle)
    s = math.sin(angle)
    rotated_points = []
    for p in points:
        p -= pivot
        p = Point(p.x*c - p.y*s, p.x*s + p.y*c)
        rotated_points.append(p + pivot)

    return rotated_points
