"""Build index.html, a standalone copy of Katsuyō for static hosting such as GitHub Pages.

katsuyo.html loads its fonts from Google Fonts. This build embeds them in the page instead, cut down to the
characters the page can show: every character in the source, all kana, and ASCII for typed romaji. The result
is one self-contained file with no outside requests.

Usage:  python build.py
Needs:  pip install fonttools brotli
"""
import base64
import io
import re
from pathlib import Path
from urllib.parse import quote

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
SRC, OUT, FONTS = ROOT / 'katsuyo.html', ROOT / 'index.html', ROOT / 'fonts'

# (CSS family, weight, source file) for every weight the page's CSS asks for
FACES = [
    ('Shippori Mincho', 400, 'ShipporiMincho-Regular.ttf'),
    ('Shippori Mincho', 600, 'ShipporiMincho-SemiBold.ttf'),
    ('Shippori Mincho', 800, 'ShipporiMincho-ExtraBold.ttf'),
    ('Yuji Syuku', 400, 'YujiSyuku-Regular.ttf'),
    ('Zen Kaku Gothic New', 400, 'ZenKakuGothicNew-Regular.ttf'),
    ('Zen Kaku Gothic New', 500, 'ZenKakuGothicNew-Medium.ttf'),
    ('Zen Kaku Gothic New', 700, 'ZenKakuGothicNew-Bold.ttf'),
]

DESCRIPTION = 'Drill Japanese verb and adjective conjugations with hints, spaced review and a cheat sheet.'
# The red 活用 seal from the page header, as the tab icon
FAVICON = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
           "<rect x='4' y='4' width='56' height='56' rx='10' fill='#D0382A' transform='rotate(-4 32 32)'/>"
           "<text x='32' y='45' font-size='34' text-anchor='middle' fill='#fff' font-family='sans-serif'>活</text></svg>")


def charset(text):
    """Every character the page could display: its own text, all kana, and ASCII."""
    chars = set(text)
    chars |= {chr(c) for c in range(0x20, 0x7F)}      # ASCII, including romaji left in the answer box
    chars |= {chr(c) for c in range(0x3041, 0x3097)}  # hiragana
    chars |= {chr(c) for c in range(0x30A1, 0x30FB)}  # katakana
    chars |= set('ー〜・、。「」『』（）！？…“”‘’–—→　')
    return ''.join(sorted(c for c in chars if c >= ' '))


def subset_woff2(path, text):
    """The font cut down to `text`, as woff2 bytes."""
    font = TTFont(path)
    opts = subset.Options()
    opts.flavor = 'woff2'  # the default layout features (vertical forms included) keep this small; '*' triples a font's size
    opts.name_IDs = ['*']
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = 'woff2'
    font.save(buf)
    return buf.getvalue()


def main():
    html = SRC.read_text(encoding='utf-8')
    text = charset(html)

    faces = []
    for family, weight, file in FACES:
        data = subset_woff2(FONTS / file, text)
        print(f'{file}: {(FONTS / file).stat().st_size // 1024:,} KB -> {len(data) // 1024:,} KB')
        faces.append(f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: normal; "
                     f"font-display: swap; src: url(data:font/woff2;base64,{base64.b64encode(data).decode()}) format('woff2'); }}")

    # Swap the Google Fonts links for the embedded faces, and drop the artifact viewer's meta tag
    html = re.sub(r'<link rel="(?:preconnect|stylesheet)" href="https://fonts\.g[^"]*"[^>]*>\n', '', html)
    html = re.sub(r'<meta name="claude:[^>]*>\n', '', html)
    font_css = ('<style>\n/* Shippori Mincho, Yuji Syuku and Zen Kaku Gothic New, SIL Open Font License 1.1 (see the OFL files), '
                'subset to the characters this page uses */\n' + '\n'.join(faces) + '\n')
    html = html.replace('<style>\n', font_css, 1)

    # The artifact viewer adds the document skeleton; a standalone page needs its own
    head, sep, body = html.partition('</style>')
    out = (f'<!doctype html>\n<html lang="en">\n<head>\n{head}{sep}\n'
           f'<meta name="description" content="{DESCRIPTION}">\n'
           f'<link rel="icon" href="data:image/svg+xml,{quote(FAVICON)}">\n'
           f'</head>\n<body>\n{body.lstrip()}</body>\n</html>\n')
    OUT.write_text(out, encoding='utf-8')

    outside = re.findall(r'(?:src|href)="(https?://[^"]+)"', out)
    print(f'index.html: {len(out.encode()) // 1024:,} KB, {len(text):,} characters kept'
          + (f', still loads: {outside}' if outside else ', no outside requests'))


if __name__ == '__main__':
    main()
