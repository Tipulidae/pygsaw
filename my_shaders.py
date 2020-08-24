from pyglet import graphics, gl
# import pyglet

#
# pyglet.options['debug_gl'] = True
# pyglet.options['debug_gl_shaders'] = True


piece_vertex_source = """#version 330 core
    in vec4 position;
    in vec4 colors;
    in vec3 tex_coords;
    in float pid;

    out vec4 vertex_colors;
    out vec3 texture_coords;

    uniform WindowBlock
    {
        mat4 projection;
        mat4 view;
    } window;
    
    uniform vec3 translate[16];

    mat4 m_translation = mat4(1.0);

    void main()
    {
        m_translation[3].xyz = translate[int(pid)];
        //m_translation[3].xyz = vec3(10.0*float(pid), 100, 0);
        gl_Position = window.projection * window.view * m_translation * position;

        vertex_colors = colors;
        texture_coords = tex_coords;
    }
"""

piece_fragment_source = """#version 330 core
    in vec4 vertex_colors;
    in vec3 texture_coords;
    out vec4 final_colors;

    uniform sampler2D sprite_texture;

    void main()
    {
        final_colors = texture(sprite_texture, texture_coords.xy) * vertex_colors;
    }
"""


piece_program = None
piece_vertex_shader = None
piece_fragment_shader = None


def load_my_shaders():

    global piece_program
    global piece_vertex_shader
    global piece_fragment_shader
    if piece_program is None:
        piece_vertex_shader = graphics.shader.Shader(
            piece_vertex_source, 'vertex'
        )
        piece_fragment_shader = graphics.shader.Shader(
            piece_fragment_source, 'fragment'
        )
        piece_program = graphics.shader.ShaderProgram(
            piece_vertex_shader, piece_fragment_shader
        )

    return piece_program

# piece_program = None
def write_to_uniform(name, data):
    print(f"write_to_uniform {piece_program}, {name}, {data}")
    pid = gl.GLuint(piece_program.id)
    loc = gl.glGetUniformLocation(pid, name.encode('utf8'))
    gl.glUseProgram(pid)
    for offset, values in data:
        gl.glUniform3f(loc + offset, *values)