import time

import pyglet
import pyglet.gl as gl
import vecrec

import earcut
from shaders import make_piece_shader, make_shape_shader

pyglet.resource.path = ['resources']
pyglet.resource.reindex()

GROUP_COUNT = 2
PIECE_THRESHOLD = 50
MAX_Z_DEPTH = 5000000


class PieceGroupFactory:
    default_groups = dict()
    big_groups = {tray: set() for tray in range(10)}

    @staticmethod
    def get_piece_group(tray):
        return PieceGroupFactory.default_groups[tray]

    @staticmethod
    def toggle_visibility(tray, is_visible):
        PieceGroupFactory.default_groups[tray].set_visibility(is_visible)
        for group in PieceGroupFactory.big_groups[tray]:
            group.set_visibility(is_visible)

    @staticmethod
    def move_to_group(group, tray):
        old_group = group.tray
        if group in PieceGroupFactory.big_groups[old_group]:
            PieceGroupFactory.big_groups[old_group].remove(group)

        group.tray = tray
        PieceGroupFactory.big_groups[tray].add(group)

    @staticmethod
    def new_big_group(tray):
        dg = PieceGroupFactory.default_groups[tray]
        group = PieceGroup(dg.texture, dg.normal_map, tray=tray)
        PieceGroupFactory.big_groups[tray].add(group)
        return group


class PieceGroup(pyglet.graphics.Group):
    def __init__(self, texture, normal_map, tray=0, x=0, y=0, z=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.texture = texture
        self.normal_map = normal_map
        self.tray = tray
        self.x = x
        self.y = y
        self.z = z
        self.size = 0
        self.program = make_piece_shader()
        self.program.use()
        self.program['diffuse_map'] = 0
        self.program['normal_map'] = 1
        self.program.stop()

    def move(self, dx, dy, dz):
        self.set_position(self.x + dx, self.y + dy, self.z + dz)

    def set_position(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.program.use()
        self.program['translate'] = (x, y, z)
        self.program.stop()

    def set_visibility(self, is_visible):
        self.program.use()
        if is_visible:
            self.program['hidden'] = 0.0
        else:
            self.program['hidden'] = 1.0
        self.program.stop()

    def set_state(self):
        self.program.use()
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(self.texture.target, self.texture.id)
        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(self.normal_map.target, self.normal_map.id)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS)

    def unset_state(self):
        gl.glDisable(gl.GL_BLEND)
        gl.glBindTexture(self.texture.target, 0)
        gl.glBindTexture(self.normal_map.target, 0)
        self.program.stop()

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def __eq__(self, other):
        return (other.__class__ is self.__class__ and
                self.program is other.program and
                self.parent is other.parent)

    def __hash__(self):
        return hash((id(self.parent), id(self.program)))


class SelectionBoxGroup(pyglet.graphics.Group):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = make_shape_shader()

    def set_state(self):
        self.program.bind()

        gl.glEnable(pyglet.gl.GL_LINE_SMOOTH)
        gl.glLineWidth(3)

        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS)

    def unset_state(self):
        gl.glLineWidth(1)
        gl.glDisable(pyglet.gl.GL_LINE_SMOOTH)
        self.program.unbind()


class OrthographicProjection(pyglet.window.EventDispatcher):
    def __init__(self, width, height, zoom=1.0):
        super().__init__()
        self.view_port = vecrec.Rect(
            left=0, bottom=0, width=width, height=height)
        self.clip_port = self.view_port
        self.zoom_level = zoom
        self._view = None
        self.program = pyglet.graphics.get_default_shader()
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
            x := int(dx * self.clip_port.width),
            y := int(dy * self.clip_port.height)
        )
        self.dispatch_event('on_pan', x, y)
        self.update()

    def update(self):
        width = max(1, self.view_port.width)
        height = max(1, self.view_port.height)

        pyglet.gl.glViewport(0, 0, width, height)

        with self.program.uniform_buffers['WindowBlock'] as window_block:
            window_block.projection[:] = pyglet.math.create_orthogonal(
                self.clip_port.left,
                self.clip_port.right,
                self.clip_port.bottom,
                self.clip_port.top,
                -MAX_Z_DEPTH,
                MAX_Z_DEPTH)
            if not self._view:
                # Set view to Identity Matrix
                self._view = pyglet.math.Mat4()
                window_block.view[:] = self._view


