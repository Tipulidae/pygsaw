from math import sqrt
import time
import random

import pyglet
import pyglet.gl as gl
import vecrec
from PIL import Image, ImageDraw
from tqdm import tqdm
from pyqtree import Index


from bezier import Point, make_jigsaw_cut
from sprite import Sprite

pyglet.resource.path = ['resources']
pyglet.resource.reindex()


class OrthographicProjection:
    def __init__(self, width, height, z_span=1, zoom=1.0):
        self.view_port = vecrec.Rect(
            left=0, bottom=0, width=width, height=height)
        self.clip_port = self.view_port
        self.z_span = z_span
        self.zoom_level = zoom
        self.update()

    def view_to_clip_coord(self, x, y):
        return (
            self.clip_port.left + x * self.clip_port.width / self.view_port.width,
            self.clip_port.bottom + y * self.clip_port.height / self.view_port.height
        )

    def change_window_size(self, old_width, old_height, new_width, new_height):
        self.view_port = vecrec.Rect(
            left=self.view_port.left,
            bottom=self.view_port.bottom,
            width=new_width,
            height=new_height
        )

        self.clip_port = vecrec.Rect(
            left=self.clip_port.left,
            bottom=self.clip_port.bottom,
            width=round(self.clip_port.width * (new_width / old_width)),
            height=round(self.clip_port.height * (new_height / old_height))
        )
        self.update()

    def zoom(self, level_diff, x, y):
        self.zoom_level *= level_diff
        scale = (level_diff - 1) / level_diff
        x_ = self.clip_port.width * x / self.view_port.width
        y_ = self.clip_port.height * y / self.view_port.height
        self.clip_port = vecrec.Rect(
            left=int(self.clip_port.left + x_ * scale),
            bottom=int(self.clip_port.bottom + y_ * scale),
            width=round(self.clip_port.width / level_diff),
            height=round(self.clip_port.height / level_diff)
        )
        # print(f"{self.clip_port}")
        self.update()

    def update(self):
        gl.glViewport(
            self.view_port.left,
            self.view_port.bottom,
            self.view_port.width,
            self.view_port.height
        )
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(
            self.clip_port.left,
            self.clip_port.right,
            self.clip_port.bottom,
            self.clip_port.top,
            -self.z_span,
            self.z_span
        )
        gl.glMatrixMode(gl.GL_MODELVIEW)


class Kitten(Sprite):
    def __init__(self, *args, mask=None, **kwargs):
        super().__init__(*args, usage='stream', **kwargs)
        self.mask = mask
        self.selected = False
        self.old_bbox = self.bbox

    @property
    def rect(self):
        return vecrec.Rect(
            left=self.x + self.width/6,
            bottom=self.y + self.height/6,
            width=self.width * 2/3,
            height=self.height * 2/3
        )

    @property
    def bbox(self):
        return (
            self.rect.left,
            self.rect.bottom,
            self.rect.right,
            self.rect.top
        )

    def select(self):
        if not self.selected:
            self.selected = True
            # self.color = (255, 0, 0)

    def unselect(self):
        if self.selected:
            self.selected = False
            # self.color = (255, 255, 255)

    def move(self, dx, dy):
        self.update(x=self.x + dx, y=self.y + dy)

    def is_pixel_inside_hitbox(self, x, y):
        if self.mask:
            return self.mask.getpixel((x - self.x, y - self.y)) == 1
        else:
            return True


class SelectionBox:
    def __init__(self, x, y):
        self.rect = vecrec.Rect(left=x, bottom=y, width=0, height=0)
        self.origin_x = x
        self.origin_y = y

    def move_to(self, x, y):
        self.rect = vecrec.Rect(
            left=min(self.origin_x, x),
            bottom=min(self.origin_y, y),
            width=abs(self.origin_x - x),
            height=abs(self.origin_y - y)
        )

    def touching(self, rect):
        return self.rect.touching(rect)


