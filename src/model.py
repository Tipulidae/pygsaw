import math
import random
import itertools
import time
import pathlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Set, Dict

from pyglet.window import EventDispatcher
from tqdm import tqdm
from pyqtree import Index as QuadTree

import src.settings as settings
from src.database import save_statistics
from src.bezier import Point, Rectangle, make_random_edges, bounding_box, \
    point_in_polygon


class Model(EventDispatcher):
    def __init__(self):
        self.pieces = None
        self.trays = None
        self.quadtree = None
        self.current_max_z_level = settings.gameplay.num_pieces
        self.timer = Timer()
        self.start_time = datetime.now()
        self.cheated = False

    def reset(self):
        self.current_max_z_level = settings.gameplay.num_pieces
        self.trays = Tray(num_pids=settings.gameplay.num_pieces)
        self.quadtree = QuadTree(bbox=(-100000, -100000, 100000, 100000))
        self.pieces = make_jigsaw_cut(
            settings.image.width,
            settings.image.height,
            settings.gameplay.nx,
            settings.gameplay.ny,
            settings.gameplay.piece_rotation
        )
        for piece in tqdm(self.pieces.values(), desc="Building quad-tree"):
            self.quadtree.insert(piece, piece.bbox)

    def to_dict(self):
        return {
            'gameplay_settings': asdict(settings.gameplay),
            'window_settings': asdict(settings.window),
            'image_settings': asdict(settings.image),
            'pieces': self.pieces,
            'trays': self.trays,
            'current_max_z_level': self.current_max_z_level,
            'elapsed_seconds': self.elapsed_seconds,
            'cheated': self.cheated,
            'start_time': self.start_time,
        }

    @classmethod
    def from_dict(cls, data):
        model = cls()
        model.pieces = data['pieces']
        model.trays = data['trays']
        model.current_max_z_level = data['current_max_z_level']
        model.timer = Timer(data['elapsed_seconds'])
        model.cheated = data['cheated']
        model.start_time = data['start_time']
        model.quadtree = QuadTree(bbox=(-100000, -100000, 100000, 100000))
        for piece in tqdm(model.pieces.values(), desc="Building quad-tree"):
            model.quadtree.insert(piece, piece.bbox)
        return model

    def piece_at_coordinate(self, x, y):
        return self._top_piece_at_location(x, y)

    def piece_ids_in_rect(self, rect):
        def to_pid(piece):
            return piece.pid

        pieces_in_rect = self.quadtree.intersect(
            bbox=(rect.left, rect.bottom, rect.right, rect.top)
        )

        return list(self.trays.filter_visible(map(to_pid, pieces_in_rect)))

    def merge_random_pieces(self, n):
        self.cheated = True
        n = min(n, len(self.pieces) - 1)
        for _ in range(n):
            piece = random.choice(list(self.pieces.values()))
            neighbour = self.pieces[random.choice(list(piece.neighbours))]
            self.quadtree.remove(piece, piece.bbox)

            if (rotation := neighbour.rotation - piece.rotation) != 0:
                piece.rotate(rotation, Point(0, 0))
            piece.x = neighbour.x
            piece.y = neighbour.y
            self.dispatch_event(
                'on_piece_moved',
                piece.pid,
                piece.x,
                piece.y,
                piece.z,
                piece.rotation
            )
            self._merge_pieces(piece, neighbour)
            self.quadtree.insert(piece, piece.bbox)

    def move_pieces(self, pids, dx, dy):
        snap_to_neighbours = len(pids) == 1
        for pid in pids:
            self.move_piece(pid, dx, dy, snap_to_neighbours=snap_to_neighbours)

    def move_piece(self, pid, dx, dy, snap_to_neighbours=True):
        piece = self.pieces[pid]
        self.quadtree.remove(piece, piece.bbox)
        piece.x += dx
        piece.y += dy
        if snap_to_neighbours:
            self.snap_piece_to_neighbours(piece)
        self.quadtree.insert(piece, piece.bbox)

    def snap_piece_to_neighbours(self, piece):
        for neighbour_pid in piece.neighbours:
            if not self.trays.is_visible(neighbour_pid):
                continue

            neighbour = self.pieces[neighbour_pid]
            if piece.rotation != neighbour.rotation:
                continue

            dist = Point.dist(
                Point(piece.x, piece.y),
                Point(neighbour.x, neighbour.y)
            )
            if dist < settings.gameplay.snap_distance:
                piece.x = neighbour.x
                piece.y = neighbour.y
                neighbour.z = piece.z
                self.dispatch_event(
                    'on_piece_moved',
                    piece.pid,
                    piece.x,
                    piece.y,
                    piece.z,
                    piece.rotation
                )

                self._merge_pieces(piece, neighbour)

    def set_piece_position(self, piece, x, y):
        self.quadtree.remove(piece, piece.bbox)
        piece.x = x
        piece.y = y

        self.dispatch_event(
            'on_piece_moved',
            piece.pid,
            piece.x,
            piece.y,
            piece.z,
            piece.rotation
        )

        self.quadtree.insert(piece, piece.bbox)

    def spread_out(self, pids):
        single_pieces = list(filter(
            lambda piece: len(piece.members) == 1,
            map(lambda pid: self.pieces[pid], pids)
        ))
        if len(single_pieces) < 1:
            return

        n = math.ceil(math.sqrt(len(single_pieces)))

        left = min(map(
            lambda piece: piece.bounding_box.left + piece.x,
            single_pieces,
        ))
        bottom = min(map(
            lambda piece: piece.bounding_box.bottom + piece.y,
            single_pieces
        ))

        for i, piece in enumerate(single_pieces):
            self.set_piece_position(
                piece,
                left + 2 * piece.width * (i % n) - piece.bounding_box.left,
                bottom + 2 * piece.height * (i // n) - piece.bounding_box.bottom
            )

    def move_pieces_to_top(self, pids):
        new_z_levels = list(range(
            self.current_max_z_level,
            self.current_max_z_level + len(pids)
        ))
        self.current_max_z_level += len(pids)

        sorted_pieces = sorted(
            [self.pieces[pid] for pid in pids],
            key=lambda p: p.z
        )

        msg = []
        for z, piece in zip(new_z_levels, sorted_pieces):
            piece.z = z
            msg.append((z, piece.pid))

        self.dispatch_event(
            'on_z_levels_changed',
            msg
        )

    def move_pieces_to_tray(self, tray, pids):
        self.trays.move_pids_to_tray(tray=tray, pids=pids)
        if self._tray_is_hidden(tray):
            self.dispatch_event(
                'on_visibility_changed',
                tray,
                False,
                self.trays.hidden_pieces
            )

    def rotate_piece_at_coordinate(self, x, y, direction):
        if not settings.gameplay.piece_rotation:
            return
        if (piece := self.piece_at_coordinate(x, y)) is None:
            return

        self.move_pieces_to_top([piece.pid])
        self.quadtree.remove(piece, piece.bbox)
        piece.rotate(direction, Point(x, y))
        self.dispatch_event(
            'on_piece_rotated',
            piece.pid,
            piece.rotation,
            piece.position
        )
        self.snap_piece_to_neighbours(piece)
        self.quadtree.insert(piece, piece.bbox)

    def get_hidden_pieces(self):
        return self.trays.hidden_pieces

    def get_piece_data(self):
        data = []
        for pid, piece in self.pieces.items():
            piece_data = piece.data
            piece_data['tray'] = self.trays.pid_to_tray[pid]
            data.append(piece_data)

        return data

    def toggle_visibility(self, tray):
        self.trays.toggle_visibility(tray)
        self.dispatch_event(
            'on_visibility_changed',
            tray,
            self._tray_is_visible(tray),
            self.trays.hidden_pieces
        )

    def toggle_pause(self, is_paused):
        if is_paused:
            self.timer.pause()
        else:
            self.timer.start()

    @property
    def elapsed_seconds(self):
        return self.timer.elapsed_seconds

    @property
    def percent_complete(self):
        total_moves = settings.gameplay.num_pieces - 1
        moves_made = settings.gameplay.num_pieces - len(self.pieces)
        return 100 * moves_made / total_moves

    def _tray_is_visible(self, tray):
        return tray in self.trays.visible_trays

    def _tray_is_hidden(self, tray):
        return not self._tray_is_visible(tray)

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
        self.trays.merge_pids(p1.pid, p2.pid)
        self.dispatch_event(
            'on_pieces_merged',
            p1.pid,
            p2.pid
        )

        self._check_game_over()

    def _pieces_at_location(self, x, y):
        for piece in self.quadtree.intersect(bbox=(x, y, x, y)):
            if (self.trays.is_visible(piece.pid)
                    and piece.contains(Point(x, y), settings.gameplay.nx)):
                yield piece

    def _top_piece_at_location(self, x, y):
        return max(
            self._pieces_at_location(x, y),
            key=(lambda p: p.z),
            default=None
        )

    def _check_game_over(self):
        if len(self.pieces) == 1:
            self.timer.pause()
            self.dispatch_event('on_win', self.elapsed_seconds)
            save_statistics(
                image_path=settings.image.path,
                num_pieces=settings.gameplay.num_pieces,
                num_intended_pieces=settings.gameplay.num_intended_pieces,
                image_width=settings.image.width,
                image_height=settings.image.height,
                snap_distance=settings.gameplay.snap_distance,
                start_time=self.start_time,
                piece_rotation=settings.gameplay.piece_rotation,
                cheated=self.cheated,
                elapsed_seconds=self.elapsed_seconds
            )

    def __eq__(self, other):
        return (
            self.current_max_z_level == other.current_max_z_level,
            self.pieces == other.pieces,
            self.trays == other.trays,
            self.quadtree == other.quadtree,
        )

    def __str__(self):
        image_name = pathlib.Path(settings.image.path).stem
        return f"{image_name}_{settings.gameplay.num_pieces}"


Model.register_event_type('on_piece_rotated')
Model.register_event_type('on_piece_moved')
Model.register_event_type('on_pieces_merged')
Model.register_event_type('on_z_levels_changed')
Model.register_event_type('on_visibility_changed')
Model.register_event_type('on_win')


@dataclass
class Piece:
    pid: int
    polygon: Dict[int, List[Point]]
    bounding_box: Rectangle
    origin: Point
    neighbours: Set[int]
    members: Set[int]
    width: int = 200
    height: int = 200
    x: float = 0
    y: float = 0
    z: float = 0
    rotation: int = 0

    def rotate(self, direction, pivot):
        self.rotation = (self.rotation + direction) % 4
        angle = direction * math.pi / 2
        p = self.position.rotate(angle, pivot)
        self.x = p.x
        self.y = p.y

        self.bounding_box.flip(direction)

    @property
    def bbox(self):
        # The bounding-box translated by piece position
        return (
            self.x + self.bounding_box.left,
            self.y + self.bounding_box.bottom,
            self.x + self.bounding_box.right,
            self.y + self.bounding_box.top
        )

    @property
    def position(self):
        return Point(self.x, self.y)

    @property
    def data(self):
        return {
            'pid': self.pid,
            'polygons': self.polygon,
            'position': (self.x, self.y, self.z),
            'rotation': self.rotation,
            'width': self.width,
            'height': self.height
        }

    def merge(self, other):
        assert isinstance(other, Piece)
        self.members = self.members.union(other.members)
        self.neighbours = self.neighbours.union(other.neighbours)
        self.neighbours.remove(self.pid)
        self.neighbours.remove(other.pid)
        self.polygon = {**self.polygon, **other.polygon}
        self.bounding_box = Rectangle(
            left=min(self.bounding_box.left, other.bounding_box.left),
            right=max(self.bounding_box.right, other.bounding_box.right),
            bottom=min(self.bounding_box.bottom, other.bounding_box.bottom),
            top=max(self.bounding_box.top, other.bounding_box.top)
        )

    def contains(self, point: Point, nx: int) -> bool:
        point = point - self.position

        # Instead of rotating the polygons, we rotate the point in the
        # opposite direction.
        angle = -self.rotation * math.pi / 2
        point = point.rotate(angle, Point(0, 0))

        pid = point_to_pid(point, nx, self.width, self.height)
        offset = Point(
            self.width * (1 + pid % nx),
            self.height * (1 + pid // nx)
        )

        neighbour = closest_neighbour_pid(
            pid,
            point - offset,
            self.width,
            self.height,
            nx
        )

        if pid in self.members and neighbour in self.members:
            return True
        elif pid in self.members and neighbour not in self.members:
            return point_in_polygon(point, self.polygon[pid])
        elif pid not in self.members and neighbour in self.members:
            return point_in_polygon(point, self.polygon[neighbour])
        else:
            return False


class Tray:
    def __init__(self, num_pids, num_trays=10):
        self.trays = {tray: set() for tray in range(num_trays)}
        self.trays[0] = set(range(num_pids))
        self.visible_trays = set(range(num_trays))
        self.pid_to_tray = {pid: 0 for pid in range(num_pids)}

    def is_visible(self, pid):
        return (
            pid in self.pid_to_tray and
            self.pid_to_tray[pid] in self.visible_trays
        )

    def filter_visible(self, pids):
        for pid in pids:
            if self.is_visible(pid):
                yield pid

    def move_pids_to_tray(self, pids, tray):
        for pid in pids:
            old_tray = self.pid_to_tray[pid]
            self.pid_to_tray[pid] = tray
            self.trays[old_tray].remove(pid)
            self.trays[tray].add(pid)

    def merge_pids(self, _, pid2):
        self.trays[self.pid_to_tray[pid2]].remove(pid2)
        self.pid_to_tray.pop(pid2)

    def toggle_visibility(self, tray):
        if tray in self.visible_trays:
            self.visible_trays.remove(tray)
        else:
            self.visible_trays.add(tray)

    @property
    def hidden_pieces(self):
        hidden = tuple(
            pieces for tray, pieces in self.trays.items()
            if tray not in self.visible_trays
        )
        return set().union(*hidden)

    def __eq__(self, other):
        return (
            self.trays == other.trays and
            self.visible_trays == other.visible_trays and
            self.pid_to_tray == other.pid_to_tray
        )


class Timer:
    def __init__(self, elapsed_seconds=0):
        self.seconds = elapsed_seconds
        self.start_time = 0
        self.is_running = False

    def start(self):
        self.is_running = True
        self.start_time = time.time()

    def pause(self):
        self.update()
        self.is_running = False

    def reset(self):
        self.is_running = False
        self.seconds = 0
        self.start_time = 0

    def update(self):
        if self.is_running:
            current_time = time.time()
            self.seconds += current_time - self.start_time
            self.start_time = current_time

    @property
    def elapsed_seconds(self):
        self.update()
        return self.seconds


def make_jigsaw_cut(image_width, image_height, nx, ny, random_rotation=False):
    # TODO: with global settings, the input params are no longer needed?
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

    pieces = {}
    for pid in tqdm(range(num_pieces), desc="Designing pieces"):
        piece = Piece(
            pid=pid,
            polygon={pid: (polygon := piece_contour(pid))},
            bounding_box=bounding_box(polygon),
            origin=(origin := origin_of_pid(pid, nx, width, height)),
            neighbours=create_neighbours(pid, num_pieces, nx),
            members={pid},
            width=width,
            height=height,
            x=random.randint(0, int(image_width * 2)) - origin.x,
            y=random.randint(0, int(image_height * 2)) - origin.y,
            z=pid
        )
        if random_rotation:
            piece.rotate(random.randint(0, 3), piece.position)

        pieces[pid] = piece

    return pieces


def create_neighbours(pid, n, nx):
    return set(filter(
        lambda p:
            (0 <= p < n) and
            (pid // nx == p // nx or pid % nx == p % nx),
        [pid - nx, pid - 1, pid + 1, pid + nx]
    ))


def point_to_pid(p, nx, width, height):
    return int(
        ((p.x - width / 2) // width) % nx +
        ((p.y - height / 2) // height) * nx
    )


def origin_of_pid(pid, nx, width, height):
    return Point(width * (pid % nx), height * (pid // nx))


def closest_neighbour_pid(pid, point, width, height, nx):
    point = point.dot(Point(height/width, 1))
    if abs(point.x) < point.y:  # North
        return pid + nx
    elif abs(point.x) < -point.y:  # South
        return pid - nx
    elif abs(point.y) < point.x:  # East
        return pid + 1
    else:  # West
        return pid - 1
