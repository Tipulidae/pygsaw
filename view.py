import time

import pyglet
import pyglet.gl as gl
import glooey
import vecrec

import earcut
from bezier import Point

pyglet.resource.path = ['resources']
pyglet.resource.reindex()

GROUP_COUNT = 2
PIECE_THRESHOLD = 50


class SpriteGroup(pyglet.graphics.Group):
    """Shared sprite rendering group.

    The group is automatically coalesced with other sprite groups sharing the
    same parent group, texture and blend parameters.
    """

    def __init__(self, texture, blend_src, blend_dest, parent=None):
        """Create a sprite group. Adapted from pyglet.sprite

        :Parameters:
            `texture` : `~pyglet.image.Texture`
                The (top-level) texture containing the sprite image.
            `blend_src` : int
                OpenGL blend source mode; for example,
                ``GL_SRC_ALPHA``.
            `blend_dest` : int
                OpenGL blend destination mode; for example,
                ``GL_ONE_MINUS_SRC_ALPHA``.
            `parent` : `~pyglet.graphics.Group`
                Optional parent group.
        """
        super(SpriteGroup, self).__init__(parent)
        self.texture = texture
        self.blend_src = blend_src
        self.blend_dest = blend_dest

    def set_state(self):
        gl.glEnable(self.texture.target)
        gl.glBindTexture(self.texture.target, self.texture.id)

        gl.glPushAttrib(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(self.blend_src, self.blend_dest)

        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS)

        gl.glEnable(gl.GL_ALPHA_TEST)
        gl.glAlphaFunc(gl.GL_GREATER, 0.01)

    def unset_state(self):
        gl.glPopAttrib()
        gl.glDisable(self.texture.target)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.texture)

    def __eq__(self, other):
        return (other.__class__ is self.__class__ and
                self.parent is other.parent and
                self.texture.target == other.texture.target and
                self.texture.id == other.texture.id and
                self.blend_src == other.blend_src and
                self.blend_dest == other.blend_dest)

    def __hash__(self):
        return hash((id(self.parent),
                     self.texture.id, self.texture.target,
                     self.blend_src, self.blend_dest))


class TranslationGroup(pyglet.graphics.Group):
    def __init__(self, x, y, z=10000, *args, **kwargs):
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
class Jigsaw(pyglet.window.Window):
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
    'on_selection_box'
)
class View(pyglet.window.EventDispatcher):
    def __init__(self, texture, big_piece_threshold, **window_settings):
        self.window = Jigsaw(**window_settings)
        self.window.push_handlers(self)
        self.projection = self.window.my_projection
        self.texture = texture
        self.group = pyglet.graphics.Group()
        self.selection_box = SelectionBox()
        self.pieces = dict()
        self.hand = Hand(default_group=self.group)
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
        self.hand.translation_group.z += 1

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
        if self.selection_box.is_active:
            x, y = self.projection.view_to_clip_coord(x_, y_)
            self.selection_box.drag_to(x, y)
            self.dispatch_event(
                'on_selection_box',
                self.selection_box.rect
            )
            self.selection_box.is_active = False
        else:
            self.hand.mouse_up()

    def on_mouse_drag(self, x_, y_, dx_, dy_, buttons, modifiers):
        if self.selection_box.is_active:
            x, y = self.projection.view_to_clip_coord(x_, y_)
            self.selection_box.drag_to(x, y)
        elif not self.hand.is_empty:
            dx = dx_ / self.projection.zoom_level
            dy = dy_ / self.projection.zoom_level
            self.hand.move(dx, dy)

    def start_selection_box(self, x, y):
        # Let's not worry about shift/control to make a bigger selection now.
        self.selection_box.activate(x, y)
        self.hand.drop_everything()

    def mouse_down_on_piece(self, pid):
        self.hand.select(self.pieces[pid])

    def select_pieces(self, pids):
        self.hand.select_pieces({pid: self.pieces[pid] for pid in pids})

    def move_piece(self, pid, x, y, z):
        self.hand.move_piece(self.pieces[pid], x, y, z)

    def merge_pieces(self, pid1, pid2):
        self.pieces[pid1].merge(self.pieces[pid2])
        self.pieces.pop(pid2)

    def remember_new_z_levels(self, msg):
        self.hand.translation_group.z += len(msg)
        for z, pid in msg:
            piece = self.pieces[pid]
            if piece.is_small:
                piece.intended_z = z
            else:
                piece.update_translation_groups(0, 0, z)



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
        self.size = 1
        self._x, self._y, self._z = 0, 0, 0
        self.intended_z = 0
        self.setup(polygon, width, height)
        self.set_position(*position)

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
        if self.is_small:
            self._update_vertices(x, y, z)
        else:
            self._update_translation_groups(x, y, z)

    def _update_vertices(self, x, y, z):
        for vertices, vertex_list in zip(
                self.original_vertices, self.vertex_list):
            new_vertex_list = []
            for i, v in enumerate(vertices):
                k = i % 3
                if k == 0:
                    new_vertex_list.append(v + x)
                elif k == 1:
                    new_vertex_list.append(v + y)
                elif k == 2:
                    new_vertex_list.append(v + z)

            vertex_list.vertices[:] = tuple(new_vertex_list)

    def _update_translation_groups(self, x, y, z):
        for translation_group in self.translation_groups:
            translation_group.x = x
            translation_group.y = y
            translation_group.z = z

    def move(self, dx, dy, z):
        self.set_position(self._x + dx, self._y + dy, z)

    def update_translation_groups(self, dx, dy, dz=0):
        for group in self.translation_groups:
            group.x += dx
            group.y += dy
            group.z += dz

    def fix_z_level(self):
        if self.is_big:
            for group in self.translation_groups:
                group.z = self.intended_z

    def merge(self, other):
        if self.is_big and other.is_big:
            self.translation_groups += other.translation_groups
        elif self.is_big and other.is_small:
            other.set_position(0, 0, 0)
            tg = max(self.translation_groups, key=(lambda g: g.size))
            tg.size += other.size
            other.group = tg
        elif self.is_small and other.is_big:
            self.set_position(0, 0, 0)
            self.translation_groups = other.translation_groups
            tg = max(self.translation_groups, key=(lambda g: g.size))
            tg.size += self.size
            self.group = tg
        elif self.is_small and other.is_small:
            if self.size + other.size >= PIECE_THRESHOLD:
                x, y, z = self.x, self.y, self.z
                self.set_position(0, 0, 0)
                other.set_position(0, 0, 0)
                translation_group = TranslationGroup(
                    x=x + self.group.parent.x,
                    y=y + self.group.parent.y,
                    z=z + self.group.parent.z)
                translation_group.size = self.size
                self.translation_groups = [translation_group]
                self.group = other.group = translation_group
            else:
                other.set_position(self.x, self.y, self.z)
                other.group = self.group

        self.original_vertices += other.original_vertices
        self.vertex_list += other.vertex_list
        self.size += other.size

    @property
    def is_big(self):
        return self.size >= PIECE_THRESHOLD

    @property
    def is_small(self):
        return not self.is_big

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


