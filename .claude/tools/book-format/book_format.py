#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
book_format.py — 書籍原稿(Markdown)を「飾り付き原稿」へ変換する（/book-format から呼ばれる）

出力形式: markdown（装飾Markdown） / html（HTML+CSS） / pdf（HTMLをChrome/Edgeで印刷）
用紙サイズ: A4 / A5

使い方:
    python book_format.py --project projects/my-book --format all --size A5
    python book_format.py --project projects/my-book --format pdf --size A4 --chapters 1,3

依存: pip install markdown pygments  ／ PDF出力には Chrome か Edge が必要
"""
from __future__ import annotations

import argparse
import datetime
import html as htmllib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windowsのcp932コンソールでも絵文字を出せるように
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import markdown as mdlib
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import TextLexer, get_lexer_by_name
    from pygments.util import ClassNotFound
except ImportError:
    print("ERROR: 必要なライブラリが見つかりません。次のコマンドで導入してください:\n"
          "    python -m pip install markdown pygments", file=sys.stderr)
    sys.exit(3)

TOOL_DIR = Path(__file__).resolve().parent
CSS_TEMPLATE = TOOL_DIR / "book.css"
OUT_DIRNAME = "07_publish"

# 用紙ごとの組版設定（mm / pt）。縦置き前提。inner=綴じ側（ノド）の余白、outer=小口側の余白
# 余白はヘッダー・ページ番号を収める帯を兼ねる。家庭用プリンターの印字不可領域（約5mm）や
# 綴じ代を考慮し、上下左右とも15mm以上を確保する。
PAPERS = {
    "A4": dict(w=210, h=297, top=24, bottom=26, inner=26, outer=21, font=10.5, lh=1.85, code=8.4),
    "A5": dict(w=148, h=210, top=19, bottom=21, inner=19, outer=15, font=9.5, lh=1.85, code=7.6),
}

# 引用ブロックの先頭ラベル → 囲み記事の種別。種別は CSS の .callout-<種別> に対応する（6種類に絞る）
#   point=要点 / tip=ヒント / note=補足 / warning=注意 / danger=警告 / column=コラム
# 原稿にラベルが無い引用は、内容から推測せず通常の引用のまま表示する（原稿にない意味づけを足さない）
CALLOUT_KEYS = [
    ("ポイント", "point"), ("POINT", "point"), ("重要", "point"), ("IMPORTANT", "point"), ("要点", "point"),
    ("ヒント", "tip"), ("TIPS", "tip"), ("TIP", "tip"), ("コツ", "tip"),
    ("補足", "note"), ("メモ", "note"), ("NOTE", "note"), ("INFO", "note"), ("参考", "note"),
    ("用語", "note"), ("具体例", "note"), ("例", "note"), ("注", "note"),
    ("注意点", "warning"), ("注意", "warning"), ("WARNING", "warning"), ("CAUTION", "warning"),
    ("よくある誤解", "warning"),
    ("警告", "danger"), ("危険", "danger"), ("DANGER", "danger"),
    ("コラム", "column"), ("COLUMN", "column"), ("豆知識", "column"), ("余談", "column"),
    ("STEP", "step"), ("ステップ", "step"),   # `> **STEP 1**: 手順の見出し` → ステップカード
]
CALLOUT_KEYS.sort(key=lambda k: -len(k[0]))
GH_ALERTS = {"NOTE": ("補足", "note"), "TIP": ("ヒント", "tip"), "IMPORTANT": ("重要", "point"),
             "WARNING": ("注意", "warning"), "CAUTION": ("警告", "danger")}
DIALOGUE_RE = re.compile(r"^\[!(DIALOGUE|会話)\]\s*$", re.I)   # `> [!DIALOGUE]` → 会話ボックス
SPEAKER_RE = re.compile(r"^\*\*(?P<name>[^*]{1,12})\*\*\s*[:：]\s*(?P<text>.*)$")

GOALS_RE = re.compile(r"^(この章で学ぶこと|本章で学ぶこと|この章のゴール|学習目標)")
OVERVIEW_RE = re.compile(r"^(この章の概要|本章の概要)")
SUMMARY_RE = re.compile(r"^(本章のまとめ|この章のまとめ|章のまとめ|まとめ)")
COLUMN_RE = re.compile(r"^(コラム|Column|COLUMN)")

# 章ファイルの章見出し（# 第N章: …）の直後に書ける、章扉用のキーワード行（本文には出さない）
#   # TAGS: LLM, トークン, ツール     → 章扉のキーワードタグ（#LLM #トークン …）
#   # EN-TITLE: INTRODUCTION          → 章扉の英字ラベル（CHAPTER 01 · INTRODUCTION）
CHAPTER_DIRECTIVE_RE = re.compile(r"^#[ \t]*(TAGS|EN-TITLE)(?:[ \t]*[:：][ \t]*|[ \t]+)(.*?)[ \t]*$", re.I | re.M)
# book/book_info.md に書く書誌情報のキーワード（# TITLE: … の形。TITLE/DESCRIPTION/FEATURE は複数行可）
BOOK_INFO_KEYS = ("TITLE", "SUBTITLE", "SERIES", "DESCRIPTION", "FEATURE", "AUTHOR", "PUBLISHER", "DATE", "HEADER")
BOOK_INFO_RE = re.compile(r"^#[ \t]*(" + "|".join(BOOK_INFO_KEYS) + r")(?:[ \t]*[:：][ \t]*|[ \t]+)(.*?)[ \t]*$", re.I)
MAX_SENTENCES = 6  # style-guide.md「1段落: 4〜6文」を超える段落は文の切れ目で分ける

LANG_NAMES = {
    "python": "Python", "py": "Python", "bash": "Bash", "sh": "Shell", "shell": "Shell", "zsh": "Shell",
    "powershell": "PowerShell", "ps1": "PowerShell", "javascript": "JavaScript", "js": "JavaScript",
    "typescript": "TypeScript", "ts": "TypeScript", "json": "JSON", "yaml": "YAML", "yml": "YAML",
    "html": "HTML", "css": "CSS", "markdown": "Markdown", "md": "Markdown", "sql": "SQL", "toml": "TOML",
    "xml": "XML", "dockerfile": "Dockerfile", "java": "Java", "go": "Go", "rust": "Rust",
    "csharp": "C#", "cpp": "C++", "c": "C", "text": "", "txt": "", "plaintext": "",
}

FILENAME_RE = re.compile(
    r"^\s*(?:#|//|--|;|/\*|<!--|REM\b)\s*(?:(?:ファイル名|filename|file)\s*[:：]\s*)?"
    r"((?:[\w\-]+[/\\])*(?:\.[\w\-]+|[\w\-]+(?:\.[\w\-]+)*\.[A-Za-z][\w\-]*))\s*(?:\*/|-->)?\s*$",
    re.I)
FENCE_OPEN_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
FENCE_CLOSE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")
MARKER_NEW_RE = re.compile(
    r"^\s*\[FIG_(\d+)_(\d+)｜([^｜\]]*)｜([^｜\]]*)｜([^｜\]]*)(?:｜([^\]]*))?\]\s*$")
MARKER_OLD_RE = re.compile(r"^\s*\[図(\d+)\.(\d+)\s*[:：]\s*([^|\]]*?)\s*(?:\|(.*))?\]\s*$")
LIST_RE = re.compile(r"^ {0,3}(?:[-*+]|\d+\.)\s+\S")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)*\|?\s*$")
IMG_MD_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)((?:\s+\"[^\"]*\")?)\)")
CJK = "\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef"
CJK_JOIN_RE = re.compile(
    rf"(?:(?<=[{CJK}])|(?<=</strong>)|(?<=</em>)|(?<=</a>)|(?<=</code>))\n"
    rf"(?=[{CJK}]|<(?:strong|em|a|code)[\s>])")


# ============================================================ データ構造

@dataclass
class Figure:
    num: str                      # "2.3"
    title: str = ""
    kind: str = ""
    summary: str = ""             # マーカーの「内容の要点」（入稿待ちの枠に表示して捨てない）
    svg: str | None = None        # インライン展開するSVG
    img: Path | None = None       # ラスター画像ファイル
    missing: bool = False         # 入稿待ち

    @property
    def label(self) -> str:
        return f"図{self.num}"

    @property
    def dom_id(self) -> str:
        return "fig-" + self.num.replace(".", "-")

    @property
    def file_stem(self) -> str:
        return "fig_" + self.num.replace(".", "_")


@dataclass
class Seg:
    kind: str                     # md / code / figure / callout / quote
    text: str = ""
    lang: str = ""
    code: str = ""
    indent: str = ""
    fig: Figure | None = None
    ckind: str = ""               # callout: point / tip / note / warning / danger / column / step / dialogue
    label: str = ""
    title: str = ""               # callout の見出し（`**POINT: 見出し**` / `**STEP 1**: 見出し`）
    body: list["Seg"] = field(default_factory=list)


@dataclass
class Chapter:
    num: int
    src: Path
    h1_raw: str
    label: str                    # 原稿どおりの「第3章」（番号のない章は空）
    title: str
    segs: list[Seg]
    raw: str = ""                 # 原稿の全文（内容チェック用。キーワード行は除く）
    toc: list[dict] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)   # # TAGS:
    en_title: str = ""                              # # EN-TITLE:

    @property
    def dom_id(self) -> str:
        return f"ch-{self.num}"


@dataclass
class Meta:
    title: str
    subtitle: str
    author: str
    date: str
    title_lines: list[str] = field(default_factory=list)   # 表紙の書名（改行位置・**強調**つき）
    series: str = ""
    description: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    publisher: str = ""
    header: str = ""                                        # 柱（ヘッダー）に出す書名
    subtitle_lines: list[str] = field(default_factory=list)  # 表紙のサブタイトル（行ごとに改行）
    author_lines: list[str] = field(default_factory=list)    # 表紙の著者欄（行ごとに改行）

    @property
    def running(self) -> str:
        return self.header or self.title

    @property
    def cover_subtitle_lines(self) -> list[str]:
        return self.subtitle_lines or ([self.subtitle] if self.subtitle else [])

    @property
    def cover_author_lines(self) -> list[str]:
        return self.author_lines or ([self.author] if self.author else [])


class Ctx:
    def __init__(self, book_dir: Path, src_dir: Path, size: str):
        self.book_dir, self.src_dir, self.size = book_dir, src_dir, size
        self.warnings: list[str] = []
        self.notes: dict[str, int] = {}   # 「整理した内容」の件数（レポートに出す）
        self.missing: dict[str, list[str]] = {}   # 内容チェックで出力に見つからなかった原稿の行（"形式: 章" → 行）

    def warn(self, msg: str) -> None:
        if msg not in self.warnings:
            self.warnings.append(msg)

    def note(self, what: str, n: int = 1) -> None:
        self.notes[what] = self.notes.get(what, 0) + n


# ============================================================ 小さなユーティリティ

def esc(s: str) -> str:
    return htmllib.escape(s, quote=True)


def strip_tags(s: str) -> str:
    return htmllib.unescape(re.sub(r"<[^>]+>", "", s))


def css_str(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def display_width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def extract_svg(text: str) -> str | None:
    a, b = text.find("<svg"), text.rfind("</svg>")
    if a < 0 or b < 0:
        return None
    svg = text[a:b + len("</svg>")]
    head = re.match(r"<svg\b[^>]*>", svg, re.S).group(0)
    if "viewBox" not in head:  # width/height はあるが viewBox が無いSVGは縮小できないので補う
        w = re.search(r'\bwidth="([\d.]+)(?:px)?"', head)
        h = re.search(r'\bheight="([\d.]+)(?:px)?"', head)
        if w and h:
            svg = svg.replace(head, head[:-1] + f' viewBox="0 0 {w.group(1)} {h.group(1)}">', 1)
    return svg


def scope_svg_ids(svg: str, prefix: str) -> str:
    """複数のSVGを1つのHTMLに展開しても id が衝突しないように接頭辞を付ける。"""
    for i in set(re.findall(r'\bid="([^"]+)"', svg)):
        svg = (svg.replace(f'id="{i}"', f'id="{prefix}{i}"')
                  .replace(f"url(#{i})", f"url(#{prefix}{i})")
                  .replace(f'href="#{i}"', f'href="#{prefix}{i}"'))
    return svg


def standalone_svg(svg: str) -> str:
    head = re.match(r"<svg\b[^>]*>", svg, re.S).group(0)
    new = head
    if "xmlns=" not in head:
        new = new.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    if "xlink:" in svg and "xmlns:xlink" not in head:
        new = new.replace("<svg", '<svg xmlns:xlink="http://www.w3.org/1999/xlink"', 1)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + svg.replace(head, new, 1)


def detect_filename(code: str) -> str:
    first = code.split("\n", 1)[0]
    m = FILENAME_RE.match(first)
    return m.group(1) if m else ""


def lang_label(lang: str) -> str:
    key = lang.lower()
    return LANG_NAMES.get(key, lang.capitalize() if lang else "")


class Assets:
    """出力先の images/ にファイルを集め、相対パスを返す。"""

    def __init__(self, out_dir: Path):
        self.dir = out_dir / "images"
        if self.dir.exists():
            shutil.rmtree(self.dir, ignore_errors=True)
        self.map: dict[Path, str] = {}
        self.used: set[str] = set()

    def _name(self, wanted: str) -> str:
        name, n = wanted, 1
        stem, suf = os.path.splitext(wanted)
        while name in self.used:
            n += 1
            name = f"{stem}_{n}{suf}"
        self.used.add(name)
        return name

    def add_file(self, path: Path) -> str:
        path = path.resolve()
        if path not in self.map:
            self.dir.mkdir(parents=True, exist_ok=True)
            name = self._name(path.name)
            shutil.copyfile(path, self.dir / name)
            self.map[path] = f"images/{name}"
        return self.map[path]

    def add_text(self, wanted: str, text: str) -> str:
        self.dir.mkdir(parents=True, exist_ok=True)
        name = self._name(wanted)
        (self.dir / name).write_text(text, encoding="utf-8")
        return f"images/{name}"


# ============================================================ 原稿の走査（コード・図・引用を切り出す）

def find_figure_file(book_dir: Path, x: int, y: int) -> Path | None:
    """/book-embed と同じ優先順位（SVG > キャプチャPNG > PNG/JPG/WEBP）で図ファイルを探す。"""
    names = [f"fig_{x}_{y}.svg", f"fig_{x}_{y}_capture.png", f"fig_{x}_{y}_capture.jpg",
             f"fig_{x}_{y}.png", f"fig_{x}_{y}.jpg", f"fig_{x}_{y}.jpeg", f"fig_{x}_{y}.webp"]
    for d in (f"chapter_{x:02d}", f"chapter_{x}"):
        for n in names:
            p = book_dir / "05_figures" / d / n
            if p.is_file():
                return p
    return None


def figure_from_marker(x: int, y: int, kind: str, title: str, summary: str, ctx: Ctx) -> Figure:
    fig = Figure(num=f"{x}.{y}", title=(title or summary).strip(), kind=kind.strip(),
                 summary=summary.strip() if title.strip() else "")
    f = find_figure_file(ctx.book_dir, x, y)
    if f is None:
        fig.missing = True
    elif f.suffix.lower() == ".svg":
        fig.svg = extract_svg(f.read_text(encoding="utf-8", errors="replace"))
        if fig.svg is None:
            ctx.warn(f"{f.name}: SVGとして読み込めないため入稿待ち扱いにしました")
            fig.missing = True
    else:
        fig.img = f
    return fig


def parse_figure_html(block: str, ctx: Ctx) -> Figure:
    """/book-embed が作る <figure> ブロックを解釈する。"""
    idm = re.search(r'id="fig-(\d+)-(\d+)"', block)
    capm = re.search(r"<figcaption>(.*?)</figcaption>", block, re.S)
    cap = strip_tags(capm.group(1)).strip() if capm else ""
    num = f"{idm.group(1)}.{idm.group(2)}" if idm else ""
    if not num:
        m = re.match(r"図\s*(\d+\.\d+)", cap)
        num = m.group(1) if m else "?"
    title = re.sub(r"^図\s*\d+\.\d+\s*[:：]?\s*", "", cap)
    title = re.sub(r"[（(]入稿待ち[）)]\s*$", "", title).strip()
    fig = Figure(num=num, title=title)
    placeholder = "figure-placeholder" in block or "入稿待ち" in cap
    svg = None if placeholder else extract_svg(block)
    img = re.search(r'<img\b[^>]*\bsrc="([^"]+)"', block)
    if svg:
        fig.svg = svg
    elif img and not placeholder:
        p = (ctx.src_dir / unquote(img.group(1))).resolve()
        if p.is_file():
            fig.img = p
        else:
            ctx.warn(f"{fig.label}: 画像ファイルが見つかりません（{img.group(1)}）")
            fig.missing = True
    else:
        fig.missing = True
        km = re.search(r">\s*([^<>—]+?)\s*—\s*入稿待ち\s*<", block)
        fig.kind = km.group(1).strip() if km else ""
    return fig


def callout_kind(label: str, exact: bool) -> str | None:
    up = label.upper()
    for key, kind in CALLOUT_KEYS:
        k = key.upper()
        if up == k or (not exact and up.startswith(k) and not label[len(key)].isalpha()):
            return kind
    return None


def match_callout(first_line: str):
    """引用ブロックの先頭ラベルから囲み記事の種別を判定する。
    戻り値: (原稿どおりのラベル, 種別, 残りの本文, 見出し) | None

    認識する書き方: `**ポイント**: …` / `**POINT:** …` / `💡 **ポイント**: …` / `NOTE: …`（太字なしは完全一致のみ）/ `[!NOTE]`
    見出し付き: `**POINT: 見出し**`（太字の中にコロン）→ 次の行からが本文
    ステップ: `**STEP 1**: 見出し` → 次の行からが説明
    """
    m = re.match(r"^\[!(\w+)\]\s*$", first_line)
    if m and m.group(1).upper() in GH_ALERTS:
        label, kind = GH_ALERTS[m.group(1).upper()]
        return label, kind, "", ""
    s = re.sub(r"^[^\w*\[（(]+", "", first_line)  # 行頭の絵文字・記号（💡 ⚠️ など）は装飾なので除く
    m = re.match(r"^\*\*(?P<l>[^*]+?)\*\*\s*[:：]?\s*(?P<rest>.*)$", s)
    bold = m is not None
    if not m:
        m = re.match(r"^(?P<l>[^\s:：*]{1,12})\s*[:：]\s*(?P<rest>.*)$", s)
    if not m:
        return None
    label, title = m.group("l").strip().rstrip(":：").strip(), ""
    tm = re.match(r"^([^:：]{1,12}?)\s*[:：]\s*(.+)$", label) if bold else None
    if tm and callout_kind(tm.group(1).strip(), exact=True):
        label, title = tm.group(1).strip(), tm.group(2).strip()
    kind = callout_kind(label, exact=not bold)
    if not kind:
        return None
    rest = m.group("rest").strip()
    if kind == "step" and not title:
        title, rest = rest, ""
    return label, kind, rest, title


def scan(text: str, ctx: Ctx) -> list[Seg]:
    """本文を md（通常のMarkdown）/ code / figure / callout / quote のセグメント列に分解する。"""
    lines = text.split("\n")
    segs: list[Seg] = []
    buf: list[str] = []
    i = 0

    def flush() -> None:
        if buf:
            segs.append(Seg("md", text="\n".join(buf)))
            buf.clear()

    while i < len(lines):
        line = lines[i]
        fm = FENCE_OPEN_RE.match(line)
        if fm and not (fm.group("fence")[0] == "`" and "`" in fm.group("info")):
            fence, indent = fm.group("fence"), fm.group("indent")
            j, code = i + 1, []
            while j < len(lines):
                cm = FENCE_CLOSE_RE.match(lines[j])
                if cm and cm.group(1)[0] == fence[0] and len(cm.group(1)) >= len(fence):
                    break
                code.append(lines[j][len(indent):] if lines[j].startswith(indent) else lines[j].lstrip())
                j += 1
            info = fm.group("info").strip()
            flush()
            segs.append(Seg("code", lang=info.split()[0] if info else "", code="\n".join(code), indent=indent))
            i = j + 1
            continue

        if re.match(r"^\s*<figure\b", line):
            j, block = i, []
            while j < len(lines):
                block.append(lines[j])
                if "</figure>" in lines[j]:
                    break
                j += 1
            flush()
            segs.append(Seg("figure", fig=parse_figure_html("\n".join(block), ctx)))
            i = j + 1
            continue

        mm = MARKER_NEW_RE.match(line)
        if mm:
            flush()
            x, y, kind, _flag, title, summary = mm.groups()
            segs.append(Seg("figure", fig=figure_from_marker(int(x), int(y), kind, title, summary or "", ctx)))
            i += 1
            continue
        mm = MARKER_OLD_RE.match(line)
        if mm:
            flush()
            kind = ""
            if mm.group(4):
                km = re.search(r"種類\s*[:：]\s*([^|]+)", mm.group(4))
                kind = km.group(1).strip() if km else ""
            segs.append(Seg("figure", fig=figure_from_marker(int(mm.group(1)), int(mm.group(2)), kind,
                                                            mm.group(3), "", ctx)))
            i += 1
            continue

        if re.match(r"^ {0,3}>", line):
            j, q = i, []
            while j < len(lines) and re.match(r"^ {0,3}>", lines[j]):
                q.append(re.sub(r"^ {0,3}> ?", "", lines[j]))
                j += 1
            flush()
            first = next((k for k, l in enumerate(q) if l.strip()), None)
            co = match_callout(q[first].strip()) if first is not None else None
            if first is not None and DIALOGUE_RE.match(q[first].strip()):
                body = "\n".join(q[first + 1:]).strip("\n")
                spaced = re.sub(r"\n(?=\*\*[^*]{1,12}\*\*\s*[:：])", "\n\n", body)  # 発言ごとに段落を分ける
                segs.append(Seg("callout", ckind="dialogue", text=body, body=scan(spaced, ctx)))
            elif co:
                label, kind, rest, title = co
                body_lines = ([rest] if rest else []) + q[first + 1:]
                segs.append(Seg("callout", ckind=kind, label=label, title=title,
                                body=scan("\n".join(body_lines), ctx)))
            else:
                segs.append(Seg("quote", body=scan("\n".join(q), ctx)))
            i = j
            continue

        buf.append(line)
        i += 1
    flush()
    return segs


LIST_ITEM_RE = re.compile(r"^(?P<ind>[ \t]*)(?:[-*+]|\d+[.)])[ \t]+\S")


def reindent_lists(text: str) -> str:
    """入れ子のリストのインデントを4の倍数にそろえる。

    Python-Markdown は入れ子を「4スペース」でしか認識しないが、LLM が書く原稿は2〜3スペース
    （CommonMark流）が普通で、そのままだと入れ子が崩れて同じ行に連結される。文字は変えず、
    行頭の空白だけを直す。
    """
    out: list[str] = []
    stack: list[int] = []   # 開いているリスト項目の元のインデント幅
    for line in text.split("\n"):
        if LIST_ITEM_RE.match(line) and not re.fullmatch(r"[-*_ ]{3,}", line.strip()):
            n = len(re.match(r"[ \t]*", line).group(0).expandtabs(4))
            while stack and stack[-1] >= n:
                stack.pop()
            out.append(" " * (4 * len(stack)) + line.lstrip(" \t"))
            stack.append(n)
        elif not line.strip():
            out.append(line)
        elif stack and line[0] in " \t":   # 項目の続きの行（段落・コードのトークン等）
            n = len(re.match(r"[ \t]*", line).group(0).expandtabs(4))
            while stack and stack[-1] >= n:
                stack.pop()
            out.append(" " * (4 * len(stack)) + line.lstrip(" \t") if stack else line)
        else:
            stack = []
            out.append(line)
    return "\n".join(out)


def normalize_md(text: str) -> str:
    """Python-Markdown が解釈できるよう、リストの入れ子を4スペースにそろえ、リスト・表の直前に空行を補う
    （CommonMark由来の書き方への対策）。"""
    text = reindent_lists(text)
    lines = text.split("\n")
    out: list[str] = []
    for idx, line in enumerate(lines):
        prev = out[-1] if out else ""
        if prev.strip() and not prev.startswith((" ", "\t")):
            if LIST_RE.match(line) and not LIST_RE.match(prev):
                out.append("")
            elif ("|" in line and idx + 1 < len(lines) and TABLE_SEP_RE.match(lines[idx + 1])
                  and "|" not in prev):
                out.append("")
        out.append(line)
    return "\n".join(out)


def callout_heading(s: Seg) -> str:
    """囲み記事のラベル行（「POINT: 見出し」「STEP 1: 見出し」）。会話ボックスはラベルなし。"""
    return f"{s.label}: {s.title}" if s.title else s.label


def walk(segs: list[Seg]):
    for s in segs:
        yield s
        if s.body:
            yield from walk(s.body)


# ============================================================ 整理（見出し構造・段落）
# 方針: 文字は一切足さず・消さず、構造（見出しレベル・段落の切れ目）だけを整える。
#       整えた件数は ctx.note() で記録し、変換レポートに出す。

def parse_heading(line: str):
    """ATX見出しを (レベル, テキスト, 記号の後に空白があったか) で返す。見出しでなければ None。"""
    m = re.match(r"^(#{1,6})[ \t]+(.*?)[ \t]*$", line)
    spaced = m is not None
    if not m:
        m = re.match(r"^(#{1,6})([^\x00-\x7f].*?)[ \t]*$", line)  # 「##見出し」（空白なし）
    if not m:
        return None
    title = re.sub(r"[ \t]+#+$", "", m.group(2)).strip()
    return (len(m.group(1)), title, spaced) if title else None


def fix_headings(text: str, state: dict, ctx: Ctx) -> str:
    """章内の見出しレベルを整える（章タイトルは H1 として別に扱うため、本文中は ## から始める）。"""
    out = []
    for line in text.split("\n"):
        h = parse_heading(line)
        if not h:
            out.append(line)
            continue
        level, title, spaced = h
        new = 2 if level == 1 else level
        if level == 1:
            ctx.note("章の途中の「#」見出しを「##」に変更")
        limit = min(state["prev"] + 1, 4)
        if new > limit:
            ctx.note("見出しレベルの飛び・深すぎる階層を補正")
            new = limit
        if not spaced:
            ctx.note("「##見出し」の記号直後に空白を補完")
        state["prev"] = new
        out.append("#" * new + " " + title)
    return "\n".join(out)


