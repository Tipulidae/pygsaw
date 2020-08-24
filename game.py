import pyglet

from controller import Controller


if __name__ == '__main__':
    controller = Controller(
        image_path='hongkong.jpg',
        num_pieces=100,
        big_piece_threshold=50,
        width=1500,
        height=1100,
        resizable=True,
        vsync=False
    )
    pyglet.app.run(interval=1/120)
