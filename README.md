# Katsuyō 活用

A Japanese verb and adjective conjugation drill: type answers in romaji or kana, get hints when you miss, and review each rule on a spaced schedule.

**Live site:** https://gleslie271.github.io/Katsuyo/

## Files

| File | What it is |
| --- | --- |
| `index.html` | The website. One self-contained file with the fonts built in. |
| `katsuyo.html` | The source page. Edit this, then rebuild. |
| `build.py` | Turns `katsuyo.html` into `index.html`, embedding the fonts cut down to the characters the page uses. |
| `fonts/` | The font licenses. The build also needs the full `.ttf` files here; they're left out of the repository (about 40 MB) and come from Google Fonts. |

## Rebuild after editing

```
pip install fonttools brotli
python build.py
```

## Update the live site

Rebuild, then commit and push. GitHub Pages republishes within a minute or two.

```
python build.py
git add -A
git commit -m "Describe the change"
git push
```

## Put it on GitHub Pages

1. Create a repository on GitHub, for example `katsuyo`.
2. Upload `index.html` and the three `fonts/OFL-*.txt` files (the font licenses ask to travel with the fonts). Uploading the whole folder works too.
3. In the repository, open **Settings → Pages**, set **Source** to *Deploy from a branch*, pick `main` and `/ (root)`, and save.
4. After a minute the site is live at `https://<your-username>.github.io/katsuyo/`.

Progress, scores and settings are saved in each visitor's browser, so nothing else needs hosting.

## Fonts

Shippori Mincho (FONTDASU), Yuji Syuku (Kinuta Font Factory) and Zen Kaku Gothic New (Yoshimichi Ohira), all under the SIL Open Font License 1.1. See the `OFL-*.txt` files in `fonts/`.
