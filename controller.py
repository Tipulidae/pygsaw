import os
import glob

import pyglet
from compress_pickle import dump, load

from model import Model
from view import View, Jigsaw


class Controller:
    def __init__(self, puzzle_settings, window_settings):
        self.model = None
        self.view = None
        self.big_piece_threshold = puzzle_settings['big_piece_threshold']
        self.window = Jigsaw(**window_settings)
        self.window.push_handlers(self)
        self.image_path = None
        self._new_puzzle(
            f"resources/{puzzle_settings['image_path']}",
            puzzle_settings['num_pieces'],
            puzzle_settings['piece_rotation']
        )

    def _new_puzzle(self, image_path, num_intended_pieces, piece_rotation=False):
        self.image_path = image_path
        texture = pyglet.image.load(image_path).get_texture()

        self.model = Model()
        self.model.reset(
            image_path,
            texture.width,
            texture.height,
            num_intended_pieces,
            piece_rotation=piece_rotation
        )
        self.view = View(
            texture,
            image_path,
            self.big_piece_threshold,
            self.model.trays.visible_trays,
            piece_data=self.model.get_piece_data(),
            window=self.window
        )

        self.model.push_handlers(self)
        self.view.push_handlers(self)
        self.view.hand.push_handlers(self)

        self.model.toggle_pause(False)
        self.view.toggle_pause(False)

    def on_new_game(self, image_path, num_pieces):
        self.window.pop_handlers()
        self.view.destroy_pieces()
        self._new_puzzle(image_path, num_pieces)

    def on_quicksave(self):
        print("quicksave!")
        dump(
            obj=self.model.to_dict(),
            path=f'.savegame/'
                 f'{os.path.basename(self.image_path)[:-4]}_'
                 f'{self.model.num_pieces}.sav',
            compression='bz2',
            set_default_extension=False
        )

    def on_quickload(self):
        print("quickload!")
        self.window.pop_handlers()
        self.view.destroy_pieces()

        data = load(
            _most_recently_modified_file_in_folder('.savegame'),
            compression='bz2',
            set_default_extension=False
        )
        self.model = Model.from_dict(data)
        self.image_path = data['image_path']
        texture = pyglet.image.load(self.image_path).get_texture()

        self.view = View(
            texture,
            self.image_path,
            self.big_piece_threshold,
            self.model.trays.visible_trays,
            piece_data=self.model.get_piece_data(),
            window=self.window
        )

        self.model.push_handlers(self)
        self.view.push_handlers(self)
        self.view.hand.push_handlers(self)
        self.model.timer.start()

    def on_mouse_down(self, x, y, is_shift):
        if (piece := self.model.piece_at_coordinate(x, y)) is not None:
            self.view.mouse_down_on_piece(piece.pid)
        elif is_shift:
            self.view.start_selection_box(x, y)
        else:
            self.view.drop_everything()

    def on_mouse_up(self, x, y):
        pass

    def on_scroll(self, x, y, direction):
        self.model.rotate_piece_at_coordinate(x, y, direction)

    def on_piece_rotated(self, pid, rotation, pivot):
        self.view.rotate_piece(pid, rotation, pivot)

    def on_view_pieces_moved(self, pids, dx, dy):
        self.model.move_pieces(pids, dx, dy)

    def on_view_select_pieces(self, pids):
        self.model.move_pieces_to_top(pids)

    def on_z_levels_changed(self, msg):
        self.view.remember_new_z_levels(msg)

    def on_piece_moved(self, pid, x, y, z):
        self.view.move_piece(pid, x, y, z)

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

    def on_info(self):
        self.view.print_info(
            elapsed_seconds=self.model.elapsed_seconds,
            percent_complete=self.model.percent_complete
        )

    def on_pause(self, is_paused):
        self.model.toggle_pause(is_paused)
        self.view.toggle_pause(is_paused)

    def on_win(self, elapsed_seconds, num_pieces):
        self.view.game_over(elapsed_seconds, num_pieces)


def _most_recently_modified_file_in_folder(path):
    files = glob.glob(f"{path}/*.sav")
    files.sort(key=os.path.getmtime)
    return files[-1]
