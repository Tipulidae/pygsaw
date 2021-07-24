import os
import glob

import pyglet
from compress_pickle import dump, load

from src.model import Model
from src.view import View, Jigsaw
import src.settings as settings


class Controller:
    def __init__(self):
        self.window = Jigsaw()
        self.window.push_handlers(self)
        self.model = None
        self.view = None
        self._new_puzzle()

    def _new_puzzle(self):
        texture = pyglet.image.load(settings.image.path).get_texture()
        settings.image.width = texture.width
        settings.image.height = texture.height
        settings.gameplay.set_dimensions()

        self.model = Model()
        self.model.reset()
        self.view = View(self.window)
        self.view.reset(
            texture,
            self.model.get_piece_data(),
            self.model.trays.visible_trays,

        )

        self.model.push_handlers(self)
        self.view.push_handlers(self)
        self.view.hand.push_handlers(self)

        self.model.toggle_pause(False)
        self.view.toggle_pause(False)

    def on_new_game(self, s):
        self.window.pop_handlers()
        self.view.destroy_pieces()

        settings.image.path = s['image_path']
        settings.gameplay.num_intended_pieces = s['num_intended_pieces']
        settings.gameplay.piece_rotation = s['piece_rotation']
        self._new_puzzle()

    def on_quicksave(self):
        print("quicksave!")
        if not os.path.exists('saves'):
            os.makedirs('saves')

        dump(
            obj=self.model.to_dict(),
            path=f'saves/{self.model}.sav',
            compression='bz2',
            set_default_extension=False
        )

    def on_quickload(self):
        print("quickload!")
        self.window.pop_handlers()
        self.view.destroy_pieces()

        data = load(
            _most_recently_modified_file_in_folder('saves'),
            compression='bz2',
            set_default_extension=False
        )
        settings.gameplay = settings.Gameplay(**data['gameplay_settings'])
        settings.window = settings.Window(**data['window_settings'])
        settings.image = settings.Image(**data['image_settings'])

        self.model = Model.from_dict(data)
        texture = pyglet.image.load(settings.image.path).get_texture()

        self.view = View(self.window)
        self.view.reset(
            texture=texture,
            piece_data=self.model.get_piece_data(),
            visible_trays=self.model.trays.visible_trays,
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

    def on_piece_rotated(self, pid, rotation, position):
        self.view.rotate_piece(pid, rotation, position)

    def on_view_pieces_moved(self, pids, dx, dy):
        self.model.move_pieces(pids, dx, dy)

    def on_view_select_pieces(self, pids):
        self.model.move_pieces_to_top(pids)

    def on_z_levels_changed(self, msg):
        self.view.remember_new_z_levels(msg)

    def on_piece_moved(self, pid, x, y, z, r):
        self.view.move_piece(pid, x, y, z, r)

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

    def on_win(self, elapsed_seconds):
        self.view.game_over(elapsed_seconds)


def _most_recently_modified_file_in_folder(path):
    files = glob.glob(f"{path}/*.sav")
    files.sort(key=os.path.getmtime)
    return files[-1]