class SelectionBox:
    def __init__(self):
        self.is_active = False
        self.origin = (0, 0)
        self.dest = (0, 0)

    def activate(self, x, y):
        self.origin = (x, y)
        self.is_active = True

    def drag_to(self, x, y):
        self.dest = (x, y)

    @property
    def rect(self):
        return vecrec.Rect(
            left=min(self.origin[0], self.dest[0]),
            bottom=min(self.origin[1], self.dest[1]),
            width=abs(self.origin[0] - self.dest[0]),
            height=abs(self.origin[1] - self.dest[1])
        )


@glooey.register_event_type(
    'on_view_pieces_moved',
    'on_view_select_pieces'
)
class Hand(pyglet.window.EventDispatcher):
    def __init__(self, default_group):
        self.default_group = default_group
        self.translation_group = TranslationGroup(0, 0)
        self.pieces = dict()
        self.step = (0, 0)

    def select(self, piece):
        if piece.pid not in self.pieces:
            self.drop_everything()
            self.dispatch_event(
                'on_view_select_pieces',
                [piece.pid]
            )
            self.pieces = {piece.pid: piece}
            if piece.is_small:
                piece.group = self.translation_group
        print(f"{piece.pid}: {piece.z}, {piece.intended_z}")

    def select_pieces(self, new_pieces):
        t0 = time.time()
        assert len(self.pieces) == 0
        self.pieces = new_pieces
        self.dispatch_event(
            'on_view_select_pieces',
            list(self.pieces)
        )
        for piece in self.pieces.values():
            if piece.is_small:
                piece.group = self.translation_group
        t1 = time.time()
        print(f"{len(new_pieces)}: {t1 - t0}")

    def mouse_up(self):
        self.dispatch_event(
            'on_view_pieces_moved',
            list(self.pieces),
            self.translation_group.x - self.step[0],
            self.translation_group.y - self.step[1]
        )
        self.step = (
            self.translation_group.x,
            self.translation_group.y
        )

    def drop_everything(self):
        for pid, piece in self.pieces.items():
            if piece.is_small:
                piece.move(
                    self.translation_group.x,
                    self.translation_group.y,
                    piece.intended_z
                )
                piece.group = self.default_group
                piece.intended_z = 0
            else:
                piece.fix_z_level()

        self.pieces = dict()
        self.translation_group.x = 0
        self.translation_group.y = 0
        self.step = 0, 0

    def move(self, dx, dy):
        self.translation_group.x += dx
        self.translation_group.y += dy
        for piece in self.pieces.values():
            piece.update_translation_groups(dx, dy)

    def move_piece(self, piece, x, y, z):
        if piece.pid in self.pieces:
            if piece.is_small:
                p1 = Point(x, y)
                p2 = Point(piece.x, piece.y)
                p3 = Point(self.translation_group.x, self.translation_group.y)
                if Point.dist(diff := (p1 - p2 - p3), Point(0, 0)) > 1e-6:
                    piece.move(diff.x, diff.y, z)
            else:
                piece.set_position(x, y, z)

        else:
            piece.set_position(x, y, z)

    @property
    def is_empty(self):
        return len(self.pieces) == 0
