import time
import math
import itertools
import glob

import pyglet
import pyglet.gl as gl
import pyglet.window.key as key
import vecrec
from tqdm import tqdm
from pyglet.math import Mat4
from humanfriendly import format_timespan

import earcut
from shaders import make_piece_shader, make_shape_shader, make_table_shader
from textures import make_normal_map
from file_picker import select_image
from bezier import Point, rotate_points, center_point


GROUP_COUNT = 2
PIECE_THRESHOLD = 3
MAX_Z_DEPTH = 5000000

PAN_KEYS = [key.W, key.A, key.S, key.D]


class PieceGroupFactory:
    default_groups = dict()
    big_groups = {tray: set() for tray in range(10)}
    hand_group = None
    _hide_borders = False

    @staticmethod
    def init_groups(texture, normal_map, visible_trays):
        PieceGroupFactory.default_groups = {
            tray: PieceGroup(texture, normal_map, tray=tray)
            for tray in range(10)
        }
        PieceGroupFactory.big_groups = {tray: set() for tray in range(10)}
        for tray in range(10):
            is_visible = tray in visible_trays
            PieceGroupFactory.toggle_visibility(tray, is_visible=is_visible)

        PieceGroupFactory.hand_group = PieceGroup(texture, normal_map)

    @staticmethod
    def get_piece_group(tray):
        return PieceGroupFactory.default_groups[tray]

    @staticmethod
    def toggle_visibility(tray, is_visible):
        PieceGroupFactory.default_groups[tray].set_visibility(is_visible)
        for group in PieceGroupFactory.big_groups[tray]:
            group.set_visibility(is_visible)

    @staticmethod
    def invert_border_visibility():
        hide_borders = not PieceGroupFactory._hide_borders
        PieceGroupFactory.set_border_visibility(hide_borders)

    @staticmethod
    def set_border_visibility(hide_borders=False):
        PieceGroupFactory._hide_borders = hide_borders
        for group in PieceGroupFactory.default_groups.values():
            group.set_border_visibility(hide_borders)

        for tray in range(10):
            for group in PieceGroupFactory.big_groups[tray]:
                group.set_border_visibility(hide_borders)

        PieceGroupFactory.hand_group.set_border_visibility(hide_borders)

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
    def __init__(self, texture, normal_map, tray=0, x=0, y=0, z=0, *args,
                 **kwargs):
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
        self.program['hide_borders'] = 0
        self.program['rotation'] = (
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        )
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

    def set_rotation(self, angle):
        c = math.cos(angle)
        s = math.sin(angle)
        self.program.use()
        self.program['rotation'] = (
            c, s, 0, 0,
            -s, c, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        )
        self.program.stop()

    def set_visibility(self, is_visible):
        self.program.use()
        if is_visible:
            self.program['hidden'] = 0.0
        else:
            self.program['hidden'] = 1.0
        self.program.stop()

    def set_border_visibility(self, hide_border):
        self.program.use()
        self.program['hide_borders'] = 1 if hide_border else 0
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
        return (
            other.__class__ is self.__class__ and
            self.program is other.program and
            self.parent is other.parent
        )

    def __hash__(self):
        return hash((id(self.parent), id(self.program)))


