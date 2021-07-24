import math

from dataclasses import dataclass


@dataclass
class Window:
    width: int = 1500
    height: int = 1100
    resizeable: bool = True
    vsync: bool = False
    refresh_interval: float = 1/120


@dataclass
class Image:
    path: str = 'resources/images/kitten.png'
    width: int = 1
    height: int = 1


@dataclass
class Gameplay:
    num_intended_pieces: int = 16
    nx: int = 4
    ny: int = 4
    piece_rotation: bool = True
    snap_distance_percent: float = 0.5
    big_piece_threshold: int = 50
    pan_speed: float = 0.8

    @property
    def num_pieces(self):
        return self.nx * self.ny

    @property
    def snap_distance(self):
        return self.snap_distance_percent * image.width / self.nx

    def set_dimensions(self):
        """
        Tries to figure out how many columns and rows there should be in a grid
        like jigsaw, given that we want n "almost square" pieces, and the image
        dimensions. Works by defining and evaluating a cost function on a set of
        numbers that is likely to contain a good approximation.
        :return: (nx, ny) tuple, where nx * ny is close to n and nx/ny is close
        to w/h.
        """
        r = image.width / image.height
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


# These will now act as singletons if you import settings as a module.
# Ex:
# from src import settings
# print(settings.window.width)
# > 1500

window = Window()
image = Image()
gameplay = Gameplay()
