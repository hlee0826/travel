"""Render a name once; all previews and downloads derive from that same master."""
import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT = Path(__file__).resolve().parent / 'fonts' / 'NotoSerifKR.ttf'


def artwork_files(raw, name):
    with Image.open(io.BytesIO(raw)) as source:
        master = source.convert('RGB')
    w, h = master.size
    if name:
        draw = ImageDraw.Draw(master)
        size = max(10, round(w * .035))
        font = ImageFont.truetype(str(FONT), size)
        while draw.textlength(name, font=font) > w * .7 and size > 8:
            size -= 1
            font = ImageFont.truetype(str(FONT), size)
        box = draw.textbbox((0, 0), name, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        x, y, pad = w * .92 - tw, h * .055, w * .02
        draw.rectangle((x-pad, y-pad/2, x+tw+pad, y+th+pad/2), fill='#faf5e7')
        draw.text((x-box[0], y-box[1]), name, font=font, fill='#302c25')
    files = {}
    for fmt in ('PNG', 'JPEG'):
        out = io.BytesIO()
        master.save(out, fmt, **({'quality': 95, 'subsampling': 0} if fmt == 'JPEG' else {}))
        files['master.' + ('jpg' if fmt == 'JPEG' else 'png')] = out.getvalue()
    preview = master.copy()
    preview.thumbnail((800, 1000))
    draw = ImageDraw.Draw(preview)
    pw, ph = preview.size
    font = ImageFont.truetype(str(FONT), max(10, round(pw * .018)))
    # Preview mark is baked into delivered pixels, not a removable browser overlay.
    draw.rectangle((0, ph-pw*.055, pw, ph), fill='#faf5e7')
    draw.text((pw/2, ph-pw*.028), 'MINHWA STUDIO · PREVIEW', font=font, fill='#302c25', anchor='mm')
    out = io.BytesIO()
    preview.save(out, 'PNG')
    files['preview.png'] = out.getvalue()
    return files


def matted_print(raw, size='12x16'):
    """Center the approved painting on the selected paper without cropping."""
    ratios = {'5x7': 7 / 5, '12x16': 4 / 3}
    if size not in ratios:
        raise ValueError('Choose an available print size.')
    with Image.open(io.BytesIO(raw)) as source:
        im = source.convert('RGB')
    w, h = im.size
    if w * 5 != h * 4:
        raise ValueError('Matting requires a 4:5 approved painting.')
    paper = Image.new('RGB', (w, round(w * ratios[size])), '#faf5e7')
    paper.paste(im, (0, (paper.height-h)//2))
    out = io.BytesIO()
    paper.save(out, 'PNG')
    return out.getvalue()
