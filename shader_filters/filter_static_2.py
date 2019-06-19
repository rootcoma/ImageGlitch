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
    co = co + rand;
    return fract(
        sin(
            dot(co.xy, vec2(12.9898, 78.233))
        ) * 43758.5453);
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

    vec2 new_tex_coord = sub_pixel + vec2(coord) / vec2(texture_size);

    vec4 tex_color = texture(tex, new_tex_coord);

    float r = f_rand(vec2(coord.x / int(100 * cos(cos(coord.y/3.0))),
        cos(coord.y / 5))) * 10.0;
    if(r > 9.3)
    {
        float c = f_rand(vec2(coord.x, coord.y) + vec2(rand, rand));
        if(c > 0.3 && c < 0.8)
            tex_color = (tex_color / 4.0) + (vec4(c,c,c, 1.0) * 3.0 / 4.0);
    }

    frag_color = tex_color;
}"""


class StaticFilter2(ShaderFilter):
    frag_source = FRAG_SOURCE
    vert_source = VERT_SOURCE
