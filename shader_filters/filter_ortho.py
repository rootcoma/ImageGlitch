import ctypes
from OpenGL import GL as gl
from shader_filter import (ShaderFilter, ORTH_VERTICES,
                           TEXTURE_VERTICES, FILTER_VERTICES)
from array import array
import sdl2

# https://stackoverflow.com/questions/11125827/how-to-use-glbufferdata-in-pyopengl

ORTH_VERT_SOURCE = """
#version 330

uniform mat4 model_matrix;
uniform mat4 view_matrix;
uniform mat4 proj_matrix;

in vec4 mc_vertex;
in vec2 vert_tex_coord;
out vec2 frag_tex_coord;

void main()
{
  mat4 mv_matrix = view_matrix * model_matrix;
  vec4 cc_vertex = mv_matrix * mc_vertex;
  frag_tex_coord = vert_tex_coord;
  gl_Position = proj_matrix * cc_vertex;
}"""

ORTH_FRAG_SOURCE = """
#version 330

uniform sampler2D tex;
in vec2 frag_tex_coord;
out vec4 frag_color;


void main()
{
    frag_color = texture(tex, frag_tex_coord);
}"""


def get_4x4_transform(scale_x, scale_y, trans_x, trans_y, trans_z):
    """Transform the from local coordinates to world coordinates.

    @return: transformation matrix used to transform from local coords
             to world coords.
    """
    transform = [[scale_x, 0.0, 0.0, trans_x],
                 [0.0, scale_y, 0.0, trans_y],
                 [0.0, 0.0, 1.0, trans_z],
                 [0.0, 0.0, 0.0, 1.0]]
    return transform


def get_projection_matrix(left, right, bottom, top):
    """Create a  orthographic projection matrix.

    U{Modern glOrtho2d<http://stackoverflow.com/questions/21323743/
    modern-equivalent-of-gluortho2d>}

    U{Orthographic Projection<http://en.wikipedia.org/wiki/
    Orthographic_projection_(geometry)>}

    """
    zNear = -25.0
    zFar = 25.0
    inv_z = 1.0 / (zFar - zNear)
    inv_y = 1.0 / (top - bottom)
    inv_x = 1.0 / (right - left)
    mat = [[(2.0 * inv_x), 0.0, 0.0, (-(right + left) * inv_x)],
           [0.0, (2.0 * inv_y), 0.0, (-(top + bottom) * inv_y)],
           [0.0, 0.0, (-2.0 * inv_z), (-(zFar + zNear) * inv_z)],
           [0.0, 0.0, 0.0, 1.0]]
    return mat


def get_view_matrix(x, y):
    scale_x = 1.0
    scale_y = 1.0
    trans_x = x
    trans_y = y
    layer = 1.0
    return get_4x4_transform(scale_x, scale_y, trans_x, trans_y, layer)


class OrthoFilter(ShaderFilter):
    attrib_locs = {
        "mc_vertex": -1,
        "vert_tex_coord": -1,
    }

    bufferss = {
        "mc_vertex": -1,
        "vert_tex_coord": -1,
    }

    def __init__(self):
        self.init_shader()

    def init_shader(self):
        """
        set up the orthogonal view final shader
        """
        self.attrib_locs = {
            "mc_vertex": -1,
            "vert_tex_coord": -1,
        }
        self.uniform_locs = {
            "model_matrix": -1,
            "view_matrix": -1,
            "proj_matrix": -1,
        }
        vert_prog = self._compile_shader(ORTH_VERT_SOURCE, gl.GL_VERTEX_SHADER)
        frag_prog = self._compile_shader(
            ORTH_FRAG_SOURCE, gl.GL_FRAGMENT_SHADER)
        self.shader = gl.glCreateProgram()
        gl.glAttachShader(self.shader, vert_prog)
        gl.glAttachShader(self.shader, frag_prog)
        gl.glLinkProgram(self.shader)
        assert (gl.glGetProgramiv(self.shader, gl.GL_LINK_STATUS) ==
                gl.GL_TRUE), (
            "Error: %s" % (gl.glGetProgramInfoLog(self.shader)))

        self.attrib_locs = {
            name: gl.glGetAttribLocation(self.shader, name)
            for name in self.attrib_locs
        }
        self.uniform_locs = {
            name: gl.glGetUniformLocation(self.shader, name)
            for name in self.uniform_locs
        }

        # Load vertices for final ortho view
        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)
        self.buffers['mc_vertex'] = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffers['mc_vertex'])

        gl.glBufferData(gl.GL_ARRAY_BUFFER, len(ORTH_VERTICES),
                        ORTH_VERTICES, gl.GL_STATIC_DRAW)
        gl.glVertexAttribPointer(self.attrib_locs['mc_vertex'], 4,
                                 gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(self.attrib_locs['mc_vertex'])

        self.buffers['vert_tex_coord'] = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffers['vert_tex_coord'])
        gl.glBufferData(gl.GL_ARRAY_BUFFER, len(TEXTURE_VERTICES),
                        TEXTURE_VERTICES, gl.GL_STATIC_DRAW)
        gl.glVertexAttribPointer(self.attrib_locs['vert_tex_coord'], 2,
                                 gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(self.attrib_locs['vert_tex_coord'])
        gl.glActiveTexture(gl.GL_TEXTURE0)

    def create_ortho_matrices(self, offset, scale,
                              window_dimensions, img_dimensions):
        """
        Create matrices for the orthogonal shaders uniform inputs
        """
        window_width, window_height = window_dimensions
        object_x = int(window_width/2 - img_dimensions[0]*scale/2) + offset[0]
        object_y = int(window_height/2 - img_dimensions[1]*scale/2) + offset[1]
        model_matrix = get_4x4_transform(int(img_dimensions[0] * scale),
                                         int(img_dimensions[1] * scale),
                                         object_x,
                                         object_y, 1.0)
        proj_matrix = get_projection_matrix(0, window_width, 0, window_height)
        view_matrix = get_view_matrix(1.0, 1.0)
        return model_matrix, proj_matrix, view_matrix

    def render(self, offset, scale, window_dimensions, img_dimensions):
        # Draw ortho view, to center image in screen
        (w, h) = window_dimensions
        gl.glViewport(0, 0, w, h)
        gl.glUseProgram(self.shader)
        model_matrix, proj_matrix, view_matrix = self.create_ortho_matrices(
            offset, scale, window_dimensions, img_dimensions)

        gl.glUniformMatrix4fv(self.uniform_locs['model_matrix'], 1,
                              gl.GL_TRUE, model_matrix)
        gl.glUniformMatrix4fv(self.uniform_locs['view_matrix'], 1,
                              gl.GL_TRUE, view_matrix)
        gl.glUniformMatrix4fv(self.uniform_locs['proj_matrix'], 1,
                              gl.GL_TRUE, proj_matrix)

        gl.glBindVertexArray(self.vao)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, int(len(ORTH_VERTICES)/4/4))
