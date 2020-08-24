from pyglet import gl, graphics
from pyglet.graphics.shader import Shader, ShaderProgram


piece_vs = """#version 330 core
    in vec4 position;
    in vec4 colors;
    in vec3 tex_coords;

    out vec4 vertex_colors;
    out vec3 texture_coords;

    uniform WindowBlock
    {
        mat4 projection;
        mat4 view;
    } window;
    
    uniform vec3 translate;

    mat4 m_translation = mat4(1.0);

    void main()
    {
        m_translation[3].xyz = translate;
        gl_Position = window.projection * window.view * m_translation * position;

        vertex_colors = colors;
        texture_coords = tex_coords;
    }
"""

piece_fs = """#version 330 core
    in vec4 vertex_colors;
    in vec3 texture_coords;
    out vec4 final_colors;

    uniform sampler2D sprite_texture;

    void main()
    {
        final_colors = texture(sprite_texture, texture_coords.xy) * vertex_colors;
    }
"""

shape_vs = """#version 150 core
    in vec4 position;
    in vec4 colors;

    out vec4 vertex_colors;

    uniform WindowBlock
    {
        mat4 projection;
        mat4 view;
    } window;

    void main()
    {
        gl_Position = window.projection * window.view * position;
        vertex_colors = colors;
    }
"""

shape_fs = """#version 150 core
    in vec4 vertex_colors;
    out vec4 final_color;

    void main()
    {
        final_color = vertex_colors;
    }
"""


piece_vertex_shader = None
piece_fragment_shader = None


def make_piece_shader():
    global piece_vertex_shader
    global piece_fragment_shader
    if piece_vertex_shader is None:
        piece_vertex_shader = Shader(piece_vs, 'vertex')
    if piece_fragment_shader is None:
        piece_fragment_shader = Shader(piece_fs, 'fragment')

    return ShaderProgram(piece_vertex_shader, piece_fragment_shader)


def make_shape_shader():
    vs = Shader(shape_vs, 'vertex')
    fs = Shader(shape_fs, 'fragment')
    return ShaderProgram(vs, fs)


def write_to_uniform(program, name, data):
    pid = gl.GLuint(program.id)
    loc = gl.glGetUniformLocation(pid, name.encode('utf8'))
    gl.glUseProgram(pid)
    gl.glUniform3f(loc, *data)
