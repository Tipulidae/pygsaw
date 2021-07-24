import pyglet

import src.settings as settings
from src.controller import Controller


if __name__ == '__main__':
    controller = Controller()
    pyglet.app.run(interval=settings.window.refresh_interval)
