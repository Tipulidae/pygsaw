import pyglet

from controller import Controller
from settings import Settings


if __name__ == '__main__':
    controller = Controller(
        # puzzle_settings={
        #     'image_path': 'resources/kitten.png',
        #     'num_intended_pieces': 16,
        #     'piece_rotation': True,
        #     'snap_distance': 0.5,
        #     'big_piece_threshold': 3,
        #
        # },
        puzzle_settings=Settings(
            image_path='resources/kitten.png'
        ),
        window_settings={
            'width': 1500,
            'height': 1100,
            'resizable': True,
            'vsync': False
        }
    )
    pyglet.app.run(interval=1/120)
