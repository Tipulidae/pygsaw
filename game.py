import pyglet

from controller import Controller


if __name__ == '__main__':
    controller = Controller(
        puzzle_settings={
            'image_path': 'kitten.png',
            'num_pieces': 16,
            'big_piece_threshold': 50,
        },
        window_settings={
            'width': 1500,
            'height': 1100,
            'resizable': True,
            'vsync': False
        }
    )
    pyglet.app.run(interval=1/120)