OPEN_BR, CLOSE_BR = "「『（(【［〈《", "」』）)】］〉》"


def split_sentences(text: str) -> list[str]:
    """「。！？」で文に分ける。かっこ内・インラインコード内の句点では分けない。"""
    out, cur, depth, in_code = [], [], 0, False
    for i, ch in enumerate(text):
        cur.append(ch)
        if ch == "`":
            in_code = not in_code
        elif in_code:
            continue
        elif ch in OPEN_BR:
            depth += 1
        elif ch in CLOSE_BR:
            depth = max(0, depth - 1)
        elif ch in "。！？" and depth == 0 and not (i + 1 < len(text) and text[i + 1] in "。！？" + CLOSE_BR):
            out.append("".join(cur))
            cur = []
    if "".join(cur).strip():
        out.append("".join(cur))
    return out


def is_plain_paragraph(lines: list[str]) -> bool:
    for l in lines:
        if not l.strip() or l[0] in " \t" or l.endswith("  ") or "<br" in l:
            return False
        if re.match(r"^(#{1,6}\s|>|[-*+]\s|\d+[.)]\s|\||<|!\[|\[FIG|\[図|:::|---|===|\*\*\*|\[[^\]]+\]:)", l):
            return False
    return True


def join_lines(lines: list[str]) -> str:
    out = lines[0].strip()
    for l in (x.strip() for x in lines[1:]):
        # 日本語どうしの改行は詰め、英数字が絡むときだけ空白1つにする
        cjk = re.match(f"[{CJK}]", out[-1:] or "x") or re.match(f"[{CJK}]", l[:1] or "x")
        out += l if cjk else " " + l
    return out