class Jigsaw(pyglet.window.Window):
    def __init__(self, pan_speed=0.8, **kwargs):
        super().__init__(**kwargs)
        self.batch = pyglet.graphics.Batch()
        self.fps = pyglet.window.FPSDisplay(window=self)
        self.pan_speed = pan_speed
        self.my_projection = OrthographicProjection(
            *self.get_framebuffer_size(),
            zoom=1.0
        )
        self.old_width, self.old_height = self.get_framebuffer_size()
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
        # self.fps.draw()

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

    def on_key_release(self, symbol, modifiers):
        if self.is_panning and not (
                self.keys[pyglet.window.key.W] or
                self.keys[pyglet.window.key.A] or
                self.keys[pyglet.window.key.S] or
                self.keys[pyglet.window.key.D]):
            pyglet.clock.unschedule(self.update)
            self.is_panning = False


class NumberKeys:
    def __init__(self):
        self.pressed = {key: False for key in range(
            pyglet.window.key._0, pyglet.window.key._9 + 1)}
        self.is_shift = False
        self.last_pressed = 0

    def press(self, key):
        if key in self.pressed:
            self.pressed[key] = True
            self.last_pressed = key - pyglet.window.key._0
        elif key == pyglet.window.key.LSHIFT:
            self.is_shift = True

    def release(self, key):
        if key in self.pressed:
            self.pressed[key] = False
            self.last_pressed = key - pyglet.window.key._0
        elif key == pyglet.window.key.LSHIFT:
            self.is_shift = False

    @property
    def is_active(self):
        if self.is_shift:
            return False
        for values in self.pressed.values():
            if values:
                return True
        return False


class View(pyglet.window.EventDispatcher):
    def __init__(self, texture, normal_map, big_piece_threshold, **window_settings):
        self.window = Jigsaw(**window_settings)
        self.window.push_handlers(self)
        self.projection = self.window.my_projection
        self.texture = texture
        self.normal_map = normal_map
        PieceGroupFactory.default_groups = {
            tray: PieceGroup(texture, normal_map, tray=tray)
            for tray in range(10)
        }
        self.selection_box = SelectionBox(self.window.batch)
        self.pieces = dict()
        self.hand = Hand(default_group=PieceGroup(texture, normal_map))
        self.projection.push_handlers(on_pan=self.hand.move)
        self.projection.push_handlers(on_pan=self.selection_box.drag)
        self.number_keys = NumberKeys()
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
            self.normal_map,
            self.window.batch
        )
        self.hand.group.z += 1

    def on_mouse_press(self, x_, y_, button, modifiers):
        """
        The x_, y_ tuple is the view coordinates of the mouse pointer, in
        which 0, 0 is the bottom left corner of the window and
        window.width, window.height is the top right corner. When the view is
        zoomed and/or panned, the view coordinates will differ from the clip-
        coordinates, which correspond to the "actual" coordinates in the model.
        """
        x, y = self.projection.view_to_clip_coord(x_, y_)
        is_shift = modifiers & pyglet.window.key.MOD_SHIFT
        self.dispatch_event('on_mouse_down', x, y, is_shift)
        self.hand.is_mouse_down = True

    def on_mouse_release(self, x_, y_, button, modifiers):
        if self.selection_box.is_active:
            x, y = self.projection.view_to_clip_coord(x_, y_)
            self.selection_box.drag_to(x, y)
            self.dispatch_event(
                'on_selection_box',
                self.selection_box.rect
            )
            self.selection_box.deactivate()
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

    def on_key_press(self, symbol, modifiers):
        self.number_keys.press(symbol)
        if symbol == pyglet.window.key.C:
            self.dispatch_event('on_cheat', 1)
        if symbol == pyglet.window.key.X:
            self.dispatch_event('on_cheat', 100)
        if symbol == pyglet.window.key.SPACE:
            pids = list(self.hand.pieces)
            if len(pids) > 0:
                self.dispatch_event('on_view_spread_out', pids)
        if symbol == pyglet.window.key.ESCAPE:
            self.hand.drop_everything()

        if _is_digit_key(symbol):
            tray = _digit_from_key(symbol)
            if modifiers & pyglet.window.key.MOD_CTRL:
                self.dispatch_event('on_toggle_visibility', tray)
            else:
                self._move_pieces_to_tray(list(self.hand.pieces), tray)

    def on_key_release(self, symbol, modifiers):
        self.number_keys.release(symbol)

    def _move_pieces_to_tray(self, pids, tray, change_group=False):
        for pid in pids:
            piece = self.pieces[pid]
            piece.set_default_tray(tray)
            if change_group and piece.is_small:
                piece.group = piece.default_group

        self.dispatch_event('on_move_pieces_to_tray', tray, pids)

    def start_selection_box(self, x, y):
        # Let's not worry about shift/control to make a bigger selection now.
        self.selection_box.activate(x, y)
        self.hand.drop_everything()

    def drop_everything(self):
        self.hand.drop_everything()

    def mouse_down_on_piece(self, pid):
        if self.number_keys.is_active:
            self._move_pieces_to_tray(
                pids=[pid],
                tray=self.number_keys.last_pressed,
                change_group=True
            )
        else:
            self.hand.select(self.pieces[pid])

    def select_pieces(self, pids):
        self.hand.select_pieces({pid: self.pieces[pid] for pid in pids})

    def snap_piece_to_position(self, pid, x, y, z):
        self.hand.snap_piece_to_position(self.pieces[pid], x, y, z)

    def merge_pieces(self, pid1, pid2):
        self.pieces[pid1].merge(self.pieces[pid2])
        self.pieces.pop(pid2)

    def remember_new_z_levels(self, msg):
        self.hand.group.move(0, 0, len(msg))
        for z, pid in msg:
            self.pieces[pid].remember_z_position(z)

    def drop_specific_pieces_from_hand(self, pids):
        self.hand.drop_pieces(pids)

    def set_visibility(self, tray, is_visible):
        PieceGroupFactory.toggle_visibility(tray, is_visible)


