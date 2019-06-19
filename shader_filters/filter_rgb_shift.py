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


int add_target(int x, int target)
{
    int i = x;
    for(int j=0; j<50; j++) {
        if(i > target + j * texture_size.x) {

            i -= 2;
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

    ivec2 flip = ivec2(-1, 1);

    // flip the coord so its in a direction we are used to
    coord = coord * flip;

    ivec2 r_offset = ivec2(
                            cos(cos(frame/2.0) * 20) * 6.0,
                            0.0
                        );
    ivec2 b_offset = ivec2(
                            -cos(frame/16.0) * 6.0,
                            0.0
                        );


    ivec2 coord_r = coord - r_offset;
    ivec2 coord_b = coord + b_offset;
    vec2 tex_coord_r = sub_pixel + vec2(coord_r) / vec2(texture_size);

    vec2 tex_coord_g = sub_pixel + vec2(coord) / vec2(texture_size);
    vec2 tex_coord_b = sub_pixel + vec2(coord_b) / vec2(texture_size);

    // flip tex_coords to match texture vertices
    tex_coord_r = tex_coord_r * flip;
    tex_coord_g = tex_coord_g * flip;
    tex_coord_b = tex_coord_b * flip;

    // Get texture for each color channel, making sure to flip coord back
    vec4 tex_color_r = texture(tex, tex_coord_r);
    vec4 tex_color_g = texture(tex, tex_coord_g);
    vec4 tex_color_b = texture(tex, tex_coord_b);
    frag_color = vec4(tex_color_r.r, tex_color_g.g, tex_color_b.b, 1.0);
}"""


class RGBShiftFilter(ShaderFilter):
    vert_source = VERT_SOURCE
    frag_source = FRAG_SOURCE
