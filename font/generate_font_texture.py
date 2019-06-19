#!/bin/python
from PIL import Image, ImageDraw, ImageFont

CHARS = [chr(i) for i in range(256)]

fnt = ImageFont.truetype('RobotoMono-Bold.ttf', 16)
img = Image.new("RGBA", (10*16, 20*16), color=(0, 0, 0, 0))
d = ImageDraw.Draw(img)
for i in range(len(CHARS)):
    d.text((i % 16 * 10, int(i/16) * 20),
           CHARS[i], font=fnt, fill=(255, 255, 255, 255))
img.save('font_tex.png', compress_level=0)
