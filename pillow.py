import pyglet
from PIL import Image, ImageDraw
from bezier import Point, Bezier, Edge

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
    # edge = Edge(
    #     Bezier(Point(0, 0), Point(50, 20), Point(100, 25), Point(80, 0)),
    #     Bezier(Point(80, 0), Point(60, -25), Point(70, -40), Point(100, -40)),
    #     Bezier(Point(100, -40), Point(130, -40), Point(140, -25), Point(120, 0)),
    #     Bezier(Point(120, 0), Point(120, 25), Point(150, 20), Point(200, 0))
    # )
    #
    # points = [Point(0, 100) + p for p in edge.evaluate(100)]
    # points = [Point(p.x * 4, p.y * 4) for p in points]
    # # points = [Point(0, 100) + p for p in edge.evaluate(30)]
    # # print(points)
    #
    # # print(curve.evaluate(10))
    #
    # img = Image.new("RGB", (800, 800), (255, 255, 255))
    # d = ImageDraw.Draw(img)
    # d.polygon(
    #     list(map(Point.tuple, points)),
    #     fill=None,
    #     outline=(0, 0, 0)
    # )

    kitten = Image.open("resources/kitten.png")
    w, h = kitten.width//2, kitten.height//2
    mask = Image.new("1", (w, h), 0)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(mask)
    d.ellipse([0, 0, w, h], fill=1)

    img.paste(
        kitten.crop((0, 0, w, h)),
        mask=mask
    )

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
