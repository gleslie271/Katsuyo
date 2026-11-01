"""Pick example sentences for the word card in katsuyo.html from the Tatoeba corpus.

Tatoeba's Japanese index (the Tanaka corpus) lists the dictionary words in each sentence, with readings and the
exact spelling used. Each drill word gets up to two short sentences with an English translation: ones the index marks
as checked good examples for the word come first, then short ones whose other words are no harder than the word's
own JLPT level. Every kanji gets furigana from the index's readings and JMdict, and a sentence where that can't be
done is passed over.

Output: examples/00.json … examples/63.json, each mapping "kanji|reading" to [[sentence, English], …]. The page
fetches only the file a word needs (exShard() in katsuyo.html uses the same hash). In a sentence, {漢字|かんじ} is
furigana and [ … ] marks the word itself.

Usage:  python make_examples.py tatoeba-dir jmdict-eng.json
  tatoeba-dir  jpn_indices.csv, jpn_sentences.tsv, eng_sentences.tsv and jpn-eng_links.tsv
               from https://downloads.tatoeba.org/exports/ (CC BY 2.0 FR)
  jmdict-eng   jmdict-eng-*.json from https://github.com/scriptin/jmdict-simplified/releases
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE, OUT = ROOT / 'katsuyo.html', ROOT / 'examples'
SHARDS = 64          # files the examples are split into
PER_WORD = 2         # sentences kept per word
MAX_JP, MAX_EN = 30, 110  # longest sentence and translation, in characters

# One word of an index line: headword(reading or #JMdict id)[sense]{spelling in the sentence}~ (~: a checked good example)
TOKEN = re.compile(r'^(?P<h>[^(\[{~]+)(?:\((?P<r>[^)]*)\))?(?:\[(?P<s>\d+)\])?(?:\{(?P<f>[^}]*)\})?(?P<good>~)?$')
SURU = {'為る', 'する'}
# Sentences with these are skipped: markup characters, and Latin letters (names, brands, romaji)
BAD = re.compile(r'[\[\]{}|<>&"A-Za-zＡ-Ｚａ-ｚ\t]')


def is_kanji(ch):
    return '一' <= ch <= '鿿' or ch in '々ヶ〆'


def has_kanji(s):
    return any(is_kanji(ch) for ch in s)


def shard(key):
    """Which examples file a word is in: a djb2 hash of "kanji|reading", the same as exShard() in the page."""
    h = 5381
    for ch in key:
        h = (h * 33 + ord(ch)) & 0xFFFFFFFF
    return h % SHARDS


CLASS = {'g': 'godan', 'i': 'ichidan', 's': 'suru', 'k': 'kuru', 'a': 'iadj', 'n': 'naadj', 'o': 'noun'}


def page_words():
    """The drill's words as (kanji, reading, JLPT level, class, meaning), from the starter list and JLPT_DATA in katsuyo.html."""
    html = PAGE.read_text(encoding='utf-8')
    starter = html[html.index('const WORDS = ['):html.index('].map(([k, r, m, c, f])')]
    core = json.loads(re.search(r'const CORE_LEVEL = (\{.*?\});', html).group(1))
    words = [(k, r, core.get(k, 5), c, m) for k, r, m, c in re.findall(r"\['([^']*)','([^']*)','([^']*)','(\w+)'", starter)]
    data = html[html.index('const JLPT_DATA = `') + 19:]
    for line in data[:data.index('`')].strip().split('\n'):
        k, r, m, c, lv = line.split('|')[:5]
        words.append((k or r, r, int(lv), CLASS[c], m))
    return words


def load_jmdict(path):
    """Readings by kanji spelling (common ones first), each entry's first reading, and each entry's parts of speech
    and English glosses by JMdict id, with the ids of the entries spelled and read a given way."""
    by_kanji, by_id, entry, by_form = defaultdict(list), {}, {}, defaultdict(list)
    for e in json.loads(Path(path).read_text(encoding='utf-8'))['words']:
        kana = sorted(e['kana'], key=lambda x: not x['common'])
        if kana:
            by_id[e['id']] = kana[0]['text']
        entry[e['id']] = ({p for s in e['sense'] for p in s['partOfSpeech']},
                          {g['text'].lower() for s in e['sense'] for g in s['gloss']})
        for r in kana:
            by_form[r['text'], r['text']].append(e['id'])
        for k in sorted(e['kanji'], key=lambda x: not x['common']):
            for r in kana:
                if '*' in r['appliesToKanji'] or k['text'] in r['appliesToKanji']:
                    by_form[k['text'], r['text']].append(e['id'])
                    if r['text'] not in by_kanji[k['text']]:
                        by_kanji[k['text']].append(r['text'])
    return by_kanji, by_id, entry, by_form


# JMdict parts of speech that fit each drill class
POS_OK = {
    'godan': lambda p: p.startswith('v5'), 'ichidan': lambda p: p.startswith('v1'), 'kuru': lambda p: p == 'vk',
    'suru': lambda p: p.startswith('vs'), 'iadj': lambda p: p.startswith('adj-i'), 'naadj': lambda p: p == 'adj-na',
    'noun': lambda p: p in ('n', 'pn', 'n-t', 'n-adv', 'n-pr'),
}