def organize_paragraphs(text: str, ctx: Ctx) -> str:
    """・改行で折り返された段落を1段落にまとめる  ・style-guide の目安（6文）を超える段落を文の切れ目で分ける"""
    blocks, out = re.split(r"\n[ \t]*\n", text), []
    for b in blocks:
        lines = b.strip("\n").split("\n")
        if not "".join(lines).strip():
            continue
        if not is_plain_paragraph(lines):
            out.append("\n".join(lines))
            continue
        para = join_lines(lines)
        if len(lines) > 1:
            ctx.note("改行で折り返された段落を1段落に整理")
        sents = split_sentences(para)
        if len([s for s in sents if s.strip()]) > MAX_SENTENCES:
            k = -(-len(sents) // 5)          # 1段落あたり5文前後になるよう等分する
            size = -(-len(sents) // k)
            out.extend("".join(sents[i:i + size]).strip() for i in range(0, len(sents), size))
            ctx.note(f"長い段落（{MAX_SENTENCES + 1}文以上）を文の切れ目で分割")
        else:
            out.append(para)
    return "\n\n".join(out)


def organize_segs(segs: list[Seg], ctx: Ctx, state: dict | None = None, top: bool = True) -> None:
    state = state if state is not None else {"prev": 1}
    for s in segs:
        if s.kind == "md":
            if top:
                s.text = fix_headings(s.text, state, ctx)
            s.text = organize_paragraphs(s.text, ctx)
        elif s.body:
            organize_segs(s.body, ctx, state, top=False)


# ============================================================ 内容チェック（原稿の文字が出力に残っているか）
# 「原稿の内容を勝手に削除しない」を機械的に確かめる。Markdown記号・空白・絵文字・コロンを除いた文字列で、
# 原稿の各行が出力に含まれているかを見る。図マーカー・<figure>・HTMLコメントは対象外（別の形で描画されるため）。

_DROP = set("*_`~\\|:：")


def norm(s: str) -> str:
    s = htmllib.unescape(s)
    return "".join(c for c in s if not c.isspace() and c not in _DROP
                   and unicodedata.category(c) not in ("So", "Mn", "Cf", "Sk"))


def reduce_line(line: str) -> list[str]:
    s = line.strip()
    if not s or re.fullmatch(r"[-*_=:|\s]+", s):
        return []
    while True:  # 引用・見出し・リストの記号を外す
        n = re.sub(r"^(?:>+\s?|#{1,6}\s*|[-*+]\s+|\d+[.)]\s+)", "", s).strip()
        if n == s:
            break
        s = n
    if re.match(r"^\[!\w+\]$", s) or s.startswith(("```", "~~~")):
        return []
    # インラインコードの中身は出力にそのまま文字として残るので、画像・リンク・タグの除去から守る
    codes: list[str] = []
    s = re.sub(r"(`+)(.+?)\1", lambda m: (codes.append(m.group(0)), f"\x00{len(codes) - 1}\x00")[1], s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)
    cells = s.split("|") if s.count("|") >= 2 else [s]  # 表は1セルずつ確認する
    return [u for u in (norm(c) for c in cells) if len(u) >= 2]


def source_units(text: str):
    """原稿を1行ずつ (元の行, 確認用の文字列リスト) にする。コードブロック内は記号を外さずそのまま確認する。"""
    fence, in_fig, in_comment = None, False, False
    for line in text.split("\n"):
        if in_fig:
            in_fig = "</figure>" not in line
            continue
        if in_comment:
            in_comment = "-->" not in line
            continue
        if fence:
            cm = FENCE_CLOSE_RE.match(line)
            if cm and cm.group(1)[0] == fence[0] and len(cm.group(1)) >= len(fence):
                fence = None
            elif len(norm(line)) >= 2:
                yield line, [norm(line)]
            continue
        fm = FENCE_OPEN_RE.match(line)
        if fm and not (fm.group("fence")[0] == "`" and "`" in fm.group("info")):
            fence = fm.group("fence")
            continue
        if re.match(r"^\s*<figure\b", line):
            in_fig = "</figure>" not in line
            continue
        if MARKER_NEW_RE.match(line) or MARKER_OLD_RE.match(line):
            continue
        if re.match(r"^\s*<!--", line):
            in_comment = "-->" not in line
            continue
        units = reduce_line(line)
        if units:
            yield line, units


def find_missing(source_text: str, output_blob: str) -> list[str]:
    """原稿の行のうち、出力（norm済みの文字列）に見つからないものを返す。"""
    return [orig.strip() for orig, us in source_units(source_text) if any(u not in output_blob for u in us)]


# ============================================================ 章の読み込み

def load_chapter(path: Path, ctx: Ctx) -> Chapter | None:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    fm = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if fm:  # メタ情報のため本文には出さないが、黙って捨てず必ず知らせる
        keys = ", ".join(re.findall(r"^([\w\-]+)\s*:", fm.group(1), re.M)) or "内容あり"
        ctx.warn(f"{path.name}: 先頭のYAMLフロントマター（{keys}）は本文に含めていません。必要なら本文に書き写してください")
        text = text[fm.end():]
    if not text.strip():
        ctx.warn(f"{path.name}: 空ファイルのためスキップしました")
        return None
    num = int(re.search(r"chapter_(\d+)", path.name).group(1))
    ctx.src_dir = path.parent  # 画像の相対パスはこの章のファイルの場所を基準に解決する
    tags, en_title = [], ""
    for m in CHAPTER_DIRECTIVE_RE.finditer(text):  # 章扉用のキーワード行（本文ではないので取り除く）
        if m.group(1).upper() == "TAGS":
            tags += [t.lstrip("#＃").strip() for t in re.split(r"[,、，]|\s+(?=[#＃])", m.group(2)) if t.strip("#＃ ")]
        else:
            en_title = m.group(2).strip()
    text = CHAPTER_DIRECTIVE_RE.sub("", text)
    segs = scan(text, ctx)

    h1_raw = ""
    for s in segs:
        if s.kind == "md":
            m = re.search(r"^#[ \t]+(.+?)[ \t]*$", s.text, re.M)
            if m:
                h1_raw = m.group(1)
                s.text = s.text[:m.start()] + s.text[m.end():]
            break
    if not h1_raw:
        ctx.warn(f"{path.name}: 章タイトル（# 見出し）が見つかりません")
        h1_raw = f"第{num}章" if num else "はじめに"

    m = re.match(r"^(第\s*\d+\s*章)\s*[:：]?\s*(.*)$", h1_raw)
    label, title = (re.sub(r"\s+", "", m.group(1)), m.group(2)) if m and m.group(2) else ("", h1_raw)
    organize_segs(segs, ctx)
    return Chapter(num=num, src=path, h1_raw=h1_raw, label=label, title=title, segs=segs, raw=text,
                   tags=tags, en_title=en_title)


def classify_h2(plain: str) -> str:
    if GOALS_RE.match(plain):
        return "goals"
    if OVERVIEW_RE.match(plain):
        return "overview"
    if SUMMARY_RE.match(plain):
        return "summary"
    if COLUMN_RE.match(plain):
        return "column"
    return ""


# ============================================================ HTML レンダラ

class HtmlRenderer:
    def __init__(self, ctx: Ctx, assets: Assets):
        self.ctx, self.assets = ctx, assets
        self.stash: dict[str, str] = {}
        self.formatter = HtmlFormatter(nowrap=True)

    # ---- 特殊セグメント → HTML
    def _token(self, html: str) -> str:
        tok = f"BKTOKEN{len(self.stash)}END"
        self.stash[tok] = html
        return tok

    def code_html(self, s: Seg) -> str:
        lang = s.lang.lower()
        lexer = TextLexer()
        if lang not in ("text", "txt", "plaintext", ""):
            try:
                lexer = get_lexer_by_name(lang)
            except ClassNotFound:
                pass
        body = highlight(s.code, lexer, self.formatter).rstrip("\n")
        fname, lname = detect_filename(s.code), lang_label(s.lang)
        head = ""
        if fname or lname:
            head = (f'<div class="code-head"><span class="code-file">{esc(fname)}</span>'
                    f'<span class="code-lang">{esc(lname)}</span></div>')
        return f'<div class="code-block">{head}<pre class="code"><code>{body}</code></pre></div>'

    def figure_html(self, fig: Figure) -> str:
        cap = f'<figcaption><span class="fig-no">{esc(fig.label)}</span>{esc(fig.title)}</figcaption>'
        if fig.svg:
            svg = scope_svg_ids(fig.svg, fig.dom_id + "-")
            body = f'<div class="figure-body">{svg}</div>'
        elif fig.img:
            src = self.assets.add_file(fig.img)
            body = f'<div class="figure-body"><img src="{esc(src)}" alt="{esc(fig.label + ": " + fig.title)}"></div>'
        else:
            kind = f"{esc(fig.kind)} — " if fig.kind else ""
            desc = f'<div class="ph-desc">{esc(fig.summary)}</div>' if fig.summary else ""  # 原稿の「内容の要点」を残す
            body = (f'<div class="figure-body missing"><div class="ph-title">{esc(fig.label)}: {esc(fig.title)}</div>'
                    f'{desc}<div class="ph-note">{kind}入稿待ち</div></div>')
            cap = (f'<figcaption><span class="fig-no">{esc(fig.label)}</span>{esc(fig.title)}'
                   f'<span class="fig-pending">（入稿待ち）</span></figcaption>')
        cls = "figure figure-missing" if fig.missing else "figure"
        return f'<figure class="{cls}" id="{fig.dom_id}">{body}{cap}</figure>'

    def special_html(self, s: Seg) -> str:
        if s.kind == "code":
            return self.code_html(s)
        if s.kind == "figure":
            return self.figure_html(s.fig)
        inner = self.inline(s.body)
        if s.kind == "callout":
            label = callout_heading(s)
            title = f'<div class="callout-title">{esc(label)}</div>' if label else ""
            return (f'<div class="callout callout-{s.ckind}">{title}'
                    f'<div class="callout-body">{inner}</div></div>')
        return f"<blockquote>{inner}</blockquote>"

    # ---- セグメント列 → HTML（見出し装飾などの前段階）
    def inline(self, segs: list[Seg]) -> str:
        parts = []
        for s in segs:
            if s.kind == "md":
                parts.append(normalize_md(s.text))
            else:
                ind = ""
                if s.kind == "code" and s.indent:
                    ind = "    " * ((len(s.indent.replace("\t", "    ")) + 3) // 4)
                parts.append(f"\n\n{ind}{self._token(self.special_html(s))}\n\n")
        md = mdlib.Markdown(extensions=["tables", "sane_lists"])
        html = md.convert("".join(parts))
        html = CJK_JOIN_RE.sub("", html)
        # 表・コードは CSS の break-inside: avoid で「可能な限り」分割しない（1ページに収まらないものだけ分割される）
        html = re.sub(r"<table>.*?</table>", lambda m: f'<div class="table-wrap">{m.group(0)}</div>', html, flags=re.S)
        html = self._fix_images(html)
        for tok, frag in self.stash.items():
            if tok in html:
                html = html.replace(f"<p>{tok}</p>", frag).replace(tok, frag)
        # 「次のコードを保存します。」のようなリード文は、直後のコード・表・図と別ページに分かれないようにする
        html = re.sub(r'<p>((?:(?!</p>).){1,160})</p>(\s*)(?=<(?:div class="(?:code-block|table-wrap)|figure))',
                      r'<p class="keep-next">\1</p>\2', html, flags=re.S)
        return html

    def _fix_images(self, html: str) -> str:
        def repl(m: re.Match) -> str:
            src = m.group(2)
            if re.match(r"^(https?:|data:|#)", src):
                return m.group(0)
            p = (self.ctx.src_dir / unquote(src)).resolve()
            if not p.is_file():
                self.ctx.warn(f"画像が見つかりません: {src}")
                return m.group(0)
            return f'{m.group(1)}"{esc(self.assets.add_file(p))}"'
        return re.sub(r'(<img\b[^>]*?\bsrc=)"([^"]+)"', repl, html)

    # ---- 章
    def chapter_html(self, ch: Chapter) -> str:
        self.ctx.src_dir = ch.src.parent
        html = self.inline(ch.segs)
        counter = [0]

        def head(m: re.Match) -> str:
            level, inner = int(m.group(1)), m.group(2)
            if level != 2:
                return f"<h{level}>{inner}</h{level}>"
            counter[0] += 1
            hid = f"{ch.dom_id}-s{counter[0]}"
            nm = re.match(r"^(\d+(?:\.\d+)+)[\s\u3000]+(.*)$", inner, re.S)
            secno, rest = (nm.group(1), nm.group(2)) if nm else ("", inner)
            plain = strip_tags(rest).strip()
            cls = classify_h2(plain)
            if cls != "goals":
                ch.toc.append(dict(id=hid, secno=secno, title=plain, cls=cls))
            no = f'<span class="secno">{esc(secno)}</span>' if secno else ""
            return f'<h2 id="{hid}">{no}<span class="sectitle">{rest}</span></h2>'

        html = re.sub(r"<h([2-4])>(.*?)</h\1>", head, html, flags=re.S)
        html = re.sub(r"<hr\s*/?>", '<hr class="rule">', html)

        parts = re.split(r'(?=<h2 id=")', html)
        out = []
        for idx, part in enumerate(parts):
            part = re.sub(r'(\s*<hr class="rule">\s*)+$', "", part)  # 節の末尾の区切り線は、次の見出しが区切りを担うので省く
            if not part.strip():
                continue
            if idx == 0 and not part.startswith("<h2"):
                out.append(f'<section class="sec sec-intro">{part}</section>')
                continue
            hm = re.match(r'<h2 id="[^"]+">.*?<span class="sectitle">(.*?)</span></h2>', part, re.S)
            cls = classify_h2(strip_tags(hm.group(1)).strip()) if hm else ""
            out.append(f'<section class="sec{(" sec-" + cls) if cls else ""}">{part}</section>')

        label = f'<div class="chapter-label">{esc(ch.label)}</div>' if ch.label else ""  # 原稿の「第1章」をそのまま出す
        # 章扉（タイトルだけの独立ページ）は名前付きページ chN-open にして、ヘッダーとページ番号を出さない。
        # 本文の各節は chN ページ。名前が変わるので、章扉と本文の間で必ず改ページされる。
        body = "".join(out).replace('<section class="sec', f'<section style="page:ch{ch.num}" class="sec')
        return (f'<section class="chapter" id="{ch.dom_id}">'
                f'<header class="chapter-head" style="page:ch{ch.num}-open">{label}'
                f'<h1 class="chapter-title">{esc(ch.title)}</h1></header>' + body + "</section>")


def page_css(size: str, meta: Meta, chapters: list[Chapter]) -> str:
    p = PAPERS[size]
    head = 'font: 7pt "Yu Gothic","Noto Sans JP","Hiragino Kaku Gothic ProN",Meiryo,sans-serif; color: #7b8590;'
    foot = 'font: 8pt "Yu Gothic","Noto Sans JP","Hiragino Kaku Gothic ProN",Meiryo,sans-serif; color: #55606b;'
    book = css_str(meta.running)
    css = [
        '@charset "UTF-8";',
        f"/* ---- 自動生成: ページ設定（{size}） / 書式を変える場合は下のテーマ部分(book.cssの後半)を編集 ---- */",
        ":root {",
        f"  --page-w: {p['w']}mm; --page-h: {p['h']}mm;",
        f"  --fs: {p['font']}pt; --lh: {p['lh']}; --code-fs: {p['code']}pt;",
        f"  --m-top: {p['top']}mm; --m-bottom: {p['bottom']}mm; --m-in: {p['inner']}mm; --m-out: {p['outer']}mm;",
        "}",
        f"@page {{ size: {size} portrait; margin: {p['top']}mm {p['outer']}mm {p['bottom']}mm {p['inner']}mm; }}",
        f"@page :left {{ margin: {p['top']}mm {p['inner']}mm {p['bottom']}mm {p['outer']}mm;"
        f' @top-left {{ content: "{book}"; {head} }} @bottom-left {{ content: counter(page); {foot} }} }}',
        f"@page :right {{ margin: {p['top']}mm {p['outer']}mm {p['bottom']}mm {p['inner']}mm;"
        f' @top-right {{ content: "{book}"; {head} }} @bottom-right {{ content: counter(page); {foot} }} }}',
        "@page cover { margin: 0; @top-left { content: none } @top-right { content: none }"
        " @bottom-left { content: none } @bottom-right { content: none } }",
    ]
    for ch in chapters:
        running = css_str(f"{ch.label} {ch.title}".strip())
        # 本文ページ: 右ページの柱（ヘッダー）に章タイトルを出す。ページ番号は共通ルール（下のノンブル）で表示
        css.append(f'@page ch{ch.num}:right {{ @top-right {{ content: "{running}"; {head} }} }}')
        # 章扉: ヘッダーもページ番号も出さない（ページ番号のカウントは進む）
        css.append(f"@page ch{ch.num}-open {{ @top-left {{ content: none }} @top-right {{ content: none }}"
                   f" @bottom-left {{ content: none }} @bottom-right {{ content: none }} }}")
    return "\n".join(css) + "\n"


def build_html(chapters: list[Chapter], meta: Meta, ctx: Ctx, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = Assets(out_dir)
    r = HtmlRenderer(ctx, assets)
    chapter_html = [r.chapter_html(ch) for ch in chapters]
    for ch, html in zip(chapters, chapter_html):  # 原稿の文字が1行も欠けていないか確認する
        miss = find_missing(ch.raw, norm(strip_tags(html)))
        if miss:
            ctx.missing[f"HTML: {ch.label or ch.title}"] = miss

    toc = ['<nav class="toc" style="page:front"><h1 class="toc-title">目次</h1><ol class="toc-list">']
    for ch in chapters:
        label = f'<span class="toc-label">{esc(ch.label)}</span>' if ch.label else ""
        toc.append(f'<li class="toc-ch"><a href="#{ch.dom_id}">{label}<span class="toc-text">{esc(ch.title)}</span></a>')
        subs = [t for t in ch.toc if t["title"]]
        if subs:
            toc.append('<ol class="toc-sub">')
            for t in subs:
                no = f'<span class="toc-no">{esc(t["secno"])}</span>' if t["secno"] else ""
                toc.append(f'<li class="toc-{t["cls"] or "sec"}"><a href="#{t["id"]}">{no}{esc(t["title"])}</a></li>')
            toc.append("</ol>")
        toc.append("</li>")
    toc.append("</ol></nav>")

    sub = (f'<div class="cover-subtitle">{"<br />".join(esc(s) for s in meta.cover_subtitle_lines)}</div>'
           if meta.cover_subtitle_lines else "")
    author = (f'<div class="cover-author">{"<br />".join(esc(a) for a in meta.cover_author_lines)}</div>'
              if meta.cover_author_lines else "")
    date = f'<div class="cover-date">{esc(meta.date)}</div>' if meta.date else ""  # 日付は --date 指定時のみ
    cover = (f'<section class="cover"><div class="cover-inner"><div class="cover-rule"></div>'
             f'<h1 class="cover-title">{esc(meta.title)}</h1>{sub}{author}{date}</div></section>')

    doc = (f'<!DOCTYPE html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           f"<title>{esc(meta.title)}</title>\n"
           f'<link rel="stylesheet" href="book.css">\n</head>\n'
           f'<body class="size-{ctx.size}">\n<main class="book">\n{cover}\n' + "\n".join(toc) + "\n"
           + "\n".join(chapter_html) + "\n</main>\n</body>\n</html>\n")
    (out_dir / "index.html").write_text(doc, encoding="utf-8")

    template = CSS_TEMPLATE.read_text(encoding="utf-8")
    pyg = HtmlFormatter(style="friendly").get_style_defs("pre.code")
    (out_dir / "book.css").write_text(
        page_css(ctx.size, meta, chapters) + "\n/* ---- Pygments（シンタックスハイライト） ---- */\n" + pyg
        + "\n\n/* ---- テーマ（book.css） ---- */\n" + template, encoding="utf-8")
    return out_dir / "index.html"


# ============================================================ Markdown（装飾）レンダラ

class MdRenderer:
    def __init__(self, ctx: Ctx, assets: Assets):
        self.ctx, self.assets = ctx, assets

    def _rewrite_images(self, line: str) -> str:
        def repl(m: re.Match) -> str:
            src = m.group(2)
            if re.match(r"^(https?:|data:|#)", src):
                return m.group(0)
            p = (self.ctx.src_dir / unquote(src)).resolve()
            if not p.is_file():
                self.ctx.warn(f"画像が見つかりません: {src}")
                return m.group(0)
            return f"![{m.group(1)}]({self.assets.add_file(p)}{m.group(3)})"
        return IMG_MD_RE.sub(repl, line)

    def figure_lines(self, fig: Figure) -> list[str]:
        cap = f"{fig.label}: {fig.title}".rstrip(": ")
        if fig.svg:
            src = self.assets.add_text(fig.file_stem + ".svg", standalone_svg(fig.svg))
        elif fig.img:
            src = self.assets.add_file(fig.img)
        else:
            kind = f"{fig.kind}・" if fig.kind else ""
            desc = ["> " + fig.summary] if fig.summary else []  # 原稿の「内容の要点」を残す
            return ["", f"> **{cap}**（{kind}入稿待ち）", *desc, ""]
        return ["", f"![{cap}]({src})", "", f"*{cap}*", ""]

    def code_lines(self, s: Seg) -> list[str]:
        run = max([len(m) for m in re.findall(r"`+", s.code)] + [2])
        fence = "`" * (run + 1)
        fname = detect_filename(s.code)
        out = [""]
        if fname:
            out += [f"**{fname}**", ""]
        out += [f"{fence}{s.lang}", *s.code.split("\n"), fence, ""]
        return [(s.indent + l) if l else l for l in out]

    def lines(self, segs: list[Seg]) -> list[str]:
        st = PanelState()
        for s in segs:
            if s.kind == "md":
                for line in normalize_md(s.text).split("\n"):
                    line = self._rewrite_images(line)
                    hm = re.match(r"^##[ \t]+(.+?)[ \t]*$", line)
                    if hm:
                        st.close()
                        plain = re.sub(r"^\d+(?:\.\d+)+\s+", "", hm.group(1))
                        cls = classify_h2(plain)
                        st.panel = cls  # 特殊節ならここから次の見出し/区切り線までを引用ブロックで囲む
                        st.emit.append("")
                        st.emit.append(line)
                        st.emit.append("")
                    elif re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line):
                        st.close()
                        st.emit.append("")
                        st.emit.append("---")
                        st.emit.append("")
                    else:
                        st.add(line)
            elif s.kind == "code":
                for l in self.code_lines(s):
                    st.add(l)
            elif s.kind == "figure":
                for l in self.figure_lines(s.fig):
                    st.add(l)
            elif s.kind in ("callout", "quote"):
                inner = self.lines(s.body)
                while inner and not inner[0].strip():
                    inner.pop(0)
                while inner and not inner[-1].strip():
                    inner.pop()
                if s.kind == "callout" and s.title:
                    inner = [f"**{callout_heading(s)}**"] + ([""] + inner if inner else [])
                elif s.kind == "callout" and s.label:
                    title = f"**{s.label}**"  # ラベルは原稿のまま（POINT / 注意 など）
                    if inner:
                        inner[0] = f"{title}: {inner[0]}"
                    else:
                        inner = [title]
                st.add("")
                for l in inner:
                    st.add(("> " + l) if l.strip() else ">")
                st.add("")
        st.close()
        return st.emit

    def chapter_md(self, ch: Chapter, first: bool) -> str:
        self.ctx.src_dir = ch.src.parent
        head = []
        if not first:
            head.append('<div style="page-break-after: always;"></div>')
            head.append("")
        head.append(f'<a id="{ch.dom_id}"></a>')
        head.append("")
        head.append(f"# {ch.h1_raw}")
        body = self.lines(ch.segs)
        text = "\n".join(head + body)
        return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


class PanelState:
    """「この章で学ぶこと」「本章のまとめ」「コラム」の節を引用ブロックの囲みにするための状態。"""

    def __init__(self):
        self.emit: list[str] = []
        self.buf: list[str] = []
        self.panel = ""

    def add(self, line: str) -> None:
        (self.buf if self.panel else self.emit).append(line)

    def close(self) -> None:
        if self.panel:
            body = self.buf
            while body and not body[0].strip():
                body = body[1:]
            while body and not body[-1].strip():
                body = body[:-1]
            self.emit.append("")
            self.emit.extend(("> " + l) if l.strip() else ">" for l in body)
            self.emit.append("")
        self.panel, self.buf = "", []


def build_markdown(chapters: list[Chapter], meta: Meta, ctx: Ctx, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = Assets(out_dir)
    r = MdRenderer(ctx, assets)
    p = PAPERS[ctx.size]

    body = [r.chapter_md(ch, first=(i == 0)) for i, ch in enumerate(chapters)]  # 先に処理して見出し等を確定

    def yq(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    fm = ["---", f"title: {yq(meta.title)}"]
    if meta.subtitle:
        fm.append(f"subtitle: {yq(meta.subtitle)}")
    if meta.author:
        fm.append(f"author: {yq(meta.author)}")
    if meta.date:
        fm.append(f"date: {yq(meta.date)}")
    fm += ["lang: ja", f"papersize: {ctx.size.lower()}",
           f"geometry: [{ctx.size.lower()}paper, top={p['top']}mm, bottom={p['bottom']}mm, "
           f"inner={p['inner']}mm, outer={p['outer']}mm]", "---", ""]
    style = (f'<style>@page {{ size: {ctx.size} portrait; margin: {p["top"]}mm {p["outer"]}mm {p["bottom"]}mm {p["inner"]}mm; }}</style>')
    cover = [style, "", f"# {meta.title}", ""]
    if meta.subtitle:
        cover += [f"### {meta.subtitle}", ""]
    info = " ・ ".join(x for x in [meta.author, meta.date, f"{ctx.size}判"] if x)
    cover += [f"> {info}", "", "---", "", "## 目次", ""]
    for ch in chapters:
        label = f"{ch.label}　" if ch.label else ""
        cover.append(f"- **[{label}{ch.title}](#{ch.dom_id})**")
        for t in ch.toc:
            no = f"{t['secno']} " if t["secno"] else ""
            cover.append(f"  - [{no}{t['title']}](#{t['id']})")
    cover += ["", '<div style="page-break-after: always;"></div>', ""]

    for ch, chapter_text in zip(chapters, body):  # 原稿の文字が1行も欠けていないか確認する
        blob = "".join(u for _, us in source_units(chapter_text) for u in us)
        miss = find_missing(ch.raw, blob)
        if miss:
            ctx.missing[f"Markdown: {ch.label or ch.title}"] = miss

    text = "\n".join(fm + cover) + "\n" + "\n\n".join(body)
    # ToC のためHTML側で章の節見出し(ch.toc)を確定させてあることが前提。MD側は見出しにアンカーを付ける
    text = _anchor_sections(text, chapters)
    out = out_dir / "book.md"
    out.write_text(text, encoding="utf-8")
    return out


def _anchor_sections(text: str, chapters: list[Chapter]) -> str:
    """節見出し（## ...）の直前に <a id> を挿入して、目次リンクを機能させる。"""
    anchors = {}
    for ch in chapters:
        for t in ch.toc:
            anchors.setdefault(t["title"], []).append(t["id"])
    used = {k: 0 for k in anchors}

    def repl(m: re.Match) -> str:
        plain = re.sub(r"^\d+(?:\.\d+)+\s+", "", m.group(2)).strip()
        ids = anchors.get(plain)
        if not ids or used[plain] >= len(ids):
            return m.group(0)
        aid = ids[used[plain]]
        used[plain] += 1
        return f'<a id="{aid}"></a>\n\n{m.group(0)}'
    return re.sub(r"^(##)[ \t]+(.+)$", repl, text, flags=re.M)


# ============================================================ PDF（Chrome / Edge ヘッドレス印刷）

def find_browser(explicit: str | None) -> str | None:
    cands: list[str] = []
    if explicit:
        cands.append(explicit)
    if os.environ.get("BOOK_FORMAT_BROWSER"):
        cands.append(os.environ["BOOK_FORMAT_BROWSER"])
    if sys.platform == "win32":
        bases = [b for b in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"),
                             os.environ.get("LOCALAPPDATA")) if b]
        cands += [os.path.join(b, r"Google\Chrome\Application\chrome.exe") for b in bases]  # Chrome を優先
        cands += [os.path.join(b, r"Microsoft\Edge\Application\msedge.exe") for b in bases]
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome", "msedge"):
        w = shutil.which(name)
        if w:
            cands.append(w)
    for c in cands:
        if c and Path(c).is_file():
            return c
    return None


def make_pdf(html_path: Path, pdf_path: Path, browser: str) -> tuple[bool, str]:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    profile = tempfile.mkdtemp(prefix="bookfmt-")
    cmd = [browser, "--headless=new", "--disable-gpu", f"--user-data-dir={profile}",
           "--no-pdf-header-footer", "--print-to-pdf-no-header", "--generate-pdf-document-outline",
           "--allow-file-access-from-files", "--virtual-time-budget=30000",
           f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.insert(2, "--no-sandbox")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        err = (proc.stderr or "")[-600:]
    except subprocess.TimeoutExpired:
        return False, "タイムアウト（300秒）"
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if pdf_path.is_file() and pdf_path.stat().st_size > 0:
        return True, ""
    return False, err.strip() or "PDFが生成されませんでした"


def docx_available() -> bool:
    try:
        import docx  # noqa: F401
        return True
    except ImportError:
        return False


def build_word(chapters: list[Chapter], meta: Meta, ctx: Ctx, out_dir: Path, browser: str | None) -> Path:
    """Word(.docx) を作り、原稿の文字が欠けていないか確認する。実装は book_docx.py。"""
    if str(TOOL_DIR) not in sys.path:
        sys.path.insert(0, str(TOOL_DIR))
    import book_docx
    me = sys.modules[__name__]
    out = book_docx.build_docx(me, chapters, meta, ctx, out_dir / "book.docx", browser)
    blob = book_docx.docx_text_blob(out, me)
    for ch in chapters:
        miss = find_missing(ch.raw, blob)
        if miss:
            ctx.missing[f"Word: {ch.label or ch.title}"] = miss
    return out


def count_pdf_pages(pdf_path: Path) -> int | None:
    try:
        return len(re.findall(rb"/Type\s*/Page[^s]", pdf_path.read_bytes())) or None
    except OSError:
        return None


# ============================================================ プロジェクト解決・メタ情報

def resolve_book_dir(arg: str | None) -> tuple[Path, Path]:
    """--project から (プロジェクトルート, book ディレクトリ) を決める。"""
    if arg:
        p = Path(arg).resolve()
        if (p / "book").is_dir():
            return p, p / "book"
        if (p / "03_manuscripts").is_dir():
            return p.parent, p
        sys.exit(f"ERROR: {p} に book/ が見つかりません。--project にはプロジェクトフォルダ（例: projects/my-book）を指定してください")
    found = sorted(d.parent for d in Path("projects").glob("*/book/03_manuscripts")) if Path("projects").is_dir() else []
    if len(found) == 1:
        return found[0].resolve(), (found[0] / "book").resolve()
    if not found:
        sys.exit("ERROR: projects/*/book/03_manuscripts が見つかりません。先に /book-chapter で原稿を作成してください")
    sys.exit("ERROR: 書籍プロジェクトが複数あります。--project で指定してください:\n  " + "\n  ".join(str(f) for f in found))


def read_meta(project_dir: Path, book_dir: Path, args) -> Meta:
    def clean(v: str) -> str:
        v = re.sub(r"[*`]", "", v).strip()
        return "" if (v.startswith("[") and v.endswith("]")) else v

    info = read_book_info(book_dir / "book_info.md")
    title_lines = info.get("TITLE", [])
    title = args.title or "".join(re.sub(r"\*\*", "", l) for l in title_lines)
    subtitle = args.subtitle or " ".join(info.get("SUBTITLE", []))
    concept = project_dir / "00_planning" / "concept.md"
    if concept.is_file():
        txt = concept.read_text(encoding="utf-8-sig")
        if not title:
            m = re.search(r"メインタイトル\**\s*[:：]\s*(.+)", txt)
            title = clean(m.group(1)) if m else ""
        if not subtitle:
            m = re.search(r"サブタイトル\**\s*[:：]\s*(.+)", txt)
            subtitle = clean(m.group(1)) if m else ""
    if not title:
        outline = book_dir / "01_structure" / "chapter_outline.md"
        if outline.is_file():
            m = re.search(r"^#\s*書籍構成\s*[:：]\s*(.+)$", outline.read_text(encoding="utf-8-sig"), re.M)
            title = clean(m.group(1)) if m else ""
    if not title:
        title = project_dir.name
    if args.title or not title_lines:
        title_lines = [title]

    def one(key: str) -> str:
        return " ".join(info.get(key, []))
    # 日付・著者は原稿にない情報なので、--date / --author か book_info.md で明示されたときだけ表紙に入れる
    # SUBTITLE / AUTHOR は複数行で書くと表紙で行ごとに改行する（引数で指定したときは1行）
    subtitle_lines = [args.subtitle] if args.subtitle else (info.get("SUBTITLE", []) or ([subtitle] if subtitle else []))
    author_lines = [args.author] if args.author else info.get("AUTHOR", [])
    return Meta(title=title, subtitle=subtitle, author=args.author or one("AUTHOR"), date=args.date or one("DATE"),
                title_lines=title_lines, series=one("SERIES"), description=info.get("DESCRIPTION", []),
                features=info.get("FEATURE", []), publisher=one("PUBLISHER"), header=one("HEADER"),
                subtitle_lines=subtitle_lines, author_lines=author_lines)


def read_book_info(path: Path) -> dict[str, list[str]]:
    """book/book_info.md の `# KEY: 値` 行を読む（KEY は BOOK_INFO_KEYS。同じKEYを複数行書くと複数行の値になる）。"""
    info: dict[str, list[str]] = {}
    if not path.is_file():
        return info
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        m = BOOK_INFO_RE.match(line.strip())
        if m and m.group(2).strip() and not re.fullmatch(r"\[.*\]", m.group(2).strip()):  # [未記入] は無視
            info.setdefault(m.group(1).upper(), []).append(m.group(2).strip())
    return info


def collect_chapters(src_dir: Path, wanted: list[int] | None) -> dict[int, Path]:
    files: dict[int, Path] = {}
    for f in src_dir.glob("chapter_*.md"):
        m = re.fullmatch(r"chapter_(\d+)\.md", f.name)
        if m and (wanted is None or int(m.group(1)) in wanted):
            files[int(m.group(1))] = f
    return files


def pick_sources(book_dir: Path, mode: str, wanted: list[int] | None, ctx: Ctx) -> tuple[list[Path], str]:
    """章ごとに入力ファイルを決める。auto は 06_final（図埋め込み済み）を優先し、無い章だけ 03_manuscripts を使う。"""
    ms = collect_chapters(book_dir / "03_manuscripts", wanted)
    fin = collect_chapters(book_dir / "06_final", wanted)
    if mode == "manuscripts":
        chosen = {n: (f, "03_manuscripts") for n, f in ms.items()}
    elif mode == "final":
        chosen = {n: (f, "06_final") for n, f in fin.items()}
    else:
        chosen = {n: (f, "03_manuscripts") for n, f in ms.items()}
        for n, f in fin.items():
            chosen[n] = (f, "06_final")
            if n in ms and f.stat().st_mtime < ms[n].stat().st_mtime:
                ctx.warn(f"chapter_{n:02d}: 06_final が 03_manuscripts より古い状態です。最新の内容を反映するには /book-embed {n} を再実行してください")
        if fin:
            for n in sorted(set(chosen) - set(fin)):
                ctx.warn(f"chapter_{n:02d}: 06_final に無いため図埋め込み前の原稿を使用しました（図ファイルがあれば変換時に取り込みます）")
    order = sorted(chosen)
    used = {d for _, d in chosen.values()}
    desc = " + ".join(sorted(used, reverse=True)) if used else "-"
    return [chosen[n][0] for n in order], desc


def analyze(chapters: list[Chapter], ctx: Ctx, papers: dict | None = None) -> dict:
    """図・コードの集計と、用紙サイズに対する警告（コードの折り返し）を作る。"""
    p = (papers or PAPERS)[ctx.size]
    text_w_mm = p["w"] - p["inner"] - p["outer"] - 8
    cols = int(text_w_mm / (p["code"] * 0.6 * 0.3528))
    stats = {"svg": 0, "img": 0, "missing": 0, "code_cols": cols, "wide": {}}
    for ch in chapters:
        for s in walk(ch.segs):
            if s.kind == "figure":
                f = s.fig
                stats["missing" if f.missing else "svg" if f.svg else "img"] += 1
            elif s.kind == "code":
                n = sum(1 for l in s.code.split("\n") if display_width(l) > cols)
                if n:
                    stats["wide"][ch.label or ch.title] = stats["wide"].get(ch.label or ch.title, 0) + n
    plain_quotes = sum(1 for ch in chapters for s in walk(ch.segs) if s.kind == "quote")
    if plain_quotes:  # 内容から種別を推測して意味づけを足すことはしない。ラベルを付けたい場合は原稿側で指定してもらう
        ctx.note(f"種別ラベルのない引用ブロックを通常の引用として表示（{plain_quotes}個。POINT/NOTE/WARNING等にしたい場合は先頭を「**ポイント**:」の形に）", 0)
    for name, n in stats["wide"].items():
        ctx.warn(f"{name}: {ctx.size}の1行{cols}桁を超えるコード行が{n}行あります（折り返して表示されます）")
    if stats["missing"]:
        ctx.warn(f"入稿待ちの図が{stats['missing']}点あります（プレースホルダーで出力）")
    return stats


# ============================================================ メイン

def parse_chapters_arg(v: str | None) -> list[int] | None:
    if not v:
        return None
    nums: list[int] = []
    for part in re.split(r"[,\s、]+", v.strip()):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            nums += list(range(int(m.group(1)), int(m.group(2)) + 1))
        elif part.isdigit():
            nums.append(int(part))
        else:
            sys.exit(f"ERROR: --chapters の指定が不正です: {part}")
    return sorted(set(nums))


def main() -> int:
    ap = argparse.ArgumentParser(description="書籍原稿を装飾付き原稿（md/html/pdf）へ変換")
    ap.add_argument("--project", help="プロジェクトフォルダ（例: projects/my-book）。省略時は projects/ 内に1つだけなら自動選択")
    ap.add_argument("--format", default="all", help="md / html / pdf / docx(word) / all（カンマ区切りで複数可）")
    ap.add_argument("--size", default="A5", help="A4 または A5")
    ap.add_argument("--chapters", help="対象章（例: 1,3 / 0-2）。省略時は全章")
    ap.add_argument("--source", choices=["auto", "final", "manuscripts"], default="auto",
                    help="入力元。auto=06_final優先（図埋め込み済み）、なければ03_manuscripts")
    ap.add_argument("--title"), ap.add_argument("--subtitle"), ap.add_argument("--author"), ap.add_argument("--date")
    ap.add_argument("--out", help="出力先ルート（既定: book/07_publish）")
    ap.add_argument("--browser", help="PDF生成に使うChrome/Edgeの実行ファイル")
    ap.add_argument("--theme", choices=["techbook", "classic"], default="techbook",
                    help="HTML/PDFのデザイン。techbook=format-template/ のHTML・CSS（既定）、classic=従来の book.css")
    ap.add_argument("--template-dir", help="techbook のデザインフォルダ（既定: リポジトリ直下の format-template/）")
    args = ap.parse_args()

    size = args.size.upper()
    if size not in PAPERS:
        sys.exit(f"ERROR: 用紙サイズは A4 か A5 を指定してください（指定値: {args.size}）")
    fmts, skip_word = set(), False
    for f in re.split(r"[,\s]+", args.format.lower()):
        if f in ("all", ""):
            fmts |= {"md", "html", "pdf"}
            if docx_available():
                fmts.add("docx")
            else:
                skip_word = True   # all のときだけ、python-docx が無ければ Word は飛ばす（明示指定ならエラー）
        elif f in ("md", "markdown"):
            fmts.add("md")
        elif f in ("word", "docx"):
            fmts.add("docx")
        elif f in ("html", "pdf"):
            fmts.add(f)
        else:
            sys.exit(f"ERROR: --format は md / html / pdf / docx / all のいずれかです（指定値: {f}）")
    if "docx" in fmts and not docx_available():
        print("ERROR: Word出力には python-docx が必要です。次のコマンドで導入してください:\n"
              "    python -m pip install python-docx pillow", file=sys.stderr)
        sys.exit(3)

    project_dir, book_dir = resolve_book_dir(args.project)
    wanted = parse_chapters_arg(args.chapters)

    ctx = Ctx(book_dir, book_dir / "03_manuscripts", size)
    files, src_name = pick_sources(book_dir, args.source, wanted, ctx)
    if not files:
        sys.exit(f"ERROR: {book_dir} に対象の chapter_XX.md がありません。先に /book-chapter を実行してください")
    chapters = [c for c in (load_chapter(f, ctx) for f in files) if c]
    if not chapters:
        sys.exit("ERROR: 変換できる章がありません（すべて空ファイルでした）")
    meta = read_meta(project_dir, book_dir, args)
    techbook = None
    if args.theme == "techbook":
        if str(TOOL_DIR) not in sys.path:
            sys.path.insert(0, str(TOOL_DIR))
        import techbook
        template_dir = Path(args.template_dir).resolve() if args.template_dir else techbook.DEFAULT_TEMPLATE_DIR
        if not (template_dir / techbook.SIZES[size]["css"]).is_file():
            sys.exit(f"ERROR: デザインのCSSが見つかりません: {template_dir / techbook.SIZES[size]['css']}"
                     "（--template-dir で format-template フォルダを指定するか、--theme classic を使ってください）")
    stats = analyze(chapters, ctx, techbook.PAPERS if techbook else None)

    suffix = size if wanted is None else f"{size}_ch{'-'.join(str(n) for n in wanted)}"
    out_root = Path(args.out).resolve() if args.out else book_dir / OUT_DIRNAME
    out = out_root / suffix
    results: list[str] = []

    # HTML は PDF の生成元でもあるため、md/html/pdf のどれを選んでも先に作る
    html_dir = out / "html"
    me = sys.modules[__name__]
    browser = find_browser(args.browser) if fmts & {"pdf", "docx", "html"} else None
    pass1_pdf = None
    if techbook:
        html_path = techbook.build_html(me, chapters, meta, ctx, html_dir, template_dir)  # ch.toc を確定させる
        if browser and fmts & {"pdf", "html"}:
            # 目次のページ番号: 1回目のPDFのしおりから各見出しのページを読み取り、HTMLを作り直す
            tmp_dir = None if "pdf" in fmts else Path(tempfile.mkdtemp(prefix="bookfmt-toc-"))
            pass1_pdf = (tmp_dir / "pass1.pdf") if tmp_dir else (out / "pdf" / "book.pdf")
            ok, err = make_pdf(html_path, pass1_pdf, browser)
            pages = techbook.page_numbers(me, chapters, pass1_pdf) if ok else {}
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            if pages:
                html_path = techbook.build_html(me, chapters, meta, ctx, html_dir, template_dir, pages)
                pass1_pdf = None   # 番号入りで作り直すので、1回目のPDFは使わない
            else:
                ctx.warn("目次のページ番号を取得できなかったため、目次にはページ番号を表示していません"
                         + (f"（PDF生成エラー: {err}）" if not ok else ""))
                pass1_pdf = pass1_pdf if ok else None
        elif fmts & {"pdf", "html"}:
            ctx.warn("Chrome / Edge が見つからないため、目次にページ番号を表示していません")
        if "html" in fmts:
            results.append(f"HTML+CSS : {html_dir / 'index.html'}（デザイン: {html_dir / techbook.SIZES[size]['css']} + {html_dir / 'book.css'}）")
    else:
        html_path = build_html(chapters, meta, ctx, html_dir)  # ch.toc を確定させる
        if "html" in fmts:
            results.append(f"HTML+CSS : {html_dir / 'index.html'}（スタイルは {html_dir / 'book.css'}）")
    if "md" in fmts:
        md_path = build_markdown(chapters, meta, ctx, out / "markdown")
        results.append(f"Markdown : {md_path}")
    if "docx" in fmts:
        word_path = build_word(chapters, meta, ctx, out / "word", browser)
        results.append(f"Word     : {word_path}")
    elif skip_word:
        ctx.warn("python-docx が無いため Word(.docx) は作成しませんでした（python -m pip install python-docx pillow で導入できます）")
    if "pdf" in fmts:
        if not browser:
            ctx.warn("Chrome / Edge が見つからないためPDFは作成できませんでした。"
                     f"{html_path} をブラウザで開き、印刷→「PDFに保存」（用紙サイズ={size}、余白=なし、背景のグラフィック=オン）で保存してください")
        else:
            ok, err = (True, "") if pass1_pdf else make_pdf(html_path, out / "pdf" / "book.pdf", browser)
            if ok:
                pages = count_pdf_pages(out / "pdf" / "book.pdf")
                results.append(f"PDF      : {out / 'pdf' / 'book.pdf'}" + (f"（約{pages}ページ）" if pages else ""))
            else:
                ctx.warn(f"PDF生成に失敗しました: {err}")
    if "html" not in fmts and "pdf" not in fmts:
        shutil.rmtree(html_dir, ignore_errors=True)  # md だけ欲しいときに html/ を残さない

    total_figs = stats["svg"] + stats["img"] + stats["missing"]
    notes = [f"- {k}: {n}箇所" if n else f"- {k}" for k, n in ctx.notes.items()]
    missing_lines = [f"- [{where}] {line}" for where, lines in ctx.missing.items() for line in lines]
    check = (["- ✅ 原稿の全行が出力に含まれていることを確認しました"] if not ctx.missing
             else ["- ❌ 原稿にあるのに出力で見つからない行があります。原稿は変更していません。出力を採用する前に確認してください:",
                   *missing_lines])
    report = [f"# 書籍フォーマット変換レポート", "",
              f"- 書名: {meta.title}", f"- 用紙サイズ: {size}", f"- 入力: {src_name}",
              f"- デザイン: {'format-template（' + techbook.SIZES[size]['css'] + '）' if techbook else 'classic（book.css）'}",
              f"- 章: {', '.join((c.label or c.title) for c in chapters)}",
              f"- 図: {total_figs}点（埋め込み済み {stats['svg'] + stats['img']} / 入稿待ち {stats['missing']}）",
              "", "## 内容チェック（原稿の削除・欠落がないか）", *check,
              "", "## 出力", *[f"- {r}" for r in results],
              "", "## 整理した内容（文字の追加・削除なし。構造のみ）", *(notes or ["- なし"]),
              "", "## 警告", *([f"- {w}" for w in ctx.warnings] or ["- なし"])]
    out.mkdir(parents=True, exist_ok=True)
    (out / "publish_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"{'❌' if ctx.missing else '✅'} 変換完了（{size} / {len(chapters)}章 / 入力: {src_name}）")
    if ctx.missing:
        total = sum(len(v) for v in ctx.missing.values())
        print(f"❌ 内容チェック失敗: 原稿の{total}行が出力で見つかりません（原稿は変更していません）")
        for where, lines in ctx.missing.items():
            for line in lines[:5]:
                print(f"   [{where}] {line[:70]}")
    else:
        print("✅ 内容チェック: 原稿の全行が出力に含まれています")
    for r in results:
        print("  " + r)
    print(f"  レポート : {out / 'publish_report.md'}")
    if ctx.notes:
        print("整理した内容（文字の追加・削除なし）:")
        for line in notes:
            print("  " + line)
    if ctx.warnings:
        print("⚠ 警告:")
        for w in ctx.warnings:
            print("  - " + w)
    return 4 if ctx.missing else 0


if __name__ == "__main__":
    sys.exit(main())
