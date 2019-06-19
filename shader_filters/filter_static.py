from shader_filter import ShaderFilter

VERT_SOURCE = """
#version 330

uniform float rand;
uniform int frame;
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

float f_rand(vec2 co) {
    co = co + vec2(rand);
    return fract(
        sin(
            dot(co.xy, vec2(12.9898, 78.233))
        ) * 43758.5453);
}

void main()
{
    texture_size = textureSize(tex, 0);

    vec2 sub_pixel = vec2(1.0/texture_size.x/1000.0,
                          1.0/texture_size.y/1000.0);

    ivec2 coord = ivec2(frag_tex_coord.x * texture_size.x,
                        frag_tex_coord.y * texture_size.y);

    vec2 coord_f = vec2(frag_tex_coord.x * float(texture_size.x),
                        frag_tex_coord.y * float(texture_size.y));

    if(int(f_rand(ivec2(vec2(coord) / vec2(120, 3))) * 80) == 4) {

        frag_color = vec4(1.0, 1.0, 1.0, 1.0) *
        vec4(
            f_rand(ivec2(vec2(3.14,3.14)+vec2(coord) / vec2(120, 3))),
            f_rand(ivec2(vec2(3.14,3.14)+vec2(coord) / vec2(120,3))),
            f_rand(ivec2(vec2(3.14,3.14)+vec2(coord) / vec2(120,3))), 1.0);
        return;
    }
    vec2 new_tex_coord = sub_pixel + vec2(coord) / vec2(texture_size);


    vec4 tex_color = texture(tex, new_tex_coord);

    frag_color = tex_color;
}"""


class StaticFilter(ShaderFilter):
    frag_source = FRAG_SOURCE
    vert_source = VERT_SOURCE