def same_word(tok, rd, w, jm):
    """Is this token the drill word w, not a homograph? Its JMdict entries must include one of w's part of speech,
    and when the index names the entry outright (カラー "collar" vs カラー "color"), that entry must have w's meaning."""
    _, _, entry, by_form = jm
    ids = [tok['id']] if tok['id'] else by_form.get((tok['h'], rd), [])
    ids = [i for i in ids if i in entry]
    if not ids:
        return True
    fits = [i for i in ids if any(POS_OK[w[3]](p) for p in entry[i][0])]
    if not fits:
        return False
    if tok['id']:
        first = re.sub(r'\s*\(.*?\)', '', re.split(r'[;,]', w[4])[0]).strip().lower()
        first = re.sub(r'^(a|an|the) ', '', first)
        return any(first in entry[i][1] or ('to ' + first) in entry[i][1] for i in fits)
    return True


def parse_line(bline):
    toks = []
    for raw in bline.split(' '):
        m = TOKEN.match(raw)
        if not m:
            return None
        r = m['r'] or ''
        toks.append({'h': m['h'], 'r': '' if r.startswith('#') else r, 'id': r[1:] if r.startswith('#') else '',
                     'sense': m['s'] or '', 'surf': m['f'] or m['h'], 'good': bool(m['good'])})
    return toks


def reading(tok, jm):
    """The token's headword reading: given in the index, from its JMdict id, or JMdict's first (common) reading."""
    by_kanji, by_id = jm[:2]
    if not has_kanji(tok['h']):
        return tok['h']
    if tok['r']:
        return tok['r']
    if tok['id'] and tok['id'] in by_id:
        return by_id[tok['id']]
    rs = by_kanji.get(tok['h'])
    return rs[0] if rs else None


def ruby_segments(surf, head, rd):
    """The spelling in the sentence as [(text, furigana or '')], or None if its kanji can't be given a reading."""
    if not has_kanji(surf):
        return [(surf, '')]
    if rd is None:
        return None
    if head == '来る':                       # 来 reads く, き or こ depending on what follows
        nxt = surf[1:2]
        rt = 'く' if nxt in ('る', 'れ') else 'き' if nxt in ('ま', 'た', 'て', 'ち') else 'こ'
        return [('来', rt), (surf[1:], '')] if surf.startswith('来') else None
    a = 0                                   # kana the headword and reading share at the start (お茶 / おちゃ)
    while a < min(len(head), len(rd)) and head[a] == rd[a] and not is_kanji(head[a]):
        a += 1
    n = 0                                   # and at the end (食べる / たべる)
    while n < min(len(head), len(rd)) - a and head[-1 - n] == rd[-1 - n]:
        n += 1
    base, rt, tail = head[a:len(head) - n], rd[a:len(rd) - n], head[len(head) - n:]
    if not surf.startswith(head[:a] + base) or not base:
        return None
    rest = surf[a + len(base):]
    if len(tail) > 1 and not rest.startswith(tail[:-1]):  # only the last kana may change (食べる → 食べた, not 食わない)
        return None
    if has_kanji(rest):
        return None
    return [(head[:a], ''), (base, rt), (rest, '')]