class Piece:
    def __init__(self, pid, polygon, position, width, height, texture, normal_map, batch):
        self.pid = pid
        self.texture = texture
        self.normal_map = normal_map
        self.batch = batch
        self.default_group = PieceGroupFactory.get_piece_group(0)
        self._group = self.default_group
        self.groups = []
        self.original_vertices = None
        self.vertex_list = None
        self.size = 1
        self._x, self._y, self._z = 0, 0, 0
        # TODO: remove this once spread_out logic is moved to model!
        self.width, self.height = width, height
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

        n = len(original_vertices) // 3
        vertex_list = self.batch.add_indexed(
            n,
            pyglet.gl.GL_TRIANGLES,
            self.group,
            indices,
            ('position3f/static', tuple(original_vertices)),
            ('colors4Bn/static', (255, 255, 255, 255) * n),
            ('tex_coords3f/static', tuple(tex_coords))
        )
        self.vertex_list = [vertex_list]

    def move(self, dx, dy, dz):
        self._x += dx
        self._y += dy
        self._z += dz

    def set_position(self, x, y, z):
        self._x, self._y, self._z = x, y, z
        if self.is_small:
            self._update_vertices(x, y, z)
        else:
            self._update_groups(x, y, z)

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

            vertex_list.position[:] = tuple(new_vertex_list)

    def _update_groups(self, x, y, z):
        for group in self.groups:
            group.set_position(x, y, z)

    def set_default_tray(self, tray):
        if self.is_small:
            self.default_group = PieceGroupFactory.get_piece_group(tray)
        else:
            for group in self.groups:
                PieceGroupFactory.move_to_group(group, tray)

    def remember_position(self, x, y, z):
        self._x, self._y, self._z = x, y, z
        if self.is_big:
            self.commit_position()

    def remember_z_position(self, z):
        self.remember_position(self._x, self._y, z)

    def remember_relative_position(self, dx, dy, dz):
        self._x += dx
        self._y += dy
        self._z += dz
        if self.is_big:
            self.commit_position()

    def commit_position(self):
        if self.is_small:
            self._update_vertices(self._x, self._y, self._z)
        else:
            self._update_groups(self._x, self._y, self._z)

    def merge(self, other):
        if self.is_big and other.is_big:
            tray = self.groups[0].tray
            self.groups += other.groups
            self.set_default_tray(tray)
            self.commit_position()
        elif self.is_big and other.is_small:
            other.set_position(0, 0, 0)
            g = max(self.groups, key=(lambda group: group.size))
            g.size += other.size
            other.group = g
        elif self.is_small and other.is_big:
            x, y, z = self.x, self.y, self.z
            tray = self.default_group.tray
            self.set_position(0, 0, 0)
            self.groups = other.groups
            g = max(self.groups, key=(lambda group: group.size))
            g.size += self.size
            self.group = g
            self.remember_position(x, y, z)
            self.set_default_tray(tray)
        elif self.is_small and other.is_small:
            if self.size + other.size >= PIECE_THRESHOLD:
                x, y, z = self.x, self.y, self.z
                self.set_position(0, 0, 0)
                other.set_position(0, 0, 0)
                tray = self.default_group.tray
                group = PieceGroupFactory.new_big_group(tray)
                group.size = self.size + other.size
                self.groups = [group]
                self.group = other.group = group
                self.remember_position(x, y, z)
            else:
                other.set_position(self.x, self.y, self.z)
                other.group = self.group

        self.original_vertices += other.original_vertices
        self.vertex_list += other.vertex_list
        self.size += other.size

    @property
    def is_big(self):
        return self.size >= PIECE_THRESHOLD or len(self.groups) > 0

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

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, group):
        for vertex_list in self.vertex_list:
            self._group = group

            self.batch.migrate(
                vertex_list,
                pyglet.gl.GL_TRIANGLES,
                self._group,
                self.batch
            )