class Main(pyglet.window.Window):
    def __init__(self, max_kittens=100, max_selection=200, **kwargs):
        super().__init__(**kwargs)
        self.batch = pyglet.graphics.Batch()
        self.group = pyglet.graphics.Group()
        self.fps = pyglet.window.FPSDisplay(window=self)
        self.pieces = []
        self.kittens = []
        self.held_kittens = []
        self.selection_box = None
        self.selection_group = None
        self.max_selection = max_selection
        self.my_projection = OrthographicProjection(
            *self.get_viewport_size(),
            z_span=max_kittens,
            zoom=1.0
        )
        self.max_kittens = max_kittens
        self.quadtree = Index(bbox=(-10000, -10000, 10000, 10000))
        self.add_kittens()
        # self.view_area = vecrec.Rect(0, 0, *self.get_viewport_size())
        # self._zoom_level = 1.0
        self.old_width, self.old_height = self.get_viewport_size()

        print(f"{self.get_viewport_size()}")

    def add_kittens(self):
        N = int(sqrt(self.max_kittens))
        kitten_image = Image.open("pygsaw/resources/hongkong.jpg").convert("RGBA")
        w = kitten_image.width // N
        h = kitten_image.height // N

        pieces = make_jigsaw_cut(w, h, N, N)
        print(f"{pieces[0].contour.evaluate(10)}")


        # temp
        mask = Image.new("1", (2*w, 2*h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([w//2, h//2, w//2 + w, h//2 + h], fill=1)

        # !temp

        def piece_img(pid):
            img = Image.new("RGBA", (2*w, 2*h), (0, 0, 0, 0))
            # mask = Image.new("1", (2*w, 2*h), 0)
            # mask_draw = ImageDraw.Draw(mask)
            # mask_draw.polygon(
            #     list(map(Point.tuple, pieces[pid].contour.evaluate(10))),
            #     fill=1,
            #     outline=1
            # )

            l = w * (pid % N) - w//2
            t = h * (pid // N) - h//2
            img.paste(
                kitten_image.crop((l, t, l+2*w, t+2*h)),
                mask=mask
            )

            # img.save(f"foo{pid}.bmp")

            return img

        imgs = [
            piece_img(i) for i in tqdm(range(N*N))
        ]

        bin = pyglet.image.atlas.TextureBin()
        pyglet_imgs = [
            bin.add(
                pyglet.image.ImageData(
                    img.width,
                    img.height,
                    'RGBA',
                    img.tobytes(),
                    -img.width*4
                )
            ) for img in imgs
        ]

        self.kittens = [
            Kitten(
                img,
                mask=mask,
                # x=pieces[i].origin.x,
                # y=pieces[i].origin.y,
                z=i,
                x=random.randint(0, int(kitten_image.width*1.4)),
                y=random.randint(0, int(kitten_image.height*1.4)),
                batch=self.batch,
                group=self.group
            )
            # for i in range(self.max_kittens)
            for (i, img) in enumerate(pyglet_imgs)
        ]

        for kitten in self.kittens:
            self.quadtree.insert(
                kitten,
                kitten.bbox
            )

    def on_resize(self, width, height):
        self.my_projection.change_window_size(
            self.old_width,
            self.old_height,
            width,
            height
        )
        self.old_width = width
        self.old_height = height

    def on_draw(self):
        self.clear()
        self.batch.draw()
        self.fps.draw()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        # print(f"{x}, {y}, {scroll_x}, {scroll_y}")
        if scroll_y > 0:
            self.my_projection.zoom(1.25, x, y)
        elif scroll_y < 0:
            self.my_projection.zoom(0.8, x, y)

    def on_mouse_press(self, x_, y_, button, modifiers):
        x, y = self.my_projection.view_to_clip_coord(x_, y_)
        for kitten in self.held_kittens:
            if (x, y) in kitten.rect:
                self.selection_box = SelectionBox(x=x, y=y)
                return True

        if button & pyglet.window.mouse.LEFT:
            t1 = time.time()
            kitten = self._top_kitten_at_location(x, y)
            if kitten:

        # for kitten in self._kittens_at_location(x, y):
        #     if button & pyglet.window.mouse.LEFT:
                self.held_kittens = [kitten]
                t3 = time.time()
                for k in self.kittens:
                    if k.z > kitten.z:
                        k.z -= 1

                kitten.z = self.max_kittens - 1

                t2 = time.time()
                print(f"z-order: {t2 - t3}")
                print(f"Total: {t2 - t1}")
                return True

        self.selection_box = SelectionBox(x=x, y=y)

    def on_mouse_release(self, x_, y_, button, modifiers):
        x, y = self.my_projection.view_to_clip_coord(x_, y_)
        if self.held_kittens:
            for kitten in self.held_kittens:
                if len(self.held_kittens) >= self.max_selection:
                    kitten.move(x - self.selection_box.origin_x,
                                y - self.selection_box.origin_y)

                self._move_kitten_in_quadtree(kitten)

            self.held_kittens = []
        elif self.selection_box:
            self.held_kittens = list(self._kittens_in_selection_box())

    def on_mouse_drag(self, x_, y_, dx_, dy_, buttons, modifiers):
        x, y = self.my_projection.view_to_clip_coord(x_, y_)
        dx = dx_ / self.my_projection.zoom_level
        dy = dy_ / self.my_projection.zoom_level
        if len(self.held_kittens) < self.max_selection:
            for kitten in self.held_kittens:
                kitten.move(dx, dy)

        if self.selection_box:
            self.selection_box.move_to(x, y)

    def _kittens_at_location(self, x, y):
        for kitten in self.quadtree.intersect(bbox=(x, y, x, y)):
            if kitten.is_pixel_inside_hitbox(x, y):
                yield kitten
        # for kitten in self.kittens:
        #     if (x, y) in kitten.rect:
        #         yield kitten

    def _top_kitten_at_location(self, x, y):
        return max(
            self._kittens_at_location(x, y),
            key=(lambda k: k.z),
            default=None
        )

    def _kittens_in_selection_box(self):
        if self.selection_box:
            for kitten in self.kittens:
                if self.selection_box.touching(kitten.rect):
                    yield kitten
        else:
            return

    def _move_kitten_in_quadtree(self, kitten):
        self.quadtree.remove(kitten, kitten.old_bbox)
        kitten.old_bbox = kitten.bbox
        self.quadtree.insert(kitten, kitten.bbox)


if __name__ == '__main__':
    game = Main(
        width=1024,
        height=768,
        resizable=True,
        vsync=False,
        max_kittens=100
    )
    pyglet.app.run()
