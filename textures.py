import aggdraw
from pyglet.image import ImageData
from PIL import Image, ImageShow, ImageFilter, ImageMath

from model import Model


# Adapted from http://www.pythonstuff.org
# https://www.pythonstuff.org/glsl/normalmaps_from_heightmaps_2.html
def height2bump(height_band, filter='scharr'):
    # 5x5 opt Scharr Filter from
    # http://nbn-resolving.de/urn/resolver.pl?urn=urn:nbn:de:bsz:16-opus-9622
    if filter == 'scharr':
        a1 = 21.38
        a2 = 85.24
        a3 = 0

        b1 = 5.96
        b2 = 61.81
        b3 = 120.46
    else:
        a1 = 1
        a2 = 2
        a3 = 0
        b1 = 1
        b2 = 4
        b3 = 6

    a4 = -a2
    a5 = -a1
    b4 = b2
    b5 = b1

    kernel = [
        (a1 * b1, a2 * b1, a3 * b1, a4 * b1, a5 * b1,
         a1 * b2, a2 * b2, a3 * b2, a4 * b2, a5 * b2,
         a1 * b3, a2 * b3, a3 * b3, a4 * b3, a5 * b3,
         a1 * b4, a2 * b4, a3 * b4, a4 * b4, a5 * b4,
         a1 * b5, a2 * b5, a3 * b5, a4 * b5, a5 * b5),
        (b1 * a1, b2 * a1, b3 * a1, b4 * a1, b5 * a1,
         b1 * a2, b2 * a2, b3 * a2, b4 * a2, b5 * a2,
         b1 * a3, b2 * a3, b3 * a3, b4 * a3, b5 * a3,
         b1 * a4, b2 * a4, b3 * a4, b4 * a4, b5 * a4,
         b1 * a5, b2 * a5, b3 * a5, b4 * a5, b5 * a5)
    ]

    scale = 0.0
    for i, val in enumerate(kernel[0]):
        if i % 5 < 5 // 2:
            scale += 255.0 * val
    scale /= 128.0

    r = height_band.filter(ImageFilter.Kernel(
        (5, 5), kernel[0], scale=scale, offset=128.0))
    g = height_band.filter(ImageFilter.Kernel(
        (5, 5), kernel[1], scale=scale, offset=128.0))
    b = ImageMath.eval(
        """128 + 128 * (1.0 - (float(r) * 2.0 / 255.0 - 1.0) ** 2.0 - 
           (float(g) * 2.0 / 255.0 - 1.0) ** 2)""",
        r=r, g=g).convert('L')

    return r, g, b


def make_height_map(pieces, width, height):
    texture = Image.new('L', (width, height), 255)

    # I'm using the aggdraw library to make antialiased lines, which is not
    # currently possible with PIL alone.
    context = aggdraw.Draw(texture)
    pen = aggdraw.Pen('gray', 1)
    for pid, piece in pieces.items():
        polygon = []
        for point in piece.polygon[pid]:
            polygon.append(point.x)
            polygon.append(point.y)
        polygon.append(polygon[0])
        polygon.append(polygon[1])
        context.line(polygon, pen)

    context.flush()
    return texture
    # return texture.filter(ImageFilter.GaussianBlur(radius=2))


def make_normal_map(pieces, image_width, image_height, piece_width, piece_height):
    height_map = make_height_map(
        pieces,
        image_width + piece_width,
        image_height + piece_height
    )
    r, g, b = height2bump(height_map, filter='sobel')
    normal_map = Image.merge('RGBA', [r, g, b, height_map])
    normal_map = normal_map.crop(
        box=(
            piece_width // 2,
            piece_height // 2,
            image_width + piece_width // 2,
            image_height + piece_height // 2
        )
    ).convert('RGBA')

    # return normal_map
    return ImageData(
        normal_map.width,
        normal_map.height,
        'RGBA',
        normal_map.tobytes(),
        normal_map.width * 4
    ).get_texture()


if __name__ == '__main__':
    model = Model(1000, 1000, 25)
    img = make_normal_map(model.pieces, 1000, 1000, 200, 200)
    ImageShow.show(img)
