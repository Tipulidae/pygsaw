import pyglet
import pyglet.gl as gl
import vecrec
import random
from PIL import Image, ImageDraw

from math import sqrt

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
            width=self.clip_port.width * (new_width / old_width),
            height=self.clip_port.height * (new_height / old_height)
        )
        self.update()

    def zoom(self, level_diff, x, y):
        self.zoom_level *= level_diff
        scale = (level_diff - 1) / level_diff
        x_ = self.clip_port.width * x / self.view_port.width
        y_ = self.clip_port.height * y / self.view_port.height
        self.clip_port = vecrec.Rect(
            left=self.clip_port.left + x_ * scale,
            bottom=self.clip_port.bottom + y_ * scale,
            width=self.clip_port.width / level_diff,
            height=self.clip_port.height / level_diff
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
    def __init__(self, *args, scale=1.0, **kwargs):
        super().__init__(*args, usage='stream', **kwargs)
        self.scale = scale
        self.selected = False

    @property
    def rect(self):
        return vecrec.Rect(
            left=self.x,
            bottom=self.y,
            width=self.width,
            height=self.height
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
        self.add_kittens()
        # self.view_area = vecrec.Rect(0, 0, *self.get_viewport_size())
        # self._zoom_level = 1.0
        self.old_width, self.old_height = self.get_viewport_size()
        print(f"{self.get_viewport_size()}")

    def add_kittens(self):
        scale = 1/sqrt(self.max_kittens)
        N = int(sqrt(self.max_kittens))

        img = pyglet.resource.image('kitten.png')
        step_x = img.width*scale + 2
        step_y = img.height*scale + 2
        w = img.width // N
        h = img.height // N

        kitten_image = Image.open("pygsaw/resources/hongkong.jpg").convert("RGBA")
        w = kitten_image.width // N
        h = kitten_image.height // N
        mask = Image.new("1", (w, h), 0)
        # img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(mask)
        d.ellipse([0, 0, w, h], fill=1)

        def foo(i):
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            l = w * (i % N)
            t = h * (i // N)
            img.paste(
                kitten_image.crop((l, t, l+w, t+h)),
                mask=mask
            )
            return img

        imgs = [
            foo(i) for i in range(self.max_kittens)
        ]

        bin = pyglet.image.atlas.TextureBin()
        pyglet_imgs = [
            bin.add(
                pyglet.image.ImageData(
                    img.width,
                    img.height,
                    'RGBA',
                    img.tobytes()
                )
            ) for img in imgs
        ]

        self.kittens = [
            Kitten(
                # img.get_region(w*(i%N), h*(i//N), w, h),
                img,
                # x=(i % N) * step_x,
                # y=(i // N) * step_y,
                z=i,
                x=random.randint(0, kitten_image.width*1.4),
                y=random.randint(0, kitten_image.height*1.4),
                # scale=scale,
                scale=1.0,
                batch=self.batch,
                group=self.group
            )
            # for i in range(self.max_kittens)
            for (i, img) in enumerate(pyglet_imgs)
        ]

    # @property
    # def zoom_level(self):
    #     return self._zoom_level
    #
    # @zoom_level.setter
    # def zoom_level(self, value):
    #     self._zoom_level = value

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
        print(f"{x}, {y}, {scroll_x}, {scroll_y}")
        if scroll_y > 0:
            self.my_projection.zoom(1.25, x, y)
        elif scroll_y < 0:
            self.my_projection.zoom(0.8, x, y)
            # self.zoom_level = 1.2
            # print(f"zoom level = {self.zoom_level}")
            # self.view_area = vecrec.Rect(
            #     left=x / (self.zoom_level * (self.zoom_level - 1)),
            #     bottom=y / (self.zoom_level * (self.zoom_level - 1)),
            #     width=self.view_area.width / self.zoom_level,
            #     height=self.view_area.height / self.zoom_level
            # )
            # self.my_projection.set(self.width, self.height, self.view_area)

    def on_mouse_press(self, x_, y_, button, modifiers):
        x, y = self.my_projection.view_to_clip_coord(x_, y_)
        for kitten in self.held_kittens:
            if (x, y) in kitten.rect:
                self.selection_box = SelectionBox(x=x, y=y)
                return True

        if button & pyglet.window.mouse.LEFT:
            kitten = self._top_kitten_at_location(x, y)
            if kitten:

        # for kitten in self._kittens_at_location(x, y):
        #     if button & pyglet.window.mouse.LEFT:
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
            if len(self.held_kittens) >= self.max_selection:
                for kitten in self.held_kittens:
                    kitten.move(x - self.selection_box.origin_x,
                                y - self.selection_box.origin_y)

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
        for kitten in self.kittens:
            if (x, y) in kitten.rect:
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


if __name__ == '__main__':
    game = Main(
        width=1024,
        height=768,
        resizable=True,
        vsync=False,
        max_kittens=10000
    )
    pyglet.app.run()
