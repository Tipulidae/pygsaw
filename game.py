import math
import time
import random

import pyglet
import pyglet.gl as gl
import vecrec
from tqdm import tqdm
from pyqtree import Index

from bezier import Point, make_jigsaw_cut, point_in_polygon
from sprite import SpriteGroup
import earcut

pyglet.resource.path = ['resources']
pyglet.resource.reindex()


class TranslationGroup(pyglet.graphics.Group):
    def __init__(self, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = x
        self.y = y

    def set_state(self):
        pyglet.gl.glPushMatrix()
        pyglet.gl.glTranslatef(self.x, self.y, 0)

    def unset_state(self):
        pyglet.gl.glPopMatrix()


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


class Piece:
    def __init__(self, pid, model, texture, batch, group, x=0, y=0, z=0):
        self.pid = pid
        self.piece_model = model
        self.texture = texture
        self.batch = batch
        self._group = SpriteGroup(
            self.texture,
            pyglet.gl.GL_SRC_ALPHA,
            pyglet.gl.GL_ONE_MINUS_SRC_ALPHA,
            group
        )
        self.vertex_list = None
        self.original_vertices = None
        self.polygon = None
        self._x, self._y, self._z = 0, 0, 0
        self._bbox = None
        self.setup()
        self.set_position(x, y, z)
        self.old_bbox = self.bbox

    @property
    def rect(self):
        return vecrec.Rect(
            left=self._x + self._bbox.left,
            bottom=self._y + self._bbox.bottom,
            width=self._bbox.width,
            height=self._bbox.height
        )

    @property
    def bbox(self):
        return (
            self.rect.left,
            self.rect.bottom,
            self.rect.right,
            self.rect.top
        )

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, group):
        self._group = SpriteGroup(
            self.texture,
            pyglet.gl.GL_SRC_ALPHA,
            pyglet.gl.GL_ONE_MINUS_SRC_ALPHA,
            group
        )

        self.batch.migrate(
            self.vertex_list,
            pyglet.gl.GL_TRIANGLES,
            self._group,
            self.batch)

    def setup(self):
        self.polygon = self.piece_model.contour.evaluate(10)

        sx = self.texture.tex_coords[6] / self.texture.width
        sy = self.texture.tex_coords[7] / self.texture.height
        offset_x = self.piece_model.origin.x - self.piece_model.width // 2
        offset_y = self.piece_model.origin.y - self.piece_model.height // 2

        self.original_vertices = []
        earcut_input = []
        tex_coords = []
        for p in self.polygon:
            self.original_vertices.append(p.x)
            self.original_vertices.append(p.y)
            self.original_vertices.append(self.z)

            earcut_input.append(p.x)
            earcut_input.append(p.y)

            tex_coords.append(sx * (p.x + offset_x))
            tex_coords.append(sy * (p.y + offset_y))
            tex_coords.append(0)

        indices = earcut.earcut(earcut_input)

        self.vertex_list = self.batch.add_indexed(
            len(self.original_vertices) // 3,
            pyglet.gl.GL_TRIANGLES,
            self.group,
            indices,
            ('v3f', tuple(self.original_vertices)),
            ('t3f', tuple(tex_coords))
        )

        self.polygon.append(self.polygon[0])
        self._make_bbox()

    def _make_bbox(self):
        left = bottom = math.inf
        right = top = -math.inf
        for p in self.polygon:
            if p.x < left:
                left = p.x
            elif p.x > right:
                right = p.x
            if p.y < bottom:
                bottom = p.y
            elif p.y > top:
                top = p.y

        self._bbox = vecrec.Rect(
            left=left,
            bottom=bottom,
            width=right - left,
            height=top - bottom
        )

    def set_position(self, x, y, z):
        self._x, self._y, self._z = x, y, z
        new_vertex_list = []
        for i, v in enumerate(self.original_vertices):
            k = i % 3
            if k == 0:
                new_vertex_list.append(v+x)
            elif k == 1:
                new_vertex_list.append(v+y)
            elif k == 2:
                new_vertex_list.append(v+z)

        self.vertex_list.vertices[:] = tuple(new_vertex_list)

    def move(self, dx, dy, dz=0):
        self.set_position(self._x + dx, self._y + dy, self._z + dz)

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, z):
        self.set_position(self._x, self._y, z)

    def hitbox(self, x, y):
        return point_in_polygon(Point(x - self._x, y - self._y), self.polygon)


