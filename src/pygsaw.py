import pyglet

from src.controller import Controller
from src.settings import Settings


if __name__ == '__main__':
    controller = Controller(
        puzzle_settings=Settings(
            image_path='resources/images/kitten.png'
        ),
        window_settings={
            'width': 1500,
            'height': 1100,
            'resizable': True,
            'vsync': False
        }
    )
    pyglet.app.run(interval=1/120)
