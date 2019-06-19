import ctypes
from OpenGL import GL as gl
from OpenGL.GL import shaders
from shader_filter import (ShaderFilter, TEXTURE_VERTICES,
                           FILTER_VERTICES, ORTH_VERTICES)
from array import array
import sdl2
from PIL import Image

VERT_SOURCE = """
#version 330

uniform mat4 model_matrix;
uniform mat4 view_matrix;
uniform mat4 proj_matrix;

in vec2 vert_coord;
in vec2 vert_tex_coord;
in vec4 vert_color;
out vec2 frag_tex_coord;
out vec4 frag_color;
void main()
{
    mat4 _model_matrix = model_matrix;
    _model_matrix[3][0] = vert_coord.x;
    _model_matrix[3][1] = vert_coord.y;
    mat4 mv_matrix = view_matrix * _model_matrix;
    vec4 cc_vertex = mv_matrix * vec4(0.0, 0.0, 0.0, 1.0);
    frag_tex_coord = vert_tex_coord;
    frag_color = vert_color;
    gl_Position = proj_matrix * cc_vertex;
}"""

FRAG_SOURCE = """
#version 330

uniform sampler2D tex;

in vec2 frag_tex_coord;
in vec4 frag_color;
out vec4 out_color;

void main()
{
    out_color = texture(tex, frag_tex_coord) * frag_color;
}"""


# from https://gist.github.com/hurricanerix/3be8221128d943ae2827
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