class TableGroup(pyglet.graphics.Group):
    def __init__(self, texture, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.texture = texture
        self.program = make_table_shader()
        self.program.use()
        self.program['diffuse_map'] = 0
        self.program.stop()

    def set_state(self):
        self.program.use()
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(self.texture.target, self.texture.id)
        # gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S,
        #                    gl.GL_MIRRORED_REPEAT)
        # gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T,
        #                    gl.GL_MIRRORED_REPEAT)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS)

    def unset_state(self):
        gl.glDisable(gl.GL_BLEND)
        gl.glBindTexture(self.texture.target, 0)
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
        aspect_x = self.clip_port.width / self.view_port.width
        aspect_y = self.clip_port.height / self.view_port.height
        return (
            self.clip_port.left + x * aspect_x,
            self.clip_port.bottom + y * aspect_y
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
            window_block.projection[:] = Mat4.orthogonal_projection(
                self.clip_port.left,
                self.clip_port.right,
                self.clip_port.bottom,
                self.clip_port.top,
                -MAX_Z_DEPTH,
                MAX_Z_DEPTH)
            if not self._view:
                # Set view to Identity Matrix
                self._view = Mat4()
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
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        self.is_panning = False
        self.is_paused = False

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
        if not self.is_paused:
            self.batch.draw()

    def toggle_pause(self, is_paused):
        self.is_paused = is_paused
        if is_paused:
            pyglet.clock.unschedule(self.update)
            self.is_panning = False

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.is_paused:
            return

        if self.keys[key.LCTRL]:
            if scroll_y > 0:
                self.my_projection.zoom(1.25, x, y)
            elif scroll_y < 0:
                self.my_projection.zoom(0.8, x, y)

    def update(self, dt):
        if self.keys[key.W]:
            self.my_projection.pan(0, self.pan_speed * dt)
        elif self.keys[key.S]:
            self.my_projection.pan(0, -self.pan_speed * dt)

        if self.keys[key.A]:
            self.my_projection.pan(-self.pan_speed * dt, 0)
        elif self.keys[key.D]:
            self.my_projection.pan(self.pan_speed * dt, 0)

    def on_key_press(self, symbol, modifiers):
        if self.is_paused:
            return

        if not self.is_panning and symbol in PAN_KEYS:
            pyglet.clock.schedule_interval(self.update, 1 / 120)
            self.is_panning = True

    def on_key_release(self, symbol, modifiers):
        if self.is_panning and not self._is_pan_key_pressed:
            pyglet.clock.unschedule(self.update)
            self.is_panning = False

    @property
    def _is_pan_key_pressed(self):
        return any([self.keys[k] for k in PAN_KEYS])


class NumberKeys:
    def __init__(self):
        self.pressed = {k: False for k in range(key._0, key._9 + 1)}
        self.is_shift = False
        self.last_pressed = 0

    def press(self, k):
        if k in self.pressed:
            self.pressed[k] = True
            self.last_pressed = k - key._0
        elif k == key.LSHIFT:
            self.is_shift = True

    def release(self, k):
        if k in self.pressed:
            self.pressed[k] = False
            self.last_pressed = k - key._0
        elif k == key.LSHIFT:
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
    def __init__(self, window):
        self.window = window
        self.window.push_handlers(self)
        self.projection = self.window.my_projection
        self.selection_box = SelectionBox(self.window.batch)

        self.pieces = None
        self.hand = None
        self.number_keys = NumberKeys()
        self.texture = None
        self.normal_map = None
        self.is_paused = False

        self.table = Table(self.window.batch)
        self.settings = None

        self.light_dir = 0
        # self.reset(texture, piece_data, visible_trays)

        # global PIECE_THRESHOLD
        # PIECE_THRESHOLD = big_piece_threshold

    def reset(self, texture, piece_data, visible_trays, settings):
        self.settings = settings
        self.texture = texture
        polygons = itertools.chain.from_iterable(
            map(lambda pd: pd['polygons'].values(), piece_data)
        )
        print("Making normal map...")
        self.normal_map = make_normal_map(
            polygons,
            texture.width,
            texture.height,
            piece_data[0]['width'],
            piece_data[0]['height'],
        )

        PieceGroupFactory.init_groups(texture, self.normal_map, visible_trays)

        self.pieces = dict()
        self.hand = Hand()
        self.projection.push_handlers(on_pan=self.hand.move)
        self.projection.push_handlers(on_pan=self.selection_box.drag)

        for data in tqdm(piece_data, desc='Creating pieces'):
            self.create_piece(**data)

    def destroy_pieces(self):
        for piece in self.pieces.values():
            for vl in piece.vertex_list:
                vl.delete()

        self.table.destroy_table()

    def new_jigsaw(self, settings):
        self.hand.drop_everything()
        self.dispatch_event(
            'on_new_game',
            settings
        )

    def create_piece(self, pid, polygons, position, rotation, width, height, tray):
        self.pieces[pid] = Piece(
            pid,
            polygons,
            tray,
            position,
            rotation,
            width,
            height,
            self.texture,
            self.normal_map,
            self.window.batch
        )
        self.hand.group.z += len(polygons)

    def toggle_pause(self, is_paused):
        self.window.toggle_pause(is_paused)
        self.is_paused = is_paused
        if is_paused:
            if self.hand.is_mouse_down:
                self.hand.mouse_up()
                self.selection_box.deactivate()

    def on_mouse_press(self, x_, y_, button, modifiers):
        """
        The x_, y_ tuple is the view coordinates of the mouse pointer, in
        which 0, 0 is the bottom left corner of the window and
        window.width, window.height is the top right corner. When the view is
        zoomed and/or panned, the view coordinates will differ from the clip-
        coordinates, which correspond to the "actual" coordinates in the model.
        """
        if self.is_paused:
            return
        x, y = self.projection.view_to_clip_coord(x_, y_)
        is_shift = modifiers & key.MOD_SHIFT
        self.dispatch_event('on_mouse_down', x, y, is_shift)
        self.hand.is_mouse_down = True

    def on_mouse_release(self, x_, y_, button, modifiers):
        if self.is_paused:
            return

        self.hand.is_mouse_down = False
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
        if self.is_paused:
            return

        if self.selection_box.is_active:
            x, y = self.projection.view_to_clip_coord(x_, y_)
            self.selection_box.drag_to(x, y)
        elif not self.hand.is_empty:
            dx = dx_ / self.projection.zoom_level
            dy = dy_ / self.projection.zoom_level
            self.hand.move(dx, dy)

    def on_mouse_scroll(self, x_, y_, scroll_x, scroll_y):
        def allow_rotation():
            return (
                self.settings.piece_rotation
                and self.hand.is_empty
                and not self.is_paused
                and not self.window.keys[key.LCTRL]
            )
        if allow_rotation():
            x, y = self.projection.view_to_clip_coord(x_, y_)
            self.dispatch_event('on_scroll', x, y, scroll_y)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.PAUSE:
            self.dispatch_event('on_pause', not self.is_paused)
        if symbol == key.R and modifiers & key.MOD_CTRL:
            select_image(
                callback=self.new_jigsaw,
                settings=self.settings
            )

        if self.is_paused:
            return

        self.number_keys.press(symbol)
        if symbol == key.C:
            self.hand.drop_everything()
            self.dispatch_event('on_cheat', 1)
        if symbol == key.X:
            self.hand.drop_everything()
            self.dispatch_event('on_cheat', 100)
        if symbol == key.SPACE:
            self.hand.mouse_up()
            pids = list(self.hand.pieces)
            if len(pids) > 0:
                self.dispatch_event('on_view_spread_out', pids)
        if symbol == key.T:
            self.table.cycle_texture()
        if symbol == key.ESCAPE:
            self.hand.mouse_up()
            self.hand.drop_everything()
        if symbol == key.F5:
            self.dispatch_event('on_quicksave')
        if symbol == key.F9:
            self.dispatch_event('on_quickload')
        if symbol == key.PERIOD:
            self.dispatch_event('on_info')
        if symbol == key.COMMA:
            PieceGroupFactory.invert_border_visibility()
        if _is_digit_key(symbol):
            tray = _digit_from_key(symbol)
            if modifiers & key.MOD_CTRL:
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

    def move_piece(self, pid, x, y, z):
        self.hand.move_piece(self.pieces[pid], x, y, z)

    def merge_pieces(self, pid1, pid2):
        self.pieces[pid1].merge(self.pieces[pid2])
        self.pieces.pop(pid2)

    def remember_new_z_levels(self, msg):
        self.hand.group.move(0, 0, len(msg))
        for z, pid in msg:
            self.pieces[pid].remember_z_position(z)

    def drop_specific_pieces_from_hand(self, pids):
        self.hand.drop_pieces(pids)

    def rotate_piece(self, pid, rotation, position):
        self.pieces[pid].rotate(rotation, position)

    def set_visibility(self, tray, is_visible):
        PieceGroupFactory.toggle_visibility(tray, is_visible)

    def print_info(self, elapsed_seconds, percent_complete):
        print(
            f"Completed {percent_complete:.1f}% in "
            f"{format_timespan(elapsed_seconds)}"
        )

    def game_over(self, elapsed_seconds):
        PieceGroupFactory.set_border_visibility(hide_borders=True)
        print(
            f"Congratulations, you won! \n"
            f"Image: {self.settings.image_path} \n"
            f"Dimensions: {self.settings.nx} * {self.settings.ny} = {self.settings.num_pieces} \n"
            f"Elapsed time: {format_timespan(elapsed_seconds)} \n"
            f"Piece rotation: {self.settings.piece_rotation}"
        )


class Piece:
    def __init__(self, pid, polygons, tray, position, rotation, width, height,
                 texture, normal_map, batch):
        self.pid = pid
        self.texture = texture
        self.normal_map = normal_map
        self.size = len(polygons)
        self.batch = batch
        self.default_group = PieceGroupFactory.get_piece_group(tray)
        self.groups = []
        if self.is_small:
            self._group = self.default_group
        else:
            self._group = PieceGroupFactory.new_big_group(tray)
            self.groups = [self.group]

        self._x, self._y, self._z, self._r = 0, 0, 0, 0

        self.polygons = []
        self.vertex_list = []
        for polygon in polygons.values():
            vl = self._create_vertices(polygon, width, height)
            self.polygons.append(polygon)
            self.vertex_list.append(vl)

        self.set_position(*position, rotation)

    def _create_vertices(self, polygon, width, height):
        sx = self.texture.tex_coords[6] / self.texture.width
        sy = self.texture.tex_coords[7] / self.texture.height
        offset_x = width // 2
        offset_y = height // 2

        vertices = []
        earcut_input = []
        tex_coords = []
        for p in polygon:
            vertices.append(p.x)
            vertices.append(p.y)
            vertices.append(0)

            earcut_input.append(p.x)
            earcut_input.append(p.y)

            tex_coords.append(sx * (p.x - offset_x))
            tex_coords.append(sy * (p.y - offset_y))
            tex_coords.append(0)

        indices = earcut.earcut(earcut_input)

        n = len(vertices) // 3
        vertex_list = self.batch.add_indexed(
            n,
            pyglet.gl.GL_TRIANGLES,
            self.group,
            indices,
            ('position3f/static', tuple(vertices)),
            ('colors4Bn/static', (255, 255, 255, 255) * n),
            ('tex_coords3f/static', tuple(tex_coords)),
            ('orientation1f/dynamic', (0.0,) * n)
        )
        return vertex_list

    def move(self, dx, dy, dz):
        self._x += dx
        self._y += dy
        self._z += dz

    def rotate(self, rotation, position):
        self._r = rotation
        self._x = position.x
        self._y = position.y
        self.commit_position()

    def set_position(self, x, y, z, r):
        self._x, self._y, self._z, self._r = x, y, z, r
        if self.is_small:
            self._update_vertices(x, y, z)
        else:
            self._update_groups(x, y, z)

    def _update_vertices(self, x, y, z):
        for polygon, vertex_list in zip(self.polygons, self.vertex_list):
            new_vertex_list = []
            for p in rotate_points(polygon, Point(0, 0), self.angle):
                new_vertex_list.append(p.x + x)
                new_vertex_list.append(p.y + y)
                new_vertex_list.append(z)

            vertex_list.position[:] = tuple(new_vertex_list)
            vertex_list.orientation[:] = (self._r, ) * len(polygon)

    def _update_groups(self, x, y, z):
        for group in self.groups:
            group.set_position(x, y, z)
            group.set_rotation(self.angle)

    def set_default_tray(self, tray):
        if self.is_small:
            self.default_group = PieceGroupFactory.get_piece_group(tray)
        else:
            for group in self.groups:
                PieceGroupFactory.move_to_group(group, tray)

    def remember_position(self, x, y, z, r):
        self._x, self._y, self._z, self._r = x, y, z, r
        if self.is_big:
            self.commit_position()

    def remember_z_position(self, z):
        self.remember_position(self._x, self._y, z, self._r)

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
            other._r = 0
            other.set_position(0, 0, 0)
            g = max(self.groups, key=(lambda group: group.size))
            g.size += other.size
            other.group = g
        elif self.is_small and other.is_big:
            x, y, z, r = self.x, self.y, self.z, self.r
            tray = self.default_group.tray
            self.set_position(0, 0, 0, 0)
            self.groups = other.groups
            g = max(self.groups, key=(lambda group: group.size))
            g.size += self.size
            self.group = g
            self.remember_position(x, y, z, r)
            self.set_default_tray(tray)
        elif self.is_small and other.is_small:
            if self.size + other.size >= PIECE_THRESHOLD:
                x, y, z, r = self.x, self.y, self.z, self.r
                self.set_position(0, 0, 0, 0)
                other.set_position(0, 0, 0, 0)
                tray = self.default_group.tray
                group = PieceGroupFactory.new_big_group(tray)
                group.size = self.size + other.size
                self.groups = [group]
                self.group = other.group = group
                self.remember_position(x, y, z, r)
            else:
                other.set_position(self.x, self.y, self.z, self.r)
                other.group = self.group

        self.polygons += other.polygons
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
    def r(self):
        return self._r

    @property
    def angle(self):
        return self._r * math.pi / 2

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


class Table:
    def __init__(self, batch):
        self.batch = batch
        self.image_paths = glob.glob('resources/textures/*.jpg')
        self.index = 0
        self.group = TableGroup(None)
        self.vertex_list = None
        self.create_table()

    def cycle_texture(self):
        self.index = (self.index + 1) % len(self.image_paths)
        self.destroy_table()
        self.create_table()

    def destroy_table(self):
        self.vertex_list.delete()

    def create_table(self):
        image_path = self.image_paths[self.index]
        texture = pyglet.image.load(image_path).get_texture()
        self.group.texture = texture

        table_width = 32768
        table_height = 32768
        original_vertices = [
            -table_width/2, -table_height/2, -1,
            table_width/2, -table_height/2, -1,
            table_width/2, table_height/2, -1,
            -table_width/2, table_height/2, -1
        ]
        indices = [
            0, 1, 2, 0, 2, 3
        ]
        tex_coords = [
            0, 0, 0,
            table_width/texture.width, 0, 0,
            table_width/texture.width, table_height/texture.height, 0,
            0, table_height/texture.height, 0
        ]

        n = len(original_vertices) // 3

        self.vertex_list = self.batch.add_indexed(
            n,
            pyglet.gl.GL_TRIANGLES,
            self.group,
            indices,
            ('position3f/static', tuple(original_vertices)),
            ('colors4Bn/static', (255, 255, 255, 255) * n),
            ('tex_coords3f/static', tuple(tex_coords))
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
            4, gl.GL_LINE_LOOP, self.group,
            ('position3f/dynamic', (0,) * 12),
            ('colors3B/static', (255,) * 12)
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
    def __init__(self):
        self.group = PieceGroupFactory.hand_group
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

    def move_piece(self, piece, x, y, z):
        if piece.pid in self.pieces and piece.is_small:
            piece.set_position(
                x - self.group.x,
                y - self.group.y,
                z - self.group.z,
                piece.r
            )
            piece.remember_position(x, y, z, piece.r)
        else:
            piece.set_position(x, y, z, piece.r)

    @property
    def is_empty(self):
        return len(self.pieces) == 0


def _is_digit_key(symbol):
    return key._0 <= symbol <= key._9


def _digit_from_key(symbol):
    return symbol - key._0


View.register_event_type('on_mouse_down')
View.register_event_type('on_mouse_up')
View.register_event_type('on_scroll')
View.register_event_type('on_selection_box')
View.register_event_type('on_key_press')
View.register_event_type('on_cheat')
View.register_event_type('on_move_pieces_to_tray')
View.register_event_type('on_toggle_visibility')
View.register_event_type('on_view_spread_out')
View.register_event_type('on_new_game')
View.register_event_type('on_quicksave')
View.register_event_type('on_quickload')
View.register_event_type('on_pause')
View.register_event_type('on_info')

Hand.register_event_type('on_view_pieces_moved')
Hand.register_event_type('on_view_select_pieces')

OrthographicProjection.register_event_type('on_pan')
