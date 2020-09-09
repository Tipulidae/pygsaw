import pyglet

from model import Model
from view import View, Jigsaw


class Controller:
    def __init__(self, puzzle_settings, window_settings):
        self.model = Model()
        self.model.push_handlers(self)
        self.view = None
        self.big_piece_threshold = puzzle_settings['big_piece_threshold']
        self.window = Jigsaw(**window_settings)
        self.window.push_handlers(self)
        self._new_puzzle(
            f"pygsaw/resources/{puzzle_settings['image_path']}",
            puzzle_settings['num_pieces'],
        )

    def _new_puzzle(self, image_path, num_pieces):
        texture = pyglet.image.load(image_path).get_texture()
        self.model.reset(texture.width, texture.height, num_pieces)
        self.view = View(
            texture,
            self.big_piece_threshold,
            piece_data=[piece.data for piece in self.model.pieces.values()],
            window=self.window
        )

        self.view.push_handlers(self)
        self.view.hand.push_handlers(self)

    def on_new_game(self, image_path, num_pieces):
        self.window.pop_handlers()
        self.view.destroy_pieces()
        self._new_puzzle(image_path, num_pieces)

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

    def on_view_spread_out(self, pids):
        self.model.spread_out(pids)

    def on_cheat(self, n):
        self.model.merge_random_pieces(n)

    def on_selection_box(self, rect):
        pids = self.model.piece_ids_in_rect(rect)
        self.view.select_pieces(pids)

    def on_move_pieces_to_tray(self, tray, pids):
        self.model.move_pieces_to_tray(tray, pids)

    def on_toggle_visibility(self, tray):
        self.model.toggle_visibility(tray)

    def on_visibility_changed(self, tray, is_visible, hidden_pieces):
        self.view.set_visibility(tray, is_visible)
        self.view.drop_specific_pieces_from_hand(hidden_pieces)
