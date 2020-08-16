import math
import time
import random
import itertools
from dataclasses import dataclass
from typing import List, Set

import vecrec
import glooey
from pyglet.window import EventDispatcher
from tqdm import tqdm
from pyqtree import Index as QuadTree

from bezier import Point, make_random_edges, bounding_box


@glooey.register_event_type('on_model_piece_moved', 'on_pieces_merged')
class Model(EventDispatcher):
    def __init__(
            self,
            image_width,
            image_height,
            num_pieces,
            snap_distance_percent=0.5):
        self.nx, self.ny, self.num_pieces = create_jigsaw_dimensions(num_pieces)
        self.image_width = image_width
        self.image_height = image_height
        self.snap_distance = snap_distance_percent * image_width / self.nx
        self.pieces = make_jigsaw_cut(
            self.image_width,
            self.image_height,
            self.nx,
            self.ny
        )
        self.quadtree = QuadTree(bbox=(-100000, -100000, 100000, 100000))
        for piece in tqdm(self.pieces.values(), desc="Building quad-tree"):
            self.quadtree.insert(piece, piece.bbox)

        self.current_max_z_level = self.num_pieces

    def piece_at_coordinate(self, x, y):
        # Find top-most piece at given coordinate and return its pid
        # If no piece is at the coordinate, return None
        piece = self._top_piece_at_location(x, y)
        if piece is None:
            return None
        else:
            return piece.pid

    def start_selection_box(self, x, y):
        # New selection box with one corner at x, y
        pass

    def select_piece(self, pid):
        # The piece was marked as selected in the view
        piece = self.pieces[pid]
        if piece.z < self.current_max_z_level - 1:
            piece.z = self.current_max_z_level
            self.current_max_z_level += 1
            self.dispatch_event(
                'on_model_piece_moved',
                pid,
                piece.x,
                piece.y,
                piece.z
            )

    def merge_random_pieces(self, n):
        n = min(n, len(self.pieces) - 1)
        for _ in range(n):
            piece = random.choice(list(self.pieces.values()))
            neighbour = self.pieces[random.choice(list(piece.neighbours))]
            self.quadtree.remove(piece, piece.bbox)

            piece.x = neighbour.x
            piece.y = neighbour.y
            self.dispatch_event(
                'on_model_piece_moved',
                piece.pid,
                piece.x,
                piece.y,
                piece.z
            )
            self._merge_pieces(piece, neighbour)
            self.quadtree.insert(piece, piece.bbox)

    def move_piece(self, pid, dx, dy):
        piece = self.pieces[pid]
        self.quadtree.remove(piece, piece.bbox)
        piece.x += dx
        piece.y += dy

        # Snap!
        for neighbour_pid in piece.neighbours:
            neighbour = self.pieces[neighbour_pid]
            dist = Point.dist(
                Point(piece.x, piece.y),
                Point(neighbour.x, neighbour.y)
            )
            if dist < self.snap_distance:
                piece.x = neighbour.x
                piece.y = neighbour.y
                self.dispatch_event(
                    'on_model_piece_moved',
                    pid,
                    piece.x,
                    piece.y,
                    piece.z
                )
                self._merge_pieces(piece, neighbour)

        self.quadtree.insert(piece, piece.bbox)

        self.dispatch_event(
            'on_model_piece_moved',
            pid,
            piece.x,
            piece.y,
            piece.z
        )

    def _merge_pieces(self, p1, p2):
        # Merges p2 into p1
        p1.merge(p2)
        self.pieces.pop(p2.pid)
        p2.neighbours.remove(p1.pid)
        for neighbour_pid in p2.neighbours:
            neighbour = self.pieces[neighbour_pid]
            neighbour.neighbours.remove(p2.pid)
            neighbour.neighbours.add(p1.pid)

        self.quadtree.remove(p2, p2.bbox)
        self.dispatch_event(
            'on_pieces_merged',
            p1.pid,
            p2.pid
        )

    def _pieces_at_location(self, x, y):
        for piece in self.quadtree.intersect(bbox=(x, y, x, y)):
            yield piece

    def _top_piece_at_location(self, x, y):
        return max(
            self._pieces_at_location(x, y),
            key=(lambda p: p.z),
            default=None
        )


@dataclass
class Piece:
    pid: int
    polygon: List[Point]
    bounding_box: vecrec.Rect
    origin: Point
    neighbours: Set[int]
    members: Set[int]
    width: int = 200
    height: int = 200
    x: float = 0
    y: float = 0
    z: float = 0

    @property
    def bbox(self):
        # The bounding-box translated by piece position
        return (
            self.x + self.bounding_box.left,
            self.y + self.bounding_box.bottom,
            self.x + self.bounding_box.right,
            self.y + self.bounding_box.top
        )

    def merge(self, other):
        assert isinstance(other, Piece)
        self.members = self.members.union(other.members)
        self.neighbours = self.neighbours.union(other.neighbours)
        self.neighbours.remove(self.pid)
        self.neighbours.remove(other.pid)
        self.bounding_box = vecrec.Rect.from_sides(
            left=min(self.bounding_box.left, other.bounding_box.left),
            right=max(self.bounding_box.right, other.bounding_box.right),
            bottom=min(self.bounding_box.bottom, other.bounding_box.bottom),
            top=max(self.bounding_box.top, other.bounding_box.top)
        )


def make_jigsaw_cut(image_width, image_height, nx, ny):
    num_edges = 2 * nx * ny - nx - ny
    num_pieces = nx * ny
    nv = (nx - 1) * ny
    width = image_width // nx
    height = image_height // ny

    edges = make_random_edges(num_edges)

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
        offset = Point(
            width * (pid % nx) + width / 2,
            height * (pid // nx) + height / 2
        )
        contour = [
            edges[get_epid(pid, "N")].stretch(width, height).translate(offset),
            edges[get_epid(pid, "E")].stretch(height, width).rotate().translate(offset + Point(width, 0)),
            edges[get_epid(pid, "S")].stretch(width, height).translate(offset + Point(0, height)).reverse(),
            edges[get_epid(pid, "W")].stretch(height, width).rotate().translate(offset).reverse()
        ]
        return list(itertools.chain.from_iterable([
            edge.evaluate(10) for edge in contour]))

    pieces = {pid: Piece(
        pid=pid,
        polygon=(polygon := piece_contour(pid)),
        bounding_box=bounding_box(polygon),
        origin=(origin := Point(width * (pid % nx), height * (pid // nx))),
        neighbours=create_neighbours(pid, num_pieces, nx),
        members={pid},
        width=width,
        height=height,
        x=random.randint(0, int(image_width * 2)) - origin.x,
        y=random.randint(0, int(image_height * 2)) - origin.y,
        z=pid
    ) for pid in tqdm(range(num_pieces), desc="Designing pieces")}

    return pieces


def create_neighbours(pid, n, nx):
    return set(filter(
        lambda p:
            (0 <= p < n) and
            (pid // nx == p // nx or pid % nx == p % nx),
        [pid - nx, pid - 1, pid + 1, pid + nx]
    ))


def create_jigsaw_dimensions(num_pieces):
    nx = ny = math.floor(math.sqrt(num_pieces))
    return nx, ny, num_pieces
