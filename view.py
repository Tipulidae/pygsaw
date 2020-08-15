import time

import pyglet
import pyglet.gl as gl
import glooey
import vecrec

import earcut
from sprite import SpriteGroup

pyglet.resource.path = ['resources']
pyglet.resource.reindex()

GROUP_COUNT = 2

global PIECE_THRESHOLD


class TranslationGroup(pyglet.graphics.Group):
    def __init__(self, x, y, z=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = x
        self.y = y
        self.z = z
        self.size = 0

    def set_state(self):
        pyglet.gl.glPushMatrix()
        pyglet.gl.glTranslatef(self.x, self.y, self.z)

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


@glooey.register_event_type('on_cheat')
class MyWindow(pyglet.window.Window):
    def __init__(self, pan_speed=0.8, **kwargs):
        super().__init__(**kwargs)
        self.batch = pyglet.graphics.Batch()
        self.fps = pyglet.window.FPSDisplay(window=self)
        self.pan_speed = pan_speed
        self.my_projection = OrthographicProjection(
            *self.get_viewport_size(),
            z_span=100000,
            zoom=1.0
        )
        self.old_width, self.old_height = self.get_viewport_size()
        self.keys = pyglet.window.key.KeyStateHandler()
        self.push_handlers(self.keys)
        self.is_panning = False

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
        if scroll_y > 0:
            self.my_projection.zoom(1.25, x, y)
        elif scroll_y < 0:
            self.my_projection.zoom(0.8, x, y)

    def update(self, dt):
        if self.keys[pyglet.window.key.W]:
            self.my_projection.pan(0, self.pan_speed * dt)
        elif self.keys[pyglet.window.key.S]:
            self.my_projection.pan(0, -self.pan_speed * dt)

        if self.keys[pyglet.window.key.A]:
            self.my_projection.pan(-self.pan_speed * dt, 0)
        elif self.keys[pyglet.window.key.D]:
            self.my_projection.pan(self.pan_speed * dt, 0)

    def on_key_press(self, symbol, modifiers):
        if not self.is_panning and symbol in [
                pyglet.window.key.W,
                pyglet.window.key.A,
                pyglet.window.key.S,
                pyglet.window.key.D]:
            pyglet.clock.schedule_interval(self.update, 1/120)
            self.is_panning = True
        if symbol == pyglet.window.key.C:
            self.dispatch_event('on_cheat', 1)
        if symbol == pyglet.window.key.X:
            self.dispatch_event('on_cheat', 100)

    def on_key_release(self, symbol, modifiers):
        if self.is_panning and not (
                self.keys[pyglet.window.key.W] or
                self.keys[pyglet.window.key.A] or
                self.keys[pyglet.window.key.S] or
                self.keys[pyglet.window.key.D]):
            pyglet.clock.unschedule(self.update)
            self.is_panning = False


@glooey.register_event_type(
    'on_mouse_down',
    'on_mouse_up',
    'on_view_piece_dropped'
)
class View(pyglet.window.EventDispatcher):
    def __init__(self, texture, big_piece_threshold, **window_settings):
        self.window = MyWindow(**window_settings)
        self.window.push_handlers(self)
        self.projection = self.window.my_projection
        self.texture = texture
        self.group = pyglet.graphics.Group()
        self.selection_group = TranslationGroup(0, 0)
        self.pieces = dict()
        self.current_max_z_level = len(self.pieces)
        self.held_pieces = []
        global PIECE_THRESHOLD
        PIECE_THRESHOLD = big_piece_threshold

    def create_piece(self, pid, polygon, position, width, height):
        self.pieces[pid] = Piece(
            pid,
            polygon,
            position,
            width,
            height,
            self.texture,
            self.window.batch,
            self.group
        )

    def on_mouse_press(self, x_, y_, button, modifiers):
        """
        The x_, y_ tuple is the view coordinates of the mouse pointer, in
        which 0, 0 is the bottom left corner of the window and
        window.width, window.height is the top right corner. When the view is
        zoomed and/or panned, the view coordinates will differ from the clip-
        coordinates, which correspond to the "actual" coordinates in the model.
        """
        x, y = self.projection.view_to_clip_coord(x_, y_)

        self.dispatch_event('on_mouse_down', x, y)

    def on_mouse_release(self, x_, y_, button, modifiers):
        t0 = time.time()
        x, y = self.projection.view_to_clip_coord(x_, y_)
        for piece in self.held_pieces:
            if not piece.translation_groups:
                piece.group = self.group

            self.dispatch_event(
                'on_view_piece_dropped',
                piece.pid,
                self.selection_group.x,
                self.selection_group.y
            )

        self.held_pieces = []
        self.selection_group.x = 0
        self.selection_group.y = 0

        t1 = time.time()
        print(f"Time elapsed: {t1 - t0}")

    def on_mouse_drag(self, x_, y_, dx_, dy_, buttons, modifiers):
        if self.held_pieces:
            dx = dx_ / self.projection.zoom_level
            dy = dy_ / self.projection.zoom_level
            self.selection_group.x += dx
            self.selection_group.y += dy
            for piece in self.held_pieces:
                piece.update_translation_groups(dx, dy)

        # For each held piece that needs it, update the translation matrix
        # Also update the selection group
        # Also update the selection box

    def select_piece(self, pid):
        self.held_pieces = [self.pieces[pid]]
        if not self.pieces[pid].translation_groups:
            self.pieces[pid].group = self.selection_group

    def move_piece(self, pid, x, y, z):
        self.pieces[pid].set_position(x, y, z)

    def merge_pieces(self, pid1, pid2):
        self.pieces[pid1].merge(self.pieces[pid2])
        self.pieces.pop(pid2)


class Piece:
    def __init__(self, pid, polygon, position, width, height, texture, batch, group):
        self.pid = pid
        self.texture = texture
        self.batch = batch
        self._group = SpriteGroup(
            self.texture,
            gl.GL_SRC_ALPHA,
            gl.GL_ONE_MINUS_SRC_ALPHA,
            group
        )
        self.translation_groups = []
        self.original_vertices = None
        self.vertex_list = None
        self._x, self._y, self._z = 0, 0, 0
        self.setup(polygon, width, height)
        self.set_position(*position)

        self.size = 1

    def setup(self, polygon, width, height):
        sx = self.texture.tex_coords[6] / self.texture.width
        sy = self.texture.tex_coords[7] / self.texture.height
        offset_x = width // 2
        offset_y = height // 2

        original_vertices = []
        earcut_input = []
        tex_coords = []
        for p in polygon:
            original_vertices.append(p.x)
            original_vertices.append(p.y)
            original_vertices.append(0)

            earcut_input.append(p.x)
            earcut_input.append(p.y)

            tex_coords.append(sx * (p.x - offset_x))
            tex_coords.append(sy * (p.y - offset_y))
            tex_coords.append(0)
        self.original_vertices = [original_vertices]

        indices = earcut.earcut(earcut_input)

        vertex_list = self.batch.add_indexed(
            len(original_vertices) // 3,
            pyglet.gl.GL_TRIANGLES,
            self.group,
            indices,
            ('v3f', tuple(original_vertices)),
            ('t3f', tuple(tex_coords))
        )
        self.vertex_list = [vertex_list]

    def set_position(self, x, y, z):
        self._x, self._y, self._z = x, y, z
        if not self.translation_groups:
            for vertices, vertex_list in zip(self.original_vertices,
                                             self.vertex_list):
                new_vertex_list = []
                for i, v in enumerate(vertices):
                    k = i % 3
                    if k == 0:
                        new_vertex_list.append(v+x)
                    elif k == 1:
                        new_vertex_list.append(v+y)
                    elif k == 2:
                        new_vertex_list.append(v+z)

                vertex_list.vertices[:] = tuple(new_vertex_list)
        else:
            for translation_group in self.translation_groups:
                translation_group.x = x
                translation_group.y = y
                translation_group.z = z

    def move(self, dx, dy, dz):
        self.set_position(self._x + dx, self._y + dy, self._z + dz)

    def update_translation_groups(self, dx, dy, dz=0):
        for group in self.translation_groups:
            group.x += dx
            group.y += dy
            group.z += dz

    def merge(self, other):
        def merge_vertices():
            self.original_vertices += other.original_vertices
            self.vertex_list += other.vertex_list

        if self.is_big and other.is_big:
            merge_vertices()
            self.translation_groups += other.translation_groups
        elif self.is_big and not other.is_big:
            merge_vertices()
            other.set_position(0, 0, 0)
            tg = max(self.translation_groups, key=(lambda g: g.size))
            tg.size += other.size
            other.group = tg
        elif not self.is_big and other.is_big:
            self.set_position(0, 0, 0)
            self.translation_groups = other.translation_groups
            tg = max(self.translation_groups, key=(lambda g: g.size))
            tg.size += self.size
            self.group = tg
            # OBS!! Very important to do this AFTER changing group, for
            # performance reasons! Otherwise we reset the position of all the
            # vertices of the group we are merging into, which is not only
            # needless, but also potentially very expensive.
            merge_vertices()
        elif not self.is_big and not other.is_big:
            merge_vertices()
            if self.size + other.size >= PIECE_THRESHOLD:
                x, y, z = self.x, self.y, self.z
                self.set_position(0, 0, 0)
                translation_group = TranslationGroup(x=x, y=y, z=z)
                translation_group.size = self.size
                self.translation_groups = [translation_group]
                self.group = translation_group

        self.size += other.size

    @property
    def is_big(self):
        return self.size >= PIECE_THRESHOLD

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, z):
        self.set_position(self._x, self._y, z)

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, group):
        for vertex_list in self.vertex_list:
            self._group = SpriteGroup(
                self.texture,
                gl.GL_SRC_ALPHA,
                gl.GL_ONE_MINUS_SRC_ALPHA,
                group
            )

            self.batch.migrate(
                vertex_list,
                gl.GL_TRIANGLES,
                self._group,
                self.batch
            )
