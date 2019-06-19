import ctypes
from OpenGL import GL as gl
from OpenGL.GL import shaders
import random
from array import array

# Identity 4x4 matrix
ORTH_VERTICES = [0.0, 0.0, 0.0, 1.0,
                 1.0, 0.0, 0.0, 1.0,
                 1.0, 1.0, 0.0, 1.0,
                 0.0, 1.0, 0.0, 1.0,
                 0.0, 0.0, 0.0, 1.0,
                 1.0, 1.0, 0.0, 1.0]
ORTH_VERTICES = array("f", ORTH_VERTICES).tostring()

# Coordinates used for textures
TEXTURE_VERTICES = [0.0, 0.0,
                    1.0, 0.0,
                    1.0, 1.0,
                    0.0, 1.0,
                    0.0, 0.0,
                    1.0, 1.0]
TEXTURE_VERTICES = array("f", TEXTURE_VERTICES).tostring()

# Basic vertices for full screen display
FILTER_VERTICES = [-1.0, -1.0,
                   1.0, -1.0,
                   1.0, 1.0,
                   -1.0, 1.0,
                   -1.0, -1.0,
                   1.0, 1.0]
FILTER_VERTICES = array("f", FILTER_VERTICES).tostring()


class ShaderFilter:
    shader = -1  # Shader program

    vao = -1  # Vertex array object

    # Locations of attributes (Not needed after creation)
    attrib_locs = {
        "vert_coord": -1,
        "vert_tex_coord": -1,
    }
    uniform_locs = {
        "rand": -1,
        "frame": -1,
    }

    # Buffer storage for vertex arrays
    buffers = {
        "vert_coord": -1,
        "vert_tex_coord": -1,
    }

    frag_source = None  # frag shader source to be defined in derived classes

    vert_source = None  # vert shader source to be defined in derived classes

    img = None

    def __init__(self):
        self.init_shader()

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

    def init_shader(self):
        """
        Creates the filter shader that filters the imported image.
        """
        vert_prog = self._compile_shader(self.vert_source, gl.GL_VERTEX_SHADER)
        frag_prog = self._compile_shader(
            self.frag_source, gl.GL_FRAGMENT_SHADER)

        self.shader = gl.glCreateProgram()
        gl.glAttachShader(self.shader, vert_prog)
        gl.glAttachShader(self.shader, frag_prog)
        gl.glLinkProgram(self.shader)
        gl.glUseProgram(self.shader)
        assert (gl.glGetProgramiv(self.shader, gl.GL_LINK_STATUS) ==
                gl.GL_TRUE), "Error: %s" % (gl.glGetProgramInfoLog(shader))
        self.attrib_locs = {
            name: gl.glGetAttribLocation(self.shader, name)
            for name in self.attrib_locs
        }
        self.uniform_locs = {
            name: gl.glGetUniformLocation(self.shader, name)
            for name in self.uniform_locs
        }

        # Create vertex array for filter
        vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(vao)

        # Load coordinates for filter shader
        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)
        vertex_buffer = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertex_buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, len(FILTER_VERTICES),
                        FILTER_VERTICES, gl.GL_STATIC_DRAW)
        gl.glVertexAttribPointer(self.attrib_locs['vert_coord'], 2,
                                 gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(self.attrib_locs['vert_coord'])

        # Load texture coordinates for filter shader
        texture_vertex_buffer = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, texture_vertex_buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, len(TEXTURE_VERTICES),
                        TEXTURE_VERTICES, gl.GL_STATIC_DRAW)
        gl.glVertexAttribPointer(self.attrib_locs['vert_tex_coord'], 2,
                                 gl.GL_FLOAT, False, 0, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(self.attrib_locs['vert_tex_coord'])

    def render(self, img_dimensions, frame):
        """
        Render the shader output
        """
        gl.glUseProgram(self.shader)
        if self.uniform_locs['rand'] != -1:
            gl.glUniform1f(self.uniform_locs['rand'], random.random())
        if self.uniform_locs['frame'] != -1:
            gl.glUniform1iv(self.uniform_locs['frame'], 1, frame)
        gl.glViewport(0, 0, img_dimensions[0], img_dimensions[1])
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, int(len(FILTER_VERTICES)/2/4))

    def _compile_shader(self, source, type):
        """
        gl.GL_VERTEX_SHADER or gl.GL_FRAGMENT_SHADER
        """
        prog = shaders.compileShader(source, type)
        assert gl.glGetShaderiv(prog, gl.GL_COMPILE_STATUS), (
            "Error: Could not compile shader.\n%s" % (source))
        return prog
