import pyglet
from tqdm import tqdm

from model import Model
from view import View
from textures import make_normal_map


class Controller:
    def __init__(
            self,
            image_path='kitten.png',
            num_pieces=4,
            big_piece_threshold=100,
            **window_settings):
        # texture = pyglet.resource.image(image_path).get_texture()
        texture = pyglet.image.load(f'pygsaw/resources/{image_path}').get_texture()
        self.model = Model(texture.width, texture.height, num_pieces)
        normal_map = make_normal_map(
            self.model.pieces,
            texture.width,
            texture.height,
            self.model.pieces[0].width,
            self.model.pieces[0].height,
        )
        self.view = View(
            texture,
            normal_map,
            big_piece_threshold,
            **window_settings
        )
        self.view.push_handlers(self)
        self.view.hand.push_handlers(self)
        self.model.push_handlers(self)
        self.view.window.push_handlers(self)

        for pid, piece in tqdm(self.model.pieces.items(),
                               desc="Drawing pieces"):
            self.view.create_piece(
                pid,
                piece.polygon[pid],
                (piece.x, piece.y, piece.z),
                piece.width,
                piece.height
            )

    def on_mouse_down(self, x, y, is_shift):
        if (piece := self.model.piece_at_coordinate(x, y)) is not None:
            self.view.mouse_down_on_piece(piece.pid)
        elif is_shift:
            self.view.start_selection_box(x, y)
        else:
            self.view.drop_everything()

    def on_mouse_up(self, x, y):
        pass

    def on_view_pieces_moved(self, pids, dx, dy):
        self.model.move_pieces(pids, dx, dy)

    def on_view_select_pieces(self, pids):
        self.model.move_pieces_to_top(pids)

    def on_z_levels_changed(self, msg):
        self.view.remember_new_z_levels(msg)

    def on_snap_piece_to_position(self, pid, x, y, z):
        self.view.snap_piece_to_position(pid, x, y, z)

    def on_pieces_merged(self, pid1, pid2):
        self.view.merge_pieces(pid1, pid2)

    def on_cheat(self, n):
        self.model.merge_random_pieces(n)

    def on_selection_box(self, rect):
        pids = self.model.piece_ids_in_rect(rect)
        self.view.select_pieces(pids)

    def on_move_pieces_to_tray(self, group, pids):
        self.model.move_pieces_to_tray(group, pids)
        hidden_pieces = self.model.get_hidden_pieces()
        self.view.drop_specific_pieces_from_hand(hidden_pieces)

    def on_toggle_visibility(self, tray):
        self.model.toggle_visibility(tray)

    def on_set_visibility(self, tray, is_visible):
        self.view.set_visibility(tray, is_visible)
        hidden_pieces = self.model.get_hidden_pieces()
        self.view.drop_specific_pieces_from_hand(hidden_pieces)
