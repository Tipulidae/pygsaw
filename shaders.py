from pyglet import gl
from pyglet.graphics.shader import Shader, ShaderProgram


piece_vs = """#version 330 core
    in vec4 position;
    in vec4 colors;
    in vec3 tex_coords;

    out vec4 vertex_colors;
    out vec3 texture_coords;
    out vec4 col;

    uniform WindowBlock
    {
        mat4 projection;
        mat4 view;
    } window;  

    uniform vec3 translate;
    uniform float hidden;

    mat4 m_translation = mat4(1.0);

    void main()
    {
        if (hidden > 0.0) {
            gl_Position = vec4(0, 0, 0, 0);
        } else {
            texture_coords = tex_coords;
            col = colors;
            m_translation[3].xyz = translate;
            gl_Position = window.projection * window.view * m_translation * position;
        }
    }
"""

piece_fs = """#version 330 core
    in vec4 col;
    in vec3 texture_coords;
    out vec4 final_colors;

    uniform sampler2D diffuse_map;
    uniform sampler2D normal_map;
    uniform float game_over;

    void main()
    {
        // Normal mapping, but with a fixed directional light and 
        // orthographic projection, meaning that I don't need to calculate the 
        // TBN matrix directly (it should be the identity matrix). 
        // Credits to https://learnopengl.com/Advanced-Lighting/Normal-Mapping
        vec3 color = texture(diffuse_map, texture_coords.xy).rgb;
        if (game_over > 0.0) {
            final_colors = vec4(color, 1);
        } else {
        
            vec3 normal = texture(normal_map, texture_coords.xy).rgb;
            normal = normalize(normal * 2.0 - 1.0);
            vec3 ambient = 0.1 * color;
    
            vec3 light_dir = normalize(vec3(-0.5,-0.5, 1));
            float diff = max(dot(light_dir, normal), 0.0);
            vec3 diffuse = diff * color;
    
            vec3 view_dir = vec3(0, 0, 1);
            vec3 reflect_dir = reflect(-light_dir, normal);
            vec3 halway_dir = normalize(light_dir + view_dir);
            float spec = pow(max(dot(normal, halway_dir), 0.0), 32.0);
    
            vec3 specular = vec3(0.2) * spec;
            final_colors = vec4(ambient + diffuse + specular, 1.0) * col;
        }
    }
"""

shape_vs = """#version 330 core
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

shape_fs = """#version 330 core
    in vec4 vertex_colors;
    out vec4 final_color;

    void main()
    {
        final_color = vertex_colors;
    }
"""


table_vs = """#version 330 core
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

    void main()
    {
        texture_coords = tex_coords;
        vertex_colors = colors;
        gl_Position = window.projection * window.view * position;
    }
"""

table_fs = """#version 330 core
    in vec4 vertex_colors;
    in vec3 texture_coords;
    out vec4 final_colors;

    uniform sampler2D diffuse_map;

    void main()
    {
        vec3 color = texture(diffuse_map, texture_coords.xy).rgb;
        final_colors = vec4(color, 1.0) * vertex_colors;
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


def make_table_shader():
    vs = Shader(table_vs, 'vertex')
    fs = Shader(table_fs, 'fragment')
    return ShaderProgram(vs, fs)



def write_to_uniform(program, name, data):
    pid = gl.GLuint(program.id)
    loc = gl.glGetUniformLocation(pid, name.encode('utf8'))
    gl.glUseProgram(pid)
    gl.glUniform3f(loc, *data)