class ConsoleFilter(ShaderFilter):
    hard_limit_chars = 10000

    colors = array("f")

    coords = array("f")

    tex_coords = array("f")

    indexes = array("I")

    attrib_locs = {
        "vert_coord": -1,
        "vert_tex_coord": -1,
        "vert_color": -1,
    }

    uniform_locs = {
        "model_matrix": -1,
        "view_matrix": -1,
        "proj_matrix": -1,
    }

    bufferss = {
        "vert_coord": -1,
        "vert_tex_coord": -1,
        "vert_color": -1,
    }

    index_buffers = {
        "vert_indexes": -1,
    }

    texture_ids = {
        "font": -1,
    }

    img_dimensions = (-1, -1)

    def __init__(self):
        self.init_shader()
        self.init_font_texture()

    def init_font_texture(self):
        img = Image.open('font/font_tex.png')
        image_bytes = img.convert("RGBA").tobytes("raw", "RGBA", 0 - 1)
        self.img_dimensions = img.size
        img.close()
        self.texture_ids['font'] = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_ids['font'])
        gl.glTexParameter(gl.GL_TEXTURE_2D,
                          gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameter(gl.GL_TEXTURE_2D,
                          gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8,
                        self.img_dimensions[0], self.img_dimensions[1], 0,
                        gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_bytes)

    def backspace(self, n=1):
        self.indexes = self.indexes[:n*-6]
        self.coords = self.coords[:n*-2*4]
        self.tex_coords = self.tex_coords[:n*-2*4]
        self.colors = self.colors[:n*-4*4]

    def _add_text(self, text, offset):
        """
        Only used for adding strings with no newlines
        """
        x = 0
        y = 0
        font_height = self.img_dimensions[1] / 16
        font_width = self.img_dimensions[0] / 16
        font_frac = 1.0 / 16.0
        for char in text:
            i = len(self.coords)/2
            tex_x = int(ord(char) % 16) * font_frac
            tex_y = int(ord(char)/16) * font_frac
            self.indexes += array("I", [i+1,     # 0,0
                                        i+3,     # 1,0
                                        i+2,     # 1,1
                                        i,       # 0,1
                                        i+1,     # 0,0
                                        i+2, ])  # 1,1

            self.coords += array('f', [x+offset[0], y+offset[1]+font_height,
                                       x+offset[0], y+offset[1],
                                       x+offset[0]+font_width,
                                       y+offset[1]+font_height,
                                       x+offset[0]+font_width, y+offset[1], ])

            self.tex_coords += array('f', [tex_x, tex_y,
                                           tex_x, tex_y+font_frac,
                                           tex_x+font_frac, tex_y,
                                           tex_x+font_frac, tex_y+font_frac, ])

            self.colors += array('f', [1.0, 1.0, 1.0, 1.0,
                                       1.0, 1.0, 1.0, 1.0,
                                       1.0, 1.0, 1.0, 1.0,
                                       1.0, 1.0, 1.0, 1.0, ])

            x += font_width

        num_chars = len(self.indexes)/6
        if num_chars > self.hard_limit_chars:
            # truncate a bit more to limit array resizing
            target_shrink = self.hard_limit_chars - 3000
            self.indexes = self.indexes[-6 * target_shrink:]
            self.coords = self.coords[2 * -4 * target_shrink:]
            self.tex_coords = self.tex_coords[2*-4*target_shrink:]
            self.colors = self.colors[4*-4*target_shrink:]
            self.indexes = array(
                'I', [i-(num_chars-target_shrink)*4 for i in self.indexes])

    def _shift_up(self):
        char_height = self.img_dimensions[1]/16
        for i in range(1, len(self.coords), 2):
            self.coords[i] += char_height

    def add_str(self, s, offset):
        """
        Used to add a string typed from the used to the console
        """
        text = s
        while "\n" in text:
            text_split = text.split('\n', 1)
            t = text_split[0]
            self._add_text(t, offset)
            self._shift_up()
            text = text_split[1]

        self._add_text(text, offset)
        self.update_buffer_data()

    def cleanup_shader(self):
        """
        Frees any resources used by shader
        """
        if(self.vao != -1):
            gl.glDeleteVertexArrays(1, int(self.vao))
            self.vao = -1
        for k, v in self.buffers.iteritems():
            if v != -1:
                gl.glDeleteBuffers(1, int(v))
                self.buffers[k] = -1
        if self.shader != -1:
            gl.glDeleteProgram(self.shader)
            self.shader = -1
        for k, v in self.texture_ids.iteritems():
            if v != -1:
                gl.glDeleteTextures(int(v))
                self.texture_ids[k] = -1

    def init_shader(self):
        """
        set up the console text shader
        """
        vert_prog = self._compile_shader(VERT_SOURCE, gl.GL_VERTEX_SHADER)
        frag_prog = self._compile_shader(FRAG_SOURCE, gl.GL_FRAGMENT_SHADER)
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

        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)
        self.buffers['vert_coord'] = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffers['vert_coord'])
        gl.glVertexAttribPointer(self.attrib_locs['vert_coord'], 2,
                                 gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(self.attrib_locs['vert_coord'])

        self.buffers['vert_tex_coord'] = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffers['vert_tex_coord'])
        gl.glVertexAttribPointer(self.attrib_locs['vert_tex_coord'], 2,
                                 gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(self.attrib_locs['vert_tex_coord'])

        self.buffers['vert_color'] = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffers['vert_color'])
        gl.glVertexAttribPointer(self.attrib_locs['vert_color'], 4,
                                 gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(self.attrib_locs['vert_color'])

        self.index_buffers['vert_indexes'] = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER,
                        self.index_buffers['vert_indexes'])
        gl.glActiveTexture(gl.GL_TEXTURE0)

    def clear(self):
        self.coords = array('f')
        self.tex_coords = array('f')
        self.colors = array('f')
        self.indexes = array('I')

    def update_buffer_data(self):
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffers['vert_coord'])
        gl.glBufferData(gl.GL_ARRAY_BUFFER,
                        self.coords.tostring(), gl.GL_STATIC_DRAW)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffers['vert_tex_coord'])
        gl.glBufferData(gl.GL_ARRAY_BUFFER,
                        self.tex_coords.tostring(), gl.GL_STATIC_DRAW)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffers['vert_color'])
        gl.glBufferData(gl.GL_ARRAY_BUFFER,
                        self.colors.tostring(), gl.GL_STATIC_DRAW)

        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER,
                        self.index_buffers['vert_indexes'])
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER,
                        self.indexes.tostring(), gl.GL_STATIC_DRAW)

    def render(self, offset, window_dimensions):
        font_height = self.img_dimensions[1] / 16
        font_width = self.img_dimensions[0] / 16
        gl.glBindVertexArray(self.vao)
        gl.glViewport(0, 0, window_dimensions[0],
                      window_dimensions[1])
        gl.glUseProgram(self.shader)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_ids['font'])
        view_matrix = get_view_matrix(1.0, 1.0)
        proj_matrix = get_projection_matrix(0, window_dimensions[0],
                                            0, window_dimensions[1])
        gl.glUniformMatrix4fv(self.uniform_locs['view_matrix'],
                              1, gl.GL_TRUE, view_matrix)
        gl.glUniformMatrix4fv(self.uniform_locs['proj_matrix'],
                              1, gl.GL_TRUE, proj_matrix)
        model_matrix = get_4x4_transform(font_width, font_height,
                                         offset[0], offset[1], 1.0)
        gl.glUniformMatrix4fv(self.uniform_locs['model_matrix'], 1,
                              gl.GL_TRUE, model_matrix)

        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER,
                        self.index_buffers['vert_indexes'])
        gl.glDrawElements(gl.GL_TRIANGLES, len(self.indexes),
                          gl.GL_UNSIGNED_INT, ctypes.c_void_p(0))
