import pyglet
from PIL import Image, ImageDraw
from bezier import Point, Bezier, Edge, CurvedEdge, Direction, Contour, make_jigsaw_cut

from tqdm import tqdm
# import numpy as np


pyglet.resource.path = ['resources']
pyglet.resource.reindex()


window = pyglet.window.Window(
    width=1024,
    height=768,
    resizable=True
)
batch = pyglet.graphics.Batch()
group = pyglet.graphics.Group()


@window.event
def on_draw():
    window.clear()
    batch.draw()


if __name__ == '__main__':
    pieces = make_jigsaw_cut(60, 40, 100, 100)

    img = Image.new("RGBA", (1000, 1000), (255, 255, 255))
    d = ImageDraw.Draw(img)
    for piece in tqdm(pieces.values()):
        d.polygon(
            list(map(Point.tuple, piece.contour.evaluate(10))),
            fill=None,
            outline=(0, 0, 0)
        )

    # kitten = Image.open("resources/kitten.png")
    # w, h = kitten.width//2, kitten.height//2
    # mask = Image.new("1", (w, h), 0)
    # img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # d = ImageDraw.Draw(mask)
    # d.ellipse([0, 0, w, h], fill=1)
    #
    # img.paste(
    #     kitten.crop((0, 0, w, h)),
    #     mask=mask
    # )

    bin = pyglet.image.atlas.TextureBin()
    pyglet_image = bin.add(
        pyglet.image.ImageData(
            img.width,
            img.height,
            'RGBA',
            img.tobytes()
        )
    )

    kitten = pyglet.sprite.Sprite(
        # pyglet.resource.image('kitten.png'),
        pyglet_image,
        batch=batch,
        group=group
    )



    pyglet.app.run()

    # img = Image.new("RGB", (500, 500), (255, 255, 255))
    #
    # d = ImageDraw.Draw(img)
    # d.polygon(
    #     [(100, 100), (150, 100), (140, 150), (130, 120), (100, 150)],
    #     fill=(0, 0, 0),
    #     outline=(0, 0, 0)
    # )
    #
    # img.show()
