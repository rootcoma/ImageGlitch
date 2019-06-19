from shader_filter import ShaderFilter

VERT_SOURCE = """
#version 330

in vec2 vert_coord;
in vec2 vert_tex_coord;
out vec2 frag_tex_coord;

void main()
{
  frag_tex_coord = vert_tex_coord;
  gl_Position = vec4(vert_coord, 0.0, 1.0);
}"""

FRAG_SOURCE = """
#version 330
uniform sampler2D tex;
in vec2 frag_tex_coord;
out vec4 frag_color;

ivec2 texture_size;


int add_target(int x, int target, int height)
{
    int i = x;
    for(int j=0; j<height; j++) {
        if(i > target + j * texture_size.x) {
            i -= 3;
        }
    }
    return i;
}


void main()
{
    texture_size = textureSize(tex, 0);

    vec2 sub_pixel = vec2(1.0/texture_size.x/1000,
                          1.0/texture_size.y/1000);

    ivec2 coord = ivec2(frag_tex_coord.x * texture_size.x,
                        frag_tex_coord.y * texture_size.y);

    int y_end = texture_size.y / 6;

    if(coord.y < y_end) {
        coord.y = y_end;
    }

    vec2 new_tex_coord = vec2(coord) / vec2(texture_size) + sub_pixel;

    vec4 tex_color = texture(tex, new_tex_coord);

    frag_color = tex_color;
}"""


class RepeatEndFilter(ShaderFilter):
    frag_source = FRAG_SOURCE
    vert_source = VERT_SOURCE
