"""Build index.html, a standalone copy of Katsuyō for static hosting such as GitHub Pages.

katsuyo.html loads its fonts from Google Fonts. This build hosts them with the page instead, cut down to the
characters the page can show. Everything the page shows by itself (its own text, the starter words, all kana and
ASCII for typed romaji) is embedded in index.html, so it opens with no outside requests. The extra kanji of the JLPT
words are split into small font files in webfonts/, each declared with a unicode-range, so the browser downloads one
only when a word on screen needs it.

Usage:  python build.py
Needs:  pip install fonttools brotli
"""
import base64
import io
import json
import re
from pathlib import Path
from urllib.parse import quote

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
SRC, OUT, FONTS, WEBFONTS = ROOT / 'katsuyo.html', ROOT / 'index.html', ROOT / 'fonts', ROOT / 'webfonts'
EXAMPLES = ROOT / 'examples'
JLPT_START, JLPT_END = '// ---------- JLPT words (generated', '// ---------- end of JLPT words ----------'
SLICE = 100  # kanji per downloadable font file

# (CSS family, weight, source file, shows JLPT words, shows example sentences) for every weight the page's CSS asks
# for. Only the brush font (the big word) and the regular mincho (answers, hints, rules, sentences) show JLPT words
# and example sentences, or the regular gothic in their place when the Japanese font setting is Clean; the rest show
# fixed text.
FACES = [
    ('Shippori Mincho', 400, 'ShipporiMincho-Regular.ttf', True, True),
    ('Shippori Mincho', 600, 'ShipporiMincho-SemiBold.ttf', False, False),
    ('Shippori Mincho', 800, 'ShipporiMincho-ExtraBold.ttf', False, False),
    ('Yuji Syuku', 400, 'YujiSyuku-Regular.ttf', True, False),
    ('Zen Kaku Gothic New', 400, 'ZenKakuGothicNew-Regular.ttf', True, True),
    ('Zen Kaku Gothic New', 500, 'ZenKakuGothicNew-Medium.ttf', False, False),
    ('Zen Kaku Gothic New', 700, 'ZenKakuGothicNew-Bold.ttf', False, False),
]

DESCRIPTION = 'Drill Japanese verb and adjective conjugations with hints, spaced review and a cheat sheet.'
# The red 活用 seal from the page header, as the tab icon
FAVICON = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
           "<rect x='4' y='4' width='56' height='56' rx='10' fill='#D0382A' transform='rotate(-4 32 32)'/>"
           "<text x='32' y='45' font-size='34' text-anchor='middle' fill='#fff' font-family='sans-serif'>活</text></svg>")


def charset(text):
    """Every character the page shows without the JLPT words: its own text, all kana, and ASCII."""
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


def unicode_range(chars):
    """A CSS unicode-range for these characters, with runs of neighbours merged: U+3041-3096,U+4E00"""
    cps, parts = sorted({ord(c) for c in chars}), []
    for cp in cps:
        if parts and parts[-1][1] == cp - 1:
            parts[-1][1] = cp
        else:
            parts.append([cp, cp])
    return ','.join(f'U+{a:X}' if a == b else f'U+{a:X}-{b:X}' for a, b in parts)


def face(family, weight, src, chars=None):
    rng = f' unicode-range: {unicode_range(chars)};' if chars else ''
    return (f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: normal; font-display: swap; "
            f"src: {src} format('woff2');{rng} }}")


def main():
    html = SRC.read_text(encoding='utf-8')
    a, b = html.index(JLPT_START), html.index(JLPT_END)
    base = charset(html[:a] + html[b:])
    # The JLPT words' extra characters, in the order the words appear (N5 first), so each slice tends to cover one level
    extra = ''.join(dict.fromkeys(c for c in html[a:b] if c not in base and c >= ' '))
    slices = [extra[i:i + SLICE] for i in range(0, len(extra), SLICE)]
    # The example sentences' characters beyond those (furigana and markup aside), in their own slices after the words'
    said = ''.join(re.sub(r'\|[^}]*\}|[{}\[\]]', '', jp) for f in sorted(EXAMPLES.glob('*.json'))
                   for ex in json.loads(f.read_text(encoding='utf-8')).values() for jp, _en in ex)
    more = ''.join(dict.fromkeys(c for c in said if c not in base and c not in extra and c >= ' '))
    ex_slices = [more[i:i + SLICE] for i in range(0, len(more), SLICE)]

    WEBFONTS.mkdir(exist_ok=True)
    for old in WEBFONTS.glob('*.woff2'):
        old.unlink()
    faces, sliced = [], 0
    for family, weight, file, vocab, sentences in FACES:
        data = subset_woff2(FONTS / file, base)
        print(f'{file}: {(FONTS / file).stat().st_size // 1024:,} KB -> {len(data) // 1024:,} KB embedded')
        url = f"url(data:font/woff2;base64,{base64.b64encode(data).decode()})"
        faces.append(face(family, weight, url, base if vocab else None))
        if vocab:
            slug = f"{family.lower().replace(' ', '-')}-{weight}"
            for i, chars in enumerate(slices + (ex_slices if sentences else [])):
                part = subset_woff2(FONTS / file, chars)
                (WEBFONTS / f'{slug}-{i:02}.woff2').write_bytes(part)
                faces.append(face(family, weight, f"url(webfonts/{slug}-{i:02}.woff2)", chars))
                sliced += len(part)

    # Swap the Google Fonts links for these faces, and drop the artifact viewer's meta tag
    html = re.sub(r'<link rel="(?:preconnect|stylesheet)" href="https://fonts\.g[^"]*"[^>]*>\n', '', html)
    html = re.sub(r'<meta name="claude:[^>]*>\n', '', html)
    font_css = ('<style>\n/* Shippori Mincho, Yuji Syuku and Zen Kaku Gothic New, SIL Open Font License 1.1 (see the OFL files), '
                'subset to the characters this page uses; the JLPT words\' extra kanji load from webfonts/ as needed */\n'
                + '\n'.join(faces) + '\n')
    html = html.replace('<style>\n', font_css, 1)

    # The artifact viewer adds the document skeleton; a standalone page needs its own
    head, sep, body = html.partition('</style>')
    out = (f'<!doctype html>\n<html lang="en">\n<head>\n{head}{sep}\n'
           f'<meta name="description" content="{DESCRIPTION}">\n'
           f'<link rel="icon" href="data:image/svg+xml,{quote(FAVICON)}">\n'
           f'</head>\n<body>\n{body.lstrip()}</body>\n</html>\n')
    OUT.write_text(out, encoding='utf-8')

    outside = re.findall(r'<(?:link|script|img)\b[^>]*\b(?:src|href)="(https?://[^"]+)"', out)  # loads, not ordinary links
    print(f'webfonts/: {len(slices)} slices x 3 fonts + {len(ex_slices)} x 2 for the example sentences, {sliced // 1024:,} KB, loaded only as needed')
    print(f'index.html: {len(out.encode()) // 1024:,} KB, {len(base):,} characters embedded, {len(extra) + len(more):,} in slices'
          + (f', still loads: {outside}' if outside else ', no outside requests'))


if __name__ == '__main__':
    main()
