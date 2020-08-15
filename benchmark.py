import random
import time

import pyglet
from tqdm import tqdm

from model import Model
from view import Piece


pyglet.resource.path = ['resources']
pyglet.resource.reindex()


def create_piece(self, pid, polygon, position, width, height):
    self.pieces[pid] = Piece(
        pid,
        polygon,
        position,
        width,
        height,
        self.texture,
        self.window.batch,
        self.group
    )


def setup(image_name, n_a, n_b):
    texture = pyglet.resource.image(image_name).get_texture()
    model = Model(texture.width, texture.height, n_a + n_b)
    batch = pyglet.graphics.Batch()
    group_a = pyglet.graphics.Group()
    group_b = pyglet.graphics.Group()

    foo = list(model.pieces.items())
    random.shuffle(foo)
    pieces_a = [
        Piece(
            pid,
            piece.polygon,
            (piece.x, piece.y, piece.z),
            piece.width,
            piece.height,
            texture,
            batch,
            group_a
        ) for pid, piece in tqdm(foo[:n_a])
    ]

    pieces_b = [
        Piece(
            pid,
            piece.polygon,
            (piece.x, piece.y, piece.z),
            piece.width,
            piece.height,
            texture,
            batch,
            group_b
        ) for pid, piece in tqdm(foo[n_a:])
    ]

    return pieces_a, pieces_b


def move(pieces_a, pieces_b):
    piece_a = pieces_a[random.randint(0, len(pieces_a) - 1)]
    piece_b = pieces_b[random.randint(0, len(pieces_b) - 1)]
    group_a = piece_a.group

    t0 = time.time()
    piece_a.group = piece_b.group
    t1 = time.time()
    piece_a.group = group_a
    return t1-t0


if __name__ == '__main__':
    """
    This benchmark creates a bunch of jigsaw pieces and divides them into two 
    groups. It then measures the time it takes to move a random piece from one 
    group to the other. The piece group is reset after each movement. 
    
    The result seems to be that it takes approximately 1ms or less for a single 
    piece to move, regardless of how many pieces are already in the group that 
    is moved from or to. 
    
    This result indicates that we should be able to schedule events where 
    large pieces with many translation groups are slowly merged, one or a few 
    pieces at a time, so that eventually there is at most a single group for 
    each piece. 
    """
    a, b = setup('hongkong.jpg', 10000, 10000)
    for _ in range(1000):
        print(move(a, b))