def markup(jp, toks, jm, target):
    """The sentence with {kanji|reading} furigana and [ ] around the tokens in `target` (indices), or None."""
    spans, pos = [], 0                       # (start, end, segments, token index)
    for i, t in enumerate(toks):
        at = jp.find(t['surf'], pos)
        if at < 0:
            if i in target:
                return None
            continue
        segs = ruby_segments(t['surf'], t['h'], reading(t, jm))
        if segs is None:
            return None
        spans.append((at, at + len(t['surf']), segs, i))
        pos = at + len(t['surf'])
    hit = [s for s in spans if s[3] in target]
    if len(hit) != len(target) or any(a[1] != b[0] for a, b in zip(hit, hit[1:])):  # the word, in one piece
        return None
    out, pos, covered = [], 0, set()
    for a, b, segs, i in spans:
        if a < pos:
            return None
        if i == target[0]:
            out.append(jp[pos:a] + '[')
        else:
            out.append(jp[pos:a])
        for text, rt in segs:
            out.append(f'{{{text}|{rt}}}' if rt else text)
        if i == target[-1]:
            out.append(']')
        covered.update(range(a, b))
        pos = b
    out.append(jp[pos:])
    if any(is_kanji(ch) and k not in covered for k, ch in enumerate(jp)):
        return None                          # a kanji outside the indexed words: no reading for it
    return ''.join(out)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    tdir, jm = Path(sys.argv[1]), load_jmdict(sys.argv[2])
    words = page_words()
    level = {}                               # headword → easiest JLPT level of a drill word spelled that way
    for k, r, lv, *_ in words:
        level[k] = max(level.get(k, 0), lv)

    # How each word shows up in the index: kanji words by headword (reading checked), kana words by reading,
    # 勉強する as 勉強 followed by する
    by_head, by_read, by_suru = defaultdict(list), defaultdict(list), defaultdict(list)
    for w in dict.fromkeys(words):
        k, r = w[:2]
        if k.endswith('する') and len(k) > 2:
            by_suru[k[:-2]].append(w)
        elif has_kanji(k):
            by_head[k].append(w)
        else:
            by_read[r].append(w)

    # Read line by line: a few sentences contain Unicode line separators that splitlines() would break on
    rows = lambda name: (line.rstrip('\n').split('\t') for line in open(tdir / name, encoding='utf-8') if line.strip())
    jp = {sid: text for sid, _, text in rows('jpn_sentences.tsv')}
    links = defaultdict(list)
    for a, b in rows('jpn-eng_links.tsv'):
        links[a].append(b)

    cands = defaultdict(list)                # word → [(score, sentence id, markup, highlighted spelling, English ids)]
    for sid, eid, bline in rows('jpn_indices.csv'):
        text = jp.get(sid)
        if not text or len(text) > MAX_JP or BAD.search(text):
            continue
        toks = parse_line(bline)
        if not toks:
            continue
        eids = ([eid] if eid not in ('0', '-1') else []) + links.get(sid, [])
        if not eids:
            continue
        for i, t in enumerate(toks):
            if t['sense'] not in ('', '01'):
                continue                     # the word in another of its meanings than the one the drill gives
            found = []                       # (word, token indices that spell it)
            for w in by_head.get(t['h'], []):
                if t['r'] and t['r'] != w[1]:
                    continue
                if not t['r'] and t['h'] in jm[0] and w[1] not in jm[0][t['h']][:1 if len(jm[0][t['h']]) > 1 else 9]:
                    continue                 # an unmarked headword means its usual reading
                if has_kanji(t['surf']):
                    found.append((w, [i]))
            rd = reading(t, jm)
            for w in by_read.get(rd, []) if rd else []:
                if not has_kanji(t['surf']):
                    found.append((w, [i]))
            if i + 1 < len(toks) and toks[i + 1]['h'] in SURU:
                for w in by_suru.get(t['h'], []):
                    if (not t['r'] or t['r'] == w[1][:-2]) and has_kanji(t['surf']) == has_kanji(w[0][:-2]):
                        found.append((w, [i, i + 1]))
            for w, target in found:
                if len(target) == 1 and not same_word(t, rd, w, jm):
                    continue
                m = markup(text, toks, jm, target)
                if not m:
                    continue
                wl = w[2]
                harder = sum(max(0, wl - level.get(o['h'], 0)) for j, o in enumerate(toks)
                             if j not in target and has_kanji(o['h']))
                spelled = ''.join(toks[j]['surf'] for j in target)
                katakana = lambda s: any('ァ' <= ch <= 'ヺ' for ch in s)
                score = (-12 if t['good'] else 0) + 2 * min(harder, 8) \
                    + max(0, len(text) - 18) * 1.5 + max(0, 8 - len(text)) * 2 \
                    + (6 if katakana(spelled) != katakana(w[0]) else 0)  # かっこいい written カッコイイ
                cands[w].append((score, int(sid), m, spelled, eids))

    need = {e for cs in cands.values() for c in cs for e in c[4]}
    en = {eid: text for eid, _, text in rows('eng_sentences.tsv') if eid in need and len(text) <= MAX_EN}

    out = defaultdict(dict)
    for w in dict.fromkeys(words):
        picked, spellings, seen = [], set(), set()
        ranked = sorted(cands.get(w, []), key=lambda c: (c[0], c[1]))
        for pass_ in (0, 1):                 # first pass: a different spelling each time (食べる, then 食べた)
            for score, sid, m, spelled, eids in ranked:
                eng = next((en[e] for e in eids if e in en), None)
                # one sentence once, and not two that translate the same (生きていれば / 今生きていれば)
                if len(picked) == PER_WORD or not eng or sid in seen or eng.lower() in seen or (pass_ == 0 and spelled in spellings):
                    continue
                picked.append([m, eng]); spellings.add(spelled); seen.update((sid, eng.lower()))
        if picked:
            key = f'{w[0]}|{w[1]}'
            out[shard(key)][key] = picked

    OUT.mkdir(exist_ok=True)
    for old in OUT.glob('*.json'):
        old.unlink()
    total = 0
    for n in range(SHARDS):
        body = json.dumps(dict(sorted(out[n].items())), ensure_ascii=False, separators=(',', ':'))
        (OUT / f'{n:02}.json').write_text(body + '\n', encoding='utf-8')
        total += len(body.encode())
    have = sum(len(d) for d in out.values())
    unique = len({w[:2] for w in words})
    print(f'{have:,} of {unique:,} words have examples ({have / unique:.0%}); examples/: {total // 1024:,} KB in {SHARDS} files')


if __name__ == '__main__':
    main()
