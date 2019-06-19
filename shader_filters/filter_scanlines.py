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

vec4 mix_colors(vec4 c1, vec4 c2) {
    vec4 c = vec4(vec3(c1.rgb*c1.a + c2.rgb*c2.a), c1.a + c2.a);
    return c;
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
    int y_offset = 0;
    int color_height = 7;
    int color_width = 4;
    int cell_height = color_height;
    int cell_width = color_width * 3;

    if((coord.x/cell_width) % 2 == 0) {
        coord.y += cell_height/2;
        coord_f.y += float(cell_height/2);
    }

    ivec2 tmp_coord = ivec2(coord.x - coord.x % (cell_width),
                            coord.y - coord.y % color_height);

    vec2 new_tex_coord = sub_pixel + vec2(tmp_coord) / vec2(texture_size);

    vec4 tex_color = texture(tex, new_tex_coord);

    if(coord.x % cell_width >= 0 &&
       coord.x % cell_width < 0 + color_width)
        tex_color *= vec4(1.0, 0.0, 0.0, 1.0);
    int tmp = color_width;
    if(coord.x % cell_width >= tmp &&
       coord.x % cell_width < tmp + color_width)
        tex_color *= vec4(0.0, 1.0, 0.0, 1.0);
    tmp += color_width;
    if(coord.x % cell_width >= tmp &&
       coord.x % cell_width < tmp + color_width)
        tex_color *= vec4(0.0, 0.0, 1.0, 1.0);

    float x = mod(coord_f.x, float(color_width));
    float y = mod(coord_f.y, float(color_height));

    if(x > float(color_width) - 0.7 || y > float(color_height) - 0.7) {
        tex_color *= 0.5;
        tex_color.a = 1.0;
    } else {
        tex_color *= 1.1;
        tex_color = clamp(tex_color, 0.0, 1.0);
    }
    
    frag_color = tex_color;
}"""


class ScanlineFilter(ShaderFilter):
    frag_source = FRAG_SOURCE
    vert_source = VERT_SOURCE