class SelectionBox:
    def __init__(self, batch):
        self.is_active = False
        self.origin = (0, 0)
        self.dest = (0, 0)
        self.batch = batch
        self.group = SelectionBoxGroup()
        self.z = MAX_Z_DEPTH

        self.vertex_list = self.batch.add(
            4, pyglet.gl.GL_LINE_LOOP, self.group,
            ('position3f/dynamic', (0,) * 12),
            ('colors3B/static', (255, ) * 12)
        )

    def activate(self, x, y):
        self.origin = (x, y)
        self.is_active = True

    def deactivate(self):
        self.vertex_list.position[:] = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.is_active = False

    def drag(self, dx, dy):
        if self.is_active:
            x, y = self.dest
            self.drag_to(x + dx, y + dy)

    def drag_to(self, x, y):
        self.dest = (x, y)
        rect = self.rect
        self.vertex_list.position[:] = (
            rect.left, rect.bottom, self.z,
            rect.right, rect.bottom, self.z,
            rect.right, rect.top, self.z,
            rect.left, rect.top, self.z
        )

    @property
    def rect(self):
        return vecrec.Rect(
            left=min(self.origin[0], self.dest[0]),
            bottom=min(self.origin[1], self.dest[1]),
            width=abs(self.origin[0] - self.dest[0]),
            height=abs(self.origin[1] - self.dest[1])
        )


class Hand(pyglet.window.EventDispatcher):
    def __init__(self, default_group):
        self.group = PieceGroup(
            default_group.texture,
            default_group.normal_map)
        self.pieces = dict()
        self.step = (0, 0)
        self.is_mouse_down = True

    def select(self, piece):
        if piece.pid not in self.pieces:
            self.drop_everything()
            self.dispatch_event(
                'on_view_select_pieces',
                [piece.pid]
            )
            self.pieces = {piece.pid: piece}
            if piece.is_small:
                piece.group = self.group

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
                piece.group = self.group
        t1 = time.time()
        print(f"{len(new_pieces)}: {t1 - t0}")

    def mouse_up(self):
        self.dispatch_event(
            'on_view_pieces_moved',
            list(self.pieces),
            self.group.x - self.step[0],
            self.group.y - self.step[1]
        )
        self.step = (
            self.group.x,
            self.group.y
        )
        if len(self.pieces) == 1:
            self.drop_everything()
        self.is_mouse_down = False

    def drop_everything(self):
        for pid, piece in self.pieces.items():
            if piece.is_small:
                piece.group = piece.default_group

            piece.commit_position()

        self.pieces = dict()
        self.group.set_position(0, 0, self.group.z)
        self.step = 0, 0

    def drop_pieces(self, pids):
        pids_in_hand = pids.intersection(self.pieces)
        if len(pids_in_hand) == len(self.pieces):
            self.mouse_up()
            self.drop_everything()
        else:
            self.dispatch_event(
                'on_view_pieces_moved',
                list(pids_in_hand),
                self.group.x - self.step[0],
                self.group.y - self.step[1]
            )
            for pid in pids_in_hand:
                piece = self.pieces[pid]
                if piece.is_small:
                    piece.group = piece.default_group

                piece.commit_position()
                self.pieces.pop(pid)

    def move(self, dx, dy):
        if self.is_mouse_down and not self.is_empty:
            self.group.move(dx, dy, 0)
            for piece in self.pieces.values():
                piece.remember_relative_position(dx, dy, 0)

    def snap_piece_to_position(self, piece, x, y, z):
        if piece.pid in self.pieces and piece.is_small:
            piece.set_position(
                x - self.group.x,
                y - self.group.y,
                z - self.group.z
            )
            piece.remember_position(x, y, z)
        else:
            piece.set_position(x, y, z)

    @property
    def is_empty(self):
        return len(self.pieces) == 0


def _is_digit_key(symbol):
    return pyglet.window.key._0 <= symbol <= pyglet.window.key._9


def _digit_from_key(symbol):
    return symbol - pyglet.window.key._0


View.register_event_type('on_mouse_down')
View.register_event_type('on_mouse_up')
View.register_event_type('on_selection_box')
View.register_event_type('on_key_press')
View.register_event_type('on_cheat')
View.register_event_type('on_move_pieces_to_tray')
View.register_event_type('on_toggle_visibility')
View.register_event_type('on_view_spread_out')

Hand.register_event_type('on_view_pieces_moved')
Hand.register_event_type('on_view_select_pieces')

OrthographicProjection.register_event_type('on_pan')
