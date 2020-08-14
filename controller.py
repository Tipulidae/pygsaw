import pyglet
from tqdm import tqdm

from model import Model
from view import View


class Controller:
    def __init__(
            self,
            image_path='kitten.png',
            num_pieces=16,
            big_piece_threshold=100,
            **window_settings):
        texture = pyglet.resource.image(image_path).get_texture()
        self.model = Model(texture.width, texture.height, num_pieces)
        self.view = View(texture, big_piece_threshold, **window_settings)
        self.view.push_handlers(self)
        self.model.push_handlers(self)
        self.view.window.push_handlers(self)

        for pid, piece in tqdm(self.model.pieces.items(),
                               desc="Drawing pieces"):
            self.view.create_piece(
                pid,
                piece.polygon,
                (piece.x, piece.y, piece.z),
                piece.width,
                piece.height
            )

    def on_mouse_down(self, x, y):
        pid = self.model.piece_at_coordinate(x, y)
        if pid is not None:
            self.model.select_piece(pid)
            self.view.select_piece(pid)
        else:
            self.model.start_selection_box(x, y)

    def on_mouse_up(self, x, y):
        pass

    def on_view_piece_dropped(self, pid, dx, dy):
        self.model.move_piece(pid, dx, dy)

    def on_model_piece_moved(self, pid, x, y, z):
        self.view.move_piece(pid, x, y, z)

    def on_pieces_merged(self, pid1, pid2):
        self.view.merge_pieces(pid1, pid2)

    def on_cheat(self, n):
        self.model.merge_random_pieces(n)
