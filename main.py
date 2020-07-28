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

    def pan(self, dx, dy):
        self.clip_port.displace(
            int(dx * self.clip_port.width),
            int(dy * self.clip_port.height)
        )
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
        self.old_bbox = self.bbox

    @property
    def rect(self):
        return vecrec.Rect(
            left=self.x,
            bottom=self.y,
            width=self.width,
            height=self.height
        )

    @property
    def bbox(self):
        return (
            self.rect.left,
            self.rect.bottom,
            self.rect.right,
            self.rect.top
        )

    def move(self, dx, dy):
        self.update(x=self.x + dx, y=self.y + dy)

    def is_pixel_inside_hitbox(self, x, y):
        if self.mask:
            return self.mask.getpixel(
                (x - self.x, self.height - y + self.y)) == 1
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
        self.pan_speed = 0.8
        self.max_selection = max_selection
        self.my_projection = OrthographicProjection(
            *self.get_viewport_size(),
            z_span=max_kittens,
            zoom=1.0
        )
        self.max_kittens = max_kittens
        self.quadtree = Index(bbox=(-100000, -100000, 100000, 100000))
        self.add_kittens()
        self.old_width, self.old_height = self.get_viewport_size()
        self.keys = pyglet.window.key.KeyStateHandler()
        self.push_handlers(self.keys)
        self.is_panning = False
        print(f"{pyglet.image.get_max_texture_size()}")

    def add_kittens(self):
        N = int(sqrt(self.max_kittens))
        # scale = 1
        kitten_image = Image.open("pygsaw/resources/kitten.png").convert("RGBA")
        # kitten_image = kitten_image.resize(
        #     (scale * kitten_image.width, scale * kitten_image.height)
        # )

        w = kitten_image.width // N
        h = kitten_image.height // N
        print(f"{w}, {h}")

        pieces = make_jigsaw_cut(w, h, N, N)

        def piece_img(pid):
            img = Image.new("RGBA", (2*w, 2*h), (0, 0, 0, 0))
            mask = Image.new("1", (2*w, 2*h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.polygon(
                list(map(Point.tuple, pieces[pid].contour.evaluate(10))),
                fill=1,
                outline=1
            )

            l = (w * (pid % N) - w//2)
            t = (h * (pid // N) - h//2)
            img.paste(
                kitten_image.crop((l, t, l+2*w, t+2*h)),
                mask=mask
            )

            return img, mask

        imgs = [
            piece_img(i) for i in tqdm(range(N*N), desc="Cutting pieces")
        ]

        bin = pyglet.image.atlas.TextureBin(
            texture_width=2*kitten_image.width,
            texture_height=2*kitten_image.height)
        pyglet_imgs = [
            (bin.add(
                pyglet.image.ImageData(
                    img.width,
                    img.height,
                    'RGBA',
                    img.tobytes(),
                    -img.width*4
                )
            ), mask) for img, mask in imgs
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
            for (i, (img, mask)) in enumerate(pyglet_imgs)
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

    def update(self, dt):
        if self.keys[pyglet.window.key.W]:
            self.my_projection.pan(0, self.pan_speed * dt)
        elif self.keys[pyglet.window.key.S]:
            self.my_projection.pan(0, -self.pan_speed * dt)

        if self.keys[pyglet.window.key.A]:
            self.my_projection.pan(-self.pan_speed * dt, 0)
        elif self.keys[pyglet.window.key.D]:
            self.my_projection.pan(self.pan_speed * dt, 0)


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

    def on_key_press(self, symbol, modifiers):
        if not self.is_panning and symbol in [
                pyglet.window.key.W,
                pyglet.window.key.A,
                pyglet.window.key.S,
                pyglet.window.key.D]:
            pyglet.clock.schedule_interval(self.update, 1/120)
            self.is_panning = True

    def on_key_release(self, symbol, modifiers):
        if self.is_panning and not (
                self.keys[pyglet.window.key.W] or
                self.keys[pyglet.window.key.A] or
                self.keys[pyglet.window.key.S] or
                self.keys[pyglet.window.key.D]):
            pyglet.clock.unschedule(self.update)
            self.is_panning = False


    def on_mouse_press(self, x_, y_, button, modifiers):
        x, y = self.my_projection.view_to_clip_coord(x_, y_)
        # for kitten in self.held_kittens:
        #     if (x, y) in kitten.rect:
        #         self.selection_box = SelectionBox(x=x, y=y)
        #         return True

        if button & pyglet.window.mouse.LEFT:
            kitten = self._top_kitten_at_location(x, y)
            if kitten:
                self.held_kittens = [kitten]
                for k in self.kittens:
                    if k.z > kitten.z:
                        k.z -= 1

                kitten.z = self.max_kittens - 1
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
        # elif self.selection_box:
        #     self.held_kittens = list(self._kittens_in_selection_box())

    def on_mouse_drag(self, x_, y_, dx_, dy_, buttons, modifiers):
        x, y = self.my_projection.view_to_clip_coord(x_, y_)
        dx = dx_ / self.my_projection.zoom_level
        dy = dy_ / self.my_projection.zoom_level
        if len(self.held_kittens) < self.max_selection:
            for kitten in self.held_kittens:
                kitten.move(dx, dy)

        # if self.selection_box:
        #     self.selection_box.move_to(x, y)

    def _kittens_at_location(self, x, y):
        for kitten in self.quadtree.intersect(bbox=(x, y, x, y)):
            if kitten.is_pixel_inside_hitbox(x, y):
                yield kitten

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
        max_kittens=1000
    )
    pyglet.app.run()
