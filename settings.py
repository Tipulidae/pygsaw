import math

from dataclasses import dataclass


@dataclass
class Settings:
    image_path: str
    num_intended_pieces: int = 16
    nx: int = 0
    ny: int = 0
    image_width: int = 0
    image_height: int = 0
    snap_distance_percent: float = 0.5
    piece_rotation: bool = True
    big_piece_threshold: int = 3

    @property
    def num_pieces(self):
        return self.nx * self.ny

    def set_dimensions(self, w, h):
        """
        Tries to figure out how many columns and rows there should be in a grid
        like jigsaw, given that we want n "almost square" pieces, and the image
        dimensions. Works by defining and evaluating a cost function on a set of
        numbers that is likely to contain a good approximation.
        :param w: Width of the jigsaw image
        :param h: Height of the jigsaw image
        :return: (nx, ny) tuple, where nx * ny is close to n and nx/ny is close to
        w/h.
        """
        r = w / h
        n = self.num_intended_pieces
        sqrtn = math.sqrt(n)
        ny1 = math.floor(sqrtn/r)
        nx1 = math.floor(sqrtn*r)

        nx_min = min(nx1, math.floor(sqrtn)) - 1
        nx_max = max(nx1, math.ceil(sqrtn)) + 1
        ny_min = min(ny1, math.floor(sqrtn)) - 1
        ny_max = max(ny1, math.ceil(sqrtn)) + 1

        combinations = [
            (x, y)
            for x in range(nx_min, nx_max+1)
            for y in range(ny_min, ny_max+1)
        ]

        def cost(nxny):
            # I want to penalize wrong number of pieces more than wrong aspect
            # ratio of pieces
            nx, ny = nxny
            return abs((r * ny/nx)**2 - 1) + 3 * abs((nx * ny / n) ** 2 - 1)

        self.nx, self.ny = min([(nx, ny) for nx, ny in combinations], key=cost)
        self.image_width = w
        self.image_height = h

    @property
    def snap_distance(self):
        return self.snap_distance_percent * self.image_width / self.nx

    def __eq__(self, other):
        return (
            self.image_path == other.image_path,
            self.num_intended_pieces == other.num_intended_pieces,
            self.nx == other.nx,
            self.ny == other.ny,
            self.image_width == other.image_width,
            self.image_height == other.image_height,
            self.snap_distance_percent == other.snap_distance_percent,
            self.piece_rotation == other.piece_rotation,
            self.big_piece_threshold == other.big_piece_threshold
        )