class Game(pyglet.window.Window):
    def __init__(
            self,
            max_pieces=100,
            pic='kitten.png',
            **kwargs):
        super().__init__(**kwargs)
        self.batch = pyglet.graphics.Batch()
        self.group = pyglet.graphics.Group()
        self.selection_group = TranslationGroup(0, 0)
        self.fps = pyglet.window.FPSDisplay(window=self)
        self.pieces = []
        self.held_pieces = []
        self.selection_box = None
        self.pan_speed = 0.8
        self.my_projection = OrthographicProjection(
            *self.get_viewport_size(),
            z_span=max_pieces,
            zoom=1.0
        )
        self.max_pieces = max_pieces
        self.pic = pic
        self.quadtree = Index(bbox=(-100000, -100000, 100000, 100000))
        self.add_pieces()
        self.old_width, self.old_height = self.get_viewport_size()
        self.keys = pyglet.window.key.KeyStateHandler()
        self.push_handlers(self.keys)
        self.is_panning = False

    def add_pieces(self):
        N = int(math.sqrt(self.max_pieces))
        kitten_image = pyglet.resource.image(self.pic)
        texture = kitten_image.get_texture()
        w = kitten_image.width // N
        h = kitten_image.height // N
        print(f"{w}, {h}")

        pieces = make_jigsaw_cut(w, h, N, N)

        self.pieces = [
            Piece(
                i,
                piece,
                texture,
                self.batch,
                self.group,
                # x=pieces[i].origin.x,
                # y=pieces[i].origin.y,
                z=i,
                x=random.randint(0, int(kitten_image.width * 1.4)),
                y=random.randint(0, int(kitten_image.height * 1.4))
            )
            for i, piece in tqdm(pieces.items(), desc="Creating pieces")
        ]

        for kitten in tqdm(self.pieces, desc="Building quad-tree"):
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
        for piece in self.held_pieces:
            if (x, y) in piece.rect:
                self.selection_box = SelectionBox(x=x, y=y)
                return True

        if button & pyglet.window.mouse.LEFT:
            piece = self._top_piece_at_location(x, y)
            if piece:
                self.held_pieces = [piece]
                piece.group = self.selection_group
                for k in self.pieces:
                    if k.z > piece.z:
                        k.z -= 1

                piece.z = self.max_pieces - 1
                return True

        self.selection_box = SelectionBox(x=x, y=y)

    def on_mouse_release(self, x, y, button, modifiers):
        if self.held_pieces:
            t0 = time.time()
            for piece in self.held_pieces:
                piece.group = self.group
            t1 = time.time()
            for piece in self.held_pieces:
                piece.move(self.selection_group.x, self.selection_group.y)
            t2 = time.time()
            for piece in self.held_pieces:
                self._move_piece_in_quadtree(piece)
            t3 = time.time()
            print(f"{t1-t0}, {t2-t1}, {t3-t2}")
            self.selection_group.x = 0
            self.selection_group.y = 0
            self.held_pieces = []
        elif self.selection_box:
            self.held_pieces = list(self._pieces_in_selection_box())
            for piece in self.held_pieces:
                piece.group = self.selection_group

    def on_mouse_drag(self, x_, y_, dx_, dy_, buttons, modifiers):
        x, y = self.my_projection.view_to_clip_coord(x_, y_)

        if self.held_pieces:
            dx = dx_ / self.my_projection.zoom_level
            dy = dy_ / self.my_projection.zoom_level
            self.selection_group.x += dx
            self.selection_group.y += dy

        if self.selection_box:
            self.selection_box.move_to(x, y)

    def _pieces_at_location(self, x, y):
        for piece in self.quadtree.intersect(bbox=(x, y, x, y)):
            if piece.hitbox(x, y):
                yield piece

    def _top_piece_at_location(self, x, y):
        return max(
            self._pieces_at_location(x, y),
            key=(lambda k: k.z),
            default=None
        )

    def _pieces_in_selection_box(self):
        if self.selection_box:
            for piece in self.pieces:
                if self.selection_box.touching(piece.rect):
                    yield piece
        else:
            return

    def _move_piece_in_quadtree(self, piece):
        self.quadtree.remove(piece, piece.old_bbox)
        piece.old_bbox = piece.bbox
        self.quadtree.insert(piece, piece.bbox)


if __name__ == '__main__':
    game = Game(
        width=1500,
        height=1100,
        resizable=True,
        vsync=False,
        pic='hongkong.jpg',
        max_pieces=2000
    )
    pyglet.app.run()
