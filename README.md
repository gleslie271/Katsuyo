# Katsuyō 活用

A Japanese verb and adjective conjugation drill: type answers in romaji or kana, get hints when you miss, and review each rule on a spaced schedule. Practice a hand-picked starter set or the JLPT N5–N1 vocabulary, about 7,500 words in all.

**Live site:** https://gleslie271.github.io/Katsuyo/

Progress, scores and settings are saved in your own browser.

## Files

| File | What it is |
| --- | --- |
| `index.html` | The website, with the fonts for everything but the JLPT words' extra kanji built in. |
| `webfonts/` | Those extra kanji, split into small font files the page loads only when a word needs them. |
| `katsuyo.html` | The source page. |
| `build.py` | Turns `katsuyo.html` into `index.html` and `webfonts/`, cutting the fonts down to the characters the page uses. |
| `make_jlpt.py` | Builds the JLPT word list inside `katsuyo.html` from the JLPT vocabulary lists and JMdict. |
| `fonts/` | The font licenses. |

## Credits

Meanings and word types for the JLPT words come from [JMdict](https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project), © the Electronic Dictionary Research and Development Group, used under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

Fonts: Shippori Mincho (FONTDASU), Yuji Syuku (Kinuta Font Factory) and Zen Kaku Gothic New (Yoshimichi Ohira), all under the SIL Open Font License 1.1. See the `OFL-*.txt` files in `fonts/`.
