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

uniform float rand;
uniform int frame;

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

    vec2 coord_f = vec2(frag_tex_coord.x * float(texture_size.x),
                        frag_tex_coord.y * float(texture_size.y));

    int i = coord.x + (texture_size.y - coord.y) * texture_size.x;

    i = add_target(i,
            texture_size.y / 7 *
            texture_size.x - texture_size.x * 20 +
            int(cos(float(frame * cos(float(frame)/3.9))/20.0) * 10.0) *
            texture_size.x, 20);
    if(rand < 0.1)
        i = add_target(i,
                texture_size.y / 3 * texture_size.x - texture_size.x * 20 +
                int(sin(float(frame)/30.0) *20.0) * texture_size.x, 15);

    vec2 new_tex_coord = sub_pixel +
            vec2(float(i % texture_size.x) / texture_size.x,
                 1.0 - float(i / texture_size.x) / texture_size.y);

    vec4 tex_color = texture(tex, new_tex_coord);

    frag_color = tex_color;
}"""


class FirstFilter(ShaderFilter):
    frag_source = FRAG_SOURCE
    vert_source = VERT_SOURCE
