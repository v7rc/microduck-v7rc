#!/usr/bin/env python3
"""Draw original vector-like robot-duck application artwork; no upstream assets copied."""
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parent/'assets'
ROOT.mkdir(exist_ok=True)
im=Image.new('RGBA',(1024,1024),(0,0,0,0));d=ImageDraw.Draw(im)
d.rounded_rectangle((20,20,1004,1004),radius=220,fill='#102d3b')
d.rounded_rectangle((174,188,811,570),radius=135,fill='#f2f7fa')
d.rounded_rectangle((258,284,721,436),radius=65,fill='#153b4d')
for x in [380,590]:d.ellipse((x-32,323,x+32,387),fill='#70e2bc')
d.rounded_rectangle((625,446,875,548),radius=45,fill='#ffae48')
d.rounded_rectangle((364,575,661,765),radius=56,fill='#b7ced7')
d.rounded_rectangle((268,745,483,854),radius=36,fill='#ffae48')
d.rounded_rectangle((542,745,757,854),radius=36,fill='#ffae48')
d.line((512,575,512,710),fill='#153b4d',width=22)
d.ellipse((478,630,546,698),fill='#258d79')
im.save(ROOT/'app-icon.png')
im.resize((256,256),Image.Resampling.LANCZOS).save(ROOT/'app-icon-preview.png')
im.save(ROOT/'app-icon.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
iconset=ROOT/'AppIcon.iconset';iconset.mkdir(exist_ok=True)
for size in [16,32,128,256,512]:
 im.resize((size,size),Image.Resampling.LANCZOS).save(iconset/f'icon_{size}x{size}.png')
 im.resize((size*2,size*2),Image.Resampling.LANCZOS).save(iconset/f'icon_{size}x{size}@2x.png')
print(ROOT)
