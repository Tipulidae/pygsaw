import pyglet

from controller import Controller


if __name__ == '__main__':
    controller = Controller(
        image_path="kitten.png",
        num_pieces=16,
        big_piece_threshold=100,
        width=1500,
        height=1100,
        resizable=True,
        vsync=False
    )
    pyglet.app.run()
