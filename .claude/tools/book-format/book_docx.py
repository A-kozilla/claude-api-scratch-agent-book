# -*- coding: utf-8 -*-
"""
book_docx.py — Word(.docx) 出力（book_format.py の build_docx から呼ばれる）

book_format.py が原稿を分解した結果（Chapter / Seg）から、python-docx で直接 Word 文書を組み立てる。
HTML/PDF と同じルールを守る:
  * 縦置きA4/A5・上下左右15mm以上の余白（ノド側を広く: 見開き用の左右対称余白）
  * 表紙・章扉にはヘッダー/ページ番号なし、目次と本文ページにはページ番号あり（左=書名 / 右=章名のヘッダー）
  * POINT/NOTE/WARNING/COLUMN・図・表・コードブロックは、可能な限りページの途中で分割しない
  * 文字の追加・削除をしない（変換後に book_format.py が内容チェックを行う）

book_format.py 側の関数・定数は `bf`（book_format モジュール）経由で参照する（循環importを避けるため）。
"""
from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import markdown as mdlib
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound

ACCENT, INK, MUTED, RULE = "1D4F7A", "202124", "666D75", "D3D8DE"
SERIF, SANS, MONO, MONO_JA = "Yu Mincho", "Yu Gothic", "Consolas", "BIZ UDGothic"
CALLOUT = {  # 種別 → (線・ラベルの色, 背景色)   HTML/PDF の book.css と同じ配色
    "point": ("1D4F7A", "EEF3F8"), "tip": ("1E7A4A", "EEF7F1"), "note": ("5B6470", "F3F4F6"),
    "warning": ("B45309", "FFF5E8"), "danger": ("B42318", "FDEEEE"), "column": ("8A6D1D", "FBF6E9"),
    "step": ("1D4F7A", "FFFFFF"), "dialogue": ("5B6470", "F7FAFC"),
}
PANEL = {  # 見出しの文言で決まる特別な節: (背景色 | None, 線の色, 全周囲みか)
    "goals": ("EEF3F8", ACCENT, False), "summary": (None, ACCENT, True), "column": ("FBF6E9", "8A6D1D", False),
}
TWIP_PER_MM = 56.6929

# OOXML の子要素の並び順（順序が違うと Word が「破損」と判定することがあるため、順序付きで挿入する）
SEQ = {
    "pPr": ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
            "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
            "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid",
            "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
            "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"],
    "rPr": ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline", "shadow",
            "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing", "w", "kern",
            "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs",
            "em", "lang", "eastAsianLayout", "specVanish", "oMath"],
    "tcPr": ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
             "textDirection", "tcFitText", "vAlign", "hideMark"],
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW",
              "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
              "tblCaption", "tblDescription"],
    "trPr": ["cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter", "cantSplit", "trHeight",
             "tblHeader", "tblCellSpacing", "jc", "hidden"],
}


# ============================================================ OOXML の小さな部品

def put(parent, child) -> None:
    """child を parent の正しい位置に入れる（同名の既存要素は置き換える）。"""
    kind = parent.tag.split("}")[1]
    name = child.tag.split("}")[1]
    for old in parent.findall(qn(f"w:{name}")):
        parent.remove(old)
    seq = SEQ.get(kind)
    if seq and name in seq:
        later = {qn(f"w:{n}") for n in seq[seq.index(name) + 1:]}
        for i, el in enumerate(parent):
            if el.tag in later:
                parent.insert(i, child)
                return
    parent.append(child)


def el(tag: str, **attrs) -> OxmlElement:
    e = OxmlElement(f"w:{tag}")
    for k, v in attrs.items():
        e.set(qn(f"w:{k}"), str(v))
    return e


def border(tag: str, color: str, pt: float, style: str = "single", space: int = 0) -> OxmlElement:
    return el(tag, val=style, sz=max(2, int(round(pt * 8))), space=space, color=color)


def par_borders(par, **edges) -> None:
    """edges: top/bottom/left/right = (色, pt, 線種 省略可)"""
    bdr = el("pBdr")
    for side in ("top", "left", "bottom", "right"):
        if side in edges:
            c, pt, *rest = edges[side]
            bdr.append(border(side, c, pt, rest[0] if rest else "single", space=4))
    put(par._p.get_or_add_pPr(), bdr)
    # Word は段落の罫線を、本文領域より約0.5mm左へずらして、約0.6mm長く描く（実測）。左右のインデントで補って余白を守る
    par.paragraph_format.left_indent = Mm(0.5)
    par.paragraph_format.right_indent = Mm(0.6)


def par_shade(par, fill: str) -> None:
    put(par._p.get_or_add_pPr(), el("shd", val="clear", color="auto", fill=fill))


def set_fonts(rpr_owner_element, latin: str, east: str) -> None:
    """style / run の rPr に日英のフォントを設定（テーマフォント指定は解除して確実に効かせる）"""
    rpr = rpr_owner_element.get_or_add_rPr()
    f = el("rFonts", ascii=latin, hAnsi=latin, eastAsia=east, cs=latin)
    put(rpr, f)


def run_font(run, latin: str, east: str, size_pt: float | None = None, bold=None, italic=None,
             color: str | None = None) -> None:
    set_fonts(run._r, latin, east)
    if size_pt:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def run_shade(run, fill: str) -> None:
    put(run._r.get_or_add_rPr(), el("shd", val="clear", color="auto", fill=fill))


def cell_props(cell, fill: str | None = None, margins: tuple | None = None, borders: dict | None = None) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    if borders:
        b = el("tcBorders")
        for side in ("top", "left", "bottom", "right"):
            if side in borders:
                c, pt, *rest = borders[side]
                b.append(border(side, c, pt, rest[0] if rest else "single"))
            else:
                b.append(el(side, val="nil"))
        put(tcpr, b)
    if fill:
        put(tcpr, el("shd", val="clear", color="auto", fill=fill))
    if margins:  # (上, 右, 下, 左) mm
        m = el("tcMar")
        for side, v in zip(("top", "right", "bottom", "left"), margins):
            m.append(el(side, w=int(v * TWIP_PER_MM), type="dxa"))
        put(tcpr, m)


def table_setup(table, width_mm: float, col_mm: list[float] | None = None, borders: dict | None = None,
                indent_mm: float = 0) -> None:
    """indent_mm: 表を左右とも内側へ寄せる量。罫線は表の端の外側へ太さの半分はみ出して描かれるため、それを補う。"""
    tblpr = table._tbl.tblPr
    width_mm -= 2 * indent_mm   # 左右とも内側へ寄せる
    if indent_mm:
        put(tblpr, el("tblInd", w=int(indent_mm * TWIP_PER_MM), type="dxa"))
    put(tblpr, el("tblW", w=int(width_mm * TWIP_PER_MM), type="dxa"))
    put(tblpr, el("tblLayout", type="fixed"))
    b = el("tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        if borders and side in borders:
            c, pt = borders[side]
            b.append(border(side, c, pt))
        else:
            b.append(el(side, val="nil"))
    put(tblpr, b)
    # 表の既定のセル余白を0にする。既定（約1.9mm）のままだと、Word は表の左端を本文領域の外へ
    # 同じ量だけはみ出させ、指定した余白より狭くなる。セルの余白は各セルの tcMar で指定する。
    mar = el("tblCellMar")
    for side in ("top", "left", "bottom", "right"):
        mar.append(el(side, w=0, type="dxa"))
    put(tblpr, mar)
    cols = col_mm or [width_mm] * len(table.columns)
    for i, w in enumerate(cols):
        table.columns[i].width = Mm(w)
        for row in table.rows:
            row.cells[i].width = Mm(w)


def row_props(row, cant_split=True, header=False) -> None:
    trpr = row._tr.get_or_add_trPr()
    if cant_split:
        put(trpr, el("cantSplit"))
    if header:
        put(trpr, el("tblHeader"))


def keep_all(par, next_=True, lines=True) -> None:
    par.paragraph_format.keep_with_next = next_
    par.paragraph_format.keep_together = lines


def tiny(par, pt: float = 4) -> None:
    """表の前後の区切り用の段落: 高さをほぼ0にする（表同士がくっついて1つに結合されるのを防ぐ）"""
    pf = par.paragraph_format
    pf.space_before = pf.space_after = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(pt)


def add_bookmark(par, name: str, bid: int) -> None:
    start, end = el("bookmarkStart", id=bid, name=name), el("bookmarkEnd", id=bid)
    ppr = par._p.pPr
    par._p.insert(1 if ppr is not None else 0, start)
    par._p.append(end)


def add_link(par, text: str, *, url: str | None = None, anchor: str | None = None, color=ACCENT, size=None,
             fonts=None, bold=None) -> None:
    h = el("hyperlink", history=1)
    if url:
        h.set(qn("r:id"), par.part.relate_to(url, RT.HYPERLINK, is_external=True))
    if anchor:
        h.set(qn("w:anchor"), anchor)
    run = par.add_run(text)
    run_font(run, *(fonts or (SERIF, SERIF)), size_pt=size, bold=bold, color=color)
    if url:
        run.font.underline = True
    par._p.remove(run._r)
    h.append(run._r)
    par._p.append(h)


def add_page_field(par, size_pt: float, color: str) -> None:
    fld = el("fldSimple", instr=" PAGE ")
    r = el("r")
    rpr = el("rPr")
    rpr.append(el("rFonts", ascii=SANS, hAnsi=SANS, eastAsia=SANS))
    rpr.append(el("color", val=color))
    rpr.append(el("sz", val=int(size_pt * 2)))
    r.append(rpr)
    t = el("t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    par._p.append(fld)


# ============================================================ HTML（Markdown変換結果）を木にする

class Node:
    def __init__(self, tag: str, attrs=None):
        self.tag, self.attrs, self.children, self.text = tag, dict(attrs or []), [], ""


class TreeBuilder(HTMLParser):
    VOID = {"br", "hr", "img", "meta", "link", "input"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs)
        self.stack[-1].children.append(n)
        if tag not in self.VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        n = Node("#text")
        n.text = data
        self.stack[-1].children.append(n)


def parse_html(html: str) -> Node:
    tb = TreeBuilder()
    tb.feed(html)
    return tb.root


def node_text(n: Node) -> str:
    return n.text if n.tag == "#text" else "".join(node_text(c) for c in n.children)


# ============================================================ 本体

class Container:
    """文書本体・表のセルのどちらにも同じ呼び方で段落や表を足せるようにする薄いラッパー。"""

    def __init__(self, target, is_doc: bool, width_mm: float):
        self.target, self.is_doc, self.width, self._fresh = target, is_doc, width_mm, not is_doc

    def par(self, style=None):
        if self._fresh:  # セルには最初から空の段落が1つあるので、それを最初に使う
            self._fresh = False
            p = self.target.paragraphs[0]
            if style:
                p.style = style
            return p
        return self.target.add_paragraph(style=style)

    def table(self, rows: int, cols: int):
        self._fresh = False
        return self.target.add_table(rows=rows, cols=cols)

    def finish(self) -> None:
        if not self.is_doc:  # セル末尾の空段落は極小にする
            last = self.target.paragraphs[-1]
            if not last.text.strip() and not last._p.xpath(".//w:drawing"):
                tiny(last)


class DocxBuilder:
    def __init__(self, bf, chapters, meta, ctx, browser: str | None):
        self.bf, self.chapters, self.meta, self.ctx, self.browser = bf, chapters, meta, ctx, browser
        self.p = bf.PAPERS[ctx.size]
        self.text_w = self.p["w"] - self.p["inner"] - self.p["outer"]
        self.body_h_mm = self.p["h"] - self.p["top"] - self.p["bottom"]
        self.doc = Document()
        self.top = Container(self.doc, True, self.text_w)
        self._bid = 0
        self.prev_par = None
        self.tmp = Path(tempfile.mkdtemp(prefix="bookdocx-"))
        self.svg_cache: dict[str, Path | None] = {}
        self.style = get_style_by_name("friendly")
        self._tok_cache: dict = {}
        self.cur_w = self.text_w
        self.wide_cols = int((self.text_w - 8) / (self.p["code"] * 0.6 * 0.3528))

    # ---------------------------------------------------------- 文書・スタイル
    def bid(self) -> int:
        self._bid += 1
        return self._bid

    def setup(self) -> None:
        f, lh = self.p["font"], self.p["lh"]
        st = self.doc.styles
        n = st["Normal"]
        set_fonts(n.element, SERIF, SERIF)
        n.font.size, n.font.color.rgb = Pt(f), RGBColor.from_string(INK)
        pf = n.paragraph_format
        pf.line_spacing_rule, pf.line_spacing = WD_LINE_SPACING.EXACTLY, Pt(f * lh)
        pf.space_before, pf.space_after = Pt(0), Pt(f * 0.85)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        ppr = n.element.get_or_add_pPr()  # 禁則処理・日本語組版（行頭に「、。）」を置かない等）
        # 禁則処理は有効。一方、次の機能は無効にする（HTML/PDF/Markdownと見た目をそろえ、余白を守るため）:
        #   overflowPunct  … 行末の句読点を右余白へはみ出させる「ぶら下げ」
        #   topLinePunct   … 行頭の約物を詰めて左余白へはみ出させる処理
        #   autoSpaceDE/DN … 日本語と英数字の間に自動で空白を入れる
        for tag, val in (("kinsoku", 1), ("wordWrap", 1), ("overflowPunct", 0), ("topLinePunct", 0),
                         ("autoSpaceDE", 0), ("autoSpaceDN", 0)):
            put(ppr, el(tag, val=val))
        sizes = {1: f * 2.1, 2: f * 1.4, 3: f * 1.15, 4: f}
        for lvl, sz in sizes.items():
            h = st[f"Heading {lvl}"]
            set_fonts(h.element, SANS, SANS)
            rf = h.element.rPr.find(qn("w:rFonts"))
            for a in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
                rf.attrib.pop(qn(f"w:{a}"), None)
            h.font.size, h.font.bold = Pt(sz), True
            h.font.color.rgb = RGBColor.from_string(ACCENT if lvl == 4 else INK)
            hp = h.paragraph_format
            hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            hp.keep_with_next = hp.keep_together = True
            hp.line_spacing_rule, hp.line_spacing = WD_LINE_SPACING.AT_LEAST, Pt(sz * 1.35)
            hp.space_before = Pt({1: 0, 2: f * 2, 3: f * 1.6, 4: f * 1.3}[lvl])
            hp.space_after = Pt({1: 0, 2: f * .8, 3: f * .5, 4: f * .4}[lvl])
        core = self.doc.core_properties
        core.title, core.author, core.language = self.meta.title, self.meta.author or "", "ja-JP"
        s = self.doc.settings
        # 互換モードを Word 2013 以降（15）にする。既定の 14 だと、Word が表の左端を本文の余白線より外へずらす
        for cs in s.element.xpath(".//w:compatSetting[@w:name='compatibilityMode']"):
            cs.set(qn("w:val"), "15")
        s.odd_and_even_pages_header_footer = True  # 奇数=右ページ / 偶数=左ページで別のヘッダー
        mirror = el("mirrorMargins")               # 見開き用: 左右の余白を「ノド側/小口側」として扱う
        stops = {"writeProtection", "view", "zoom", "removePersonalInformation", "removeDateAndTime",
                 "doNotDisplayPageBoundaries", "displayBackgroundShape", "printPostScriptOverText",
                 "printFractionalCharacterWidth", "printFormsData", "embedTrueTypeFonts", "embedSystemFonts",
                 "saveSubsetFonts", "saveFormsData"}
        idx = 0
        for i, c in enumerate(s.element):
            if c.tag.split("}")[1] in stops:
                idx = i + 1
        s.element.insert(idx, mirror)

    def page(self, sec) -> None:
        p = self.p
        sec.orientation = WD_ORIENT.PORTRAIT
        sec.page_width, sec.page_height = Mm(p["w"]), Mm(p["h"])
        sec.top_margin, sec.bottom_margin = Mm(p["top"]), Mm(p["bottom"])
        sec.left_margin, sec.right_margin = Mm(p["inner"]), Mm(p["outer"])  # 左右対称余白では 左=ノド側 / 右=小口側
        sec.header_distance = sec.footer_distance = Mm(8)

    def new_section(self):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        tiny(self.doc.paragraphs[-1])   # セクション区切りを持つ空段落が改ページを誘発しないようにする
        self.page(sec)
        self.prev_par = None
        return sec

    def header_footer(self, sec, odd: str, even: str, number: bool) -> None:
        """odd=右ページ / even=左ページ。文字が空ならヘッダーなし。number=False ならページ番号なし。"""
        for a in ("header", "footer", "even_page_header", "even_page_footer"):
            getattr(sec, a).is_linked_to_previous = False
        for hf, text, align in ((sec.header, odd, WD_ALIGN_PARAGRAPH.RIGHT),
                                (sec.even_page_header, even, WD_ALIGN_PARAGRAPH.LEFT)):
            par = hf.paragraphs[0]
            par.alignment = align
            if text:
                run_font(par.add_run(text), SANS, SANS, 7, color="7B8590")
        for hf, align in ((sec.footer, WD_ALIGN_PARAGRAPH.RIGHT), (sec.even_page_footer, WD_ALIGN_PARAGRAPH.LEFT)):
            par = hf.paragraphs[0]
            par.alignment = align
            if number:
                add_page_field(par, 8, "55606B")

    # ---------------------------------------------------------- 表紙・目次・章扉
    def cover(self) -> None:
        sec = self.doc.sections[0]
        self.page(sec)
        m = self.meta
        d = self.doc
        first = d.add_paragraph()
        first.paragraph_format.space_before = Mm(self.p["h"] * 0.27)
        par_borders(first, top=(ACCENT, 3.0))
        first.paragraph_format.right_indent = Mm(self.text_w - 20)
        title = d.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.LEFT
        title.paragraph_format.space_before = Pt(18)
        run_font(title.add_run(m.title), SANS, SANS, self.p["font"] * 2.0, bold=True, color=ACCENT)
        title.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
        title.paragraph_format.line_spacing = Pt(self.p["font"] * 2.9)
        for text, size, bold, gap in ((m.subtitle, 1.15, False, 10), (m.author, 1.1, True, Mm(self.p["h"] * .12).pt),
                                      (m.date, .9, False, 4)):
            if text:
                par = d.add_paragraph()
                par.alignment = WD_ALIGN_PARAGRAPH.LEFT
                par.paragraph_format.space_before = Pt(gap)
                run_font(par.add_run(text), SANS, SANS, self.p["font"] * size, bold=bold,
                         color=INK if bold else MUTED)
        self.header_footer(sec, "", "", number=False)

    def toc(self) -> None:
        sec = self.new_section()
        self.header_footer(sec, self.meta.running, self.meta.running, number=True)
        d, f = self.doc, self.p["font"]
        t = d.add_paragraph()
        t.alignment = WD_ALIGN_PARAGRAPH.LEFT
        t.paragraph_format.space_after = Pt(f * 1.2)
        run_font(t.add_run("目次"), SANS, SANS, f * 1.7, bold=True)
        par_borders(t, bottom=(ACCENT, 1.5))
        for ch in self.chapters:
            par = d.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf = par.paragraph_format
            pf.space_before, pf.space_after, pf.keep_with_next = Pt(f * 1.0), Pt(f * .15), True
            if ch.label:
                pf.left_indent, pf.first_line_indent = Mm(16), Mm(-16)
                add_link(par, ch.label, anchor=self.anchor(ch.dom_id), color=ACCENT, size=f, fonts=(SANS, SANS), bold=True)
                par.add_run("\t")
                par.paragraph_format.tab_stops.add_tab_stop(Mm(16))
            add_link(par, ch.title, anchor=self.anchor(ch.dom_id), color=INK, size=f, fonts=(SANS, SANS), bold=True)
            for e in ch.toc:
                sp = d.add_paragraph()
                sp.alignment = WD_ALIGN_PARAGRAPH.LEFT
                spf = sp.paragraph_format
                spf.left_indent, spf.first_line_indent = Mm(16 + 12), Mm(-12)
                spf.space_before, spf.space_after = Pt(0), Pt(f * .1)
                sp.paragraph_format.tab_stops.add_tab_stop(Mm(16 + 12))
                if e["secno"]:
                    add_link(sp, e["secno"], anchor=self.anchor(e["id"]), color=ACCENT, size=f * .92,
                             fonts=(SANS, SANS), bold=True)
                    sp.add_run("\t")
                else:
                    spf.first_line_indent = Mm(0)
                    spf.left_indent = Mm(16 + 12)
                add_link(sp, e["title"], anchor=self.anchor(e["id"]), color=INK, size=f * .92, fonts=(SANS, SANS))

    @staticmethod
    def anchor(dom_id: str) -> str:
        return dom_id.replace("-", "_")   # ブックマーク名に使える文字（英数字と _）にする

    def chapter_opener(self, ch) -> None:
        sec = self.new_section()
        self.header_footer(sec, "", "", number=False)   # 章扉: ヘッダーもページ番号も出さない
        d, f = self.doc, self.p["font"]
        top_gap = Mm(self.p["h"] * 0.26)   # タイトルを紙面の上から約1/4の位置に置く
        if ch.label:
            lab = d.add_paragraph()
            lab.alignment = WD_ALIGN_PARAGRAPH.LEFT
            lab.paragraph_format.space_before = top_gap
            run_font(lab.add_run(ch.label), SANS, SANS, f * 1.25, bold=True, color=ACCENT)
            lab.paragraph_format.keep_with_next = True
        h = d.add_paragraph(style="Heading 1")
        h.add_run(ch.title)
        par_borders(h, top=(ACCENT, 1.5))
        h.paragraph_format.space_before = Pt(f * 0.9) if ch.label else top_gap
        add_bookmark(h, self.anchor(ch.dom_id), self.bid())

    # ---------------------------------------------------------- 内容
    def items_of(self, segs) -> list:
        """セグメント列 → [('node', HTML要素) | ('seg', 特殊セグメント)]（Markdown部分はHTML経由で要素に分解）"""
        bf, out = self.bf, []
        for s in segs:
            if s.kind == "md":
                md = mdlib.Markdown(extensions=["tables", "sane_lists"])
                root = parse_html(md.convert(bf.normalize_md(s.text)))
                for n in root.children:
                    if n.tag == "#text" and not n.text.strip():
                        continue
                    out.append(("node", n))
            else:
                out.append(("seg", s))
        return out

    def chapter_body(self, ch) -> None:
        self.bf_ctx_dir(ch)
        sec = self.new_section()
        running = f"{ch.label} {ch.title}".strip()
        self.header_footer(sec, running, self.meta.running, number=True)
        groups, cur = [], None
        for it in self.items_of(ch.segs):   # 見出し(##)ごとの節に分け、特別な節（学ぶこと・まとめ・コラム）は枠に入れる
            if it[0] == "node" and it[1].tag == "h2":
                cur = {"cls": self.bf.classify_h2(self._h2_plain(it[1])), "items": []}
                groups.append(cur)
            if cur is None:
                cur = {"cls": "", "items": []}
                groups.append(cur)
            cur["items"].append(it)
        for g in groups:   # 節の末尾の区切り線（---）は、次の見出しが区切りを担うので省く（HTML/PDFと同じ）
            while len(g["items"]) > 1 and g["items"][-1][0] == "node" and g["items"][-1][1].tag == "hr":
                g["items"].pop()
        counter = 0
        for g in groups:
            first = g["items"][0]
            bm = None
            if first[0] == "node" and first[1].tag == "h2":
                counter += 1
                bm = self.anchor(f"{ch.dom_id}-s{counter}")
            if g["cls"] in PANEL:
                self.panel(g["items"], g["cls"], bm)
            else:
                self.render_items(self.top, g["items"], bm)

    def bf_ctx_dir(self, ch) -> None:
        self.ctx.src_dir = ch.src.parent

    def _h2_plain(self, n: Node) -> str:
        return re.sub(r"^\d+(?:\.\d+)+[\s　]+", "", node_text(n)).strip()

    def panel(self, items, cls: str, bookmark: str | None) -> None:
        fill, color, box = PANEL[cls]
        self.gap(self.top)
        table = self.top.table(1, 1)
        table_setup(table, self.text_w, indent_mm=0.3)
        cell = table.cell(0, 0)
        cell_props(cell, fill=fill, margins=(1, 4, 1.5, 4),
                   borders={"top": (color, 2.0)} if not box else {s: (color, 0.8) for s in ("top", "left", "bottom", "right")})
        row_props(table.rows[0], cant_split=True)
        inner = Container(cell, False, self.text_w - 0.6 - 8.6)   # 表の内側 = 幅 − 左右の寄せ − セル余白
        self.render_items(inner, items, bookmark, in_panel=cls)
        inner.finish()
        tiny(self.doc.add_paragraph())
        self.prev_par = None

    def render_items(self, ctr: Container, items, bookmark=None, in_panel: str | None = None) -> None:
        for i, (kind, obj) in enumerate(items):
            if kind == "seg":
                self.render_seg(ctr, obj)
            else:
                self.render_node(ctr, obj, bookmark if (i == 0 and obj.tag == "h2") else None, in_panel)

    def keep_lead(self) -> None:
        """リード文（直前の短い段落）を、直後のコード・表・図と同じページにする"""
        pp = self.prev_par
        if pp is not None and len(pp.text) <= 160:
            pp.paragraph_format.keep_with_next = True

    # ---------- 特殊セグメント
    def render_seg(self, ctr: Container, s) -> None:
        if s.kind == "code":
            self.keep_lead()
            self.code(ctr, s)
        elif s.kind == "figure":
            self.keep_lead()
            self.figure(ctr, s.fig)
        elif s.kind in ("callout", "quote"):
            self.callout(ctr, s)
        self.prev_par = None

    def spacer(self, ctr: Container) -> None:
        if ctr.is_doc:
            tiny(ctr.par())
        else:   # セルの中では、入れ子の表の直後に Word が自動で足す空段落を区切りとして使う（二重に空けない）
            tiny(ctr.target.paragraphs[-1])

    def gap(self, ctr: Container) -> None:
        """表の前の間隔。Word は表を直前の段落にぴったりくっつけるため、小さな段落で隙間を作る。
        リード文→表の「同じページに置く」指定が途切れないよう keep_with_next にしておく。"""
        if ctr.is_doc:
            g = ctr.par()
            tiny(g, 5)
            g.paragraph_format.keep_with_next = True

    def code(self, ctr: Container, s) -> None:
        bf = self.bf
        fname, lname = bf.detect_filename(s.code), bf.lang_label(s.lang)
        lines = s.code.split("\n")
        rows = 2 if (fname or lname) else 1
        self.gap(ctr)
        t = ctr.table(rows, 1)
        table_setup(t, ctr.width, borders={k: ("C9D0D7", 0.6) for k in ("top", "left", "bottom", "right")},
                    indent_mm=0.3 if ctr.is_doc else 0)
        est_lines = sum(max(1, math.ceil(bf.display_width(l) / self.wide_cols)) for l in lines)
        est_mm = est_lines * self.p["code"] * 1.55 * 0.3528 + 8
        keep = est_mm <= self.body_h_mm * 0.9   # 1ページに収まるものは必ず収める
        if rows == 2:
            hc = t.cell(0, 0)
            cell_props(hc, fill="ECEFF2", margins=(.8, 2.5, .8, 2.5),
                       borders={"bottom": ("C9D0D7", 0.6), "top": ("C9D0D7", .6), "left": ("C9D0D7", .6), "right": ("C9D0D7", .6)})
            hp = hc.paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            hp.paragraph_format.space_after = Pt(0)
            hp.paragraph_format.line_spacing_rule, hp.paragraph_format.line_spacing = WD_LINE_SPACING.EXACTLY, Pt(self.p["code"] * 1.7)
            hp.paragraph_format.tab_stops.add_tab_stop(Mm(ctr.width - 0.6 - 5.2), WD_TAB_ALIGNMENT.RIGHT)  # 右揃え位置 = 表の内側の右端
            run_font(hp.add_run(fname), MONO, MONO_JA, self.p["code"] * 0.95, bold=True, color="4A525A")
            hp.add_run("\t")
            run_font(hp.add_run(lname), MONO, MONO_JA, self.p["code"] * 0.95, color=MUTED)
            keep_all(hp)
            row_props(t.rows[0], cant_split=True)
        body = t.cell(rows - 1, 0)
        cell_props(body, fill="F8F9FA", margins=(1.6, 2.5, 1.6, 2.5),
                   borders={k: ("C9D0D7", 0.6) for k in ("top", "left", "bottom", "right")})
        row_props(t.rows[rows - 1], cant_split=keep)
        lang = s.lang.lower()
        lexer = TextLexer()
        if lang not in ("", "text", "txt", "plaintext"):
            try:
                lexer = get_lexer_by_name(lang)
            except ClassNotFound:
                pass
        # トークンを行ごとに分けて、色付きの run にする
        per_line: list[list[tuple[str, dict]]] = [[]]
        for ttype, value in lex(s.code, lexer):
            attrs = self._tok(ttype)
            parts = value.split("\n")
            for k, part in enumerate(parts):
                if k:
                    per_line.append([])
                if part:
                    per_line[-1].append((part, attrs))
        for idx, runs in enumerate(per_line):
            if idx == 0:
                par = body.paragraphs[0]
            else:
                par = body.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf = par.paragraph_format
            pf.space_before = pf.space_after = Pt(0)
            pf.line_spacing_rule, pf.line_spacing = WD_LINE_SPACING.EXACTLY, Pt(self.p["code"] * 1.55)
            if keep and idx < len(per_line) - 1:
                pf.keep_with_next = True
            pf.widow_control = True
            if not runs:
                run_font(par.add_run(""), MONO, MONO_JA, self.p["code"])
            for text, a in runs:
                run_font(par.add_run(text), MONO, MONO_JA, self.p["code"], bold=a.get("bold"),
                         italic=a.get("italic"), color=a.get("color"))
        self.spacer(ctr)

    def _tok(self, ttype) -> dict:
        if ttype not in self._tok_cache:
            st = self.style.style_for_token(ttype)
            self._tok_cache[ttype] = {"color": (st.get("color") or "").upper() or None,
                                      "bold": True if st.get("bold") else None,
                                      "italic": True if st.get("italic") else None}
        return self._tok_cache[ttype]

    def callout(self, ctr: Container, s) -> None:
        if s.kind == "callout":
            color, fill = CALLOUT[s.ckind]
            borders = {"left": (color, 3.0)}
        else:
            color, fill, borders = MUTED, None, {"left": (RULE, 2.5)}
        self.gap(ctr)
        t = ctr.table(1, 1)
        ind = 0.55 if ctr.is_doc else 0
        table_setup(t, ctr.width, indent_mm=ind)
        cell = t.cell(0, 0)
        cell_props(cell, fill=fill, margins=(1.6, 3, 1.2, 3.5), borders=borders)
        body_items = self.items_of(s.body)
        approx = sum(len(node_text(o)) if k == "node" else len(getattr(o, "code", "")) + 200 for k, o in body_items)
        row_props(t.rows[0], cant_split=approx <= 1200)
        inner = Container(cell, False, ctr.width - 2 * ind - 3 - 3.5 - 0.6)   # 表の内側 = 幅 − 寄せ − セル余白(左右)
        heading = self.bf.callout_heading(s) if s.kind == "callout" else ""
        if heading:  # ラベル（原稿のまま。見出し付きなら「POINT: 見出し」）は太字・色付き。本文の直前に置く
            lp = inner.par()
            lp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            lp.paragraph_format.space_after = Pt(self.p["font"] * .2)
            run_font(lp.add_run(heading), SANS, SANS, self.p["font"] * .9, bold=True, color=color)
            keep_all(lp)
        self.render_items(inner, body_items)
        inner.finish()
        self.spacer(ctr)

    # ---------- 図
    def figure(self, ctr: Container, fig) -> None:
        cap_txt = f"{fig.label} {fig.title}".strip()
        png = None
        if fig.svg:
            png = self.rasterize(fig)
        elif fig.img:
            png = Path(fig.img)
        if png is None:
            self.gap(ctr)
            t = ctr.table(1, 1)
            table_setup(t, ctr.width, borders={k: ("B9C1C9", 1.0) for k in ("top", "left", "bottom", "right")},
                        indent_mm=0.5 if ctr.is_doc else 0)
            c = t.cell(0, 0)
            cell_props(c, fill="FAFBFC", margins=(5, 3, 5, 3),
                       borders={k: ("B9C1C9", 1.0, "dashed") for k in ("top", "left", "bottom", "right")})
            row_props(t.rows[0], cant_split=True)
            lines = [(f"{fig.label}: {fig.title}", True)]
            if fig.summary:
                lines.append((fig.summary, False))
            lines.append((f"{fig.kind} — 入稿待ち" if fig.kind else "入稿待ち", False))
            inner = Container(c, False, ctr.width - 1 - 6)
            for text, bold in lines:
                p = inner.par()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(2)
                run_font(p.add_run(text), SANS, SANS, self.p["font"] * (1 if bold else .85), bold=bold, color="7B838C")
            cp = ctr.par()
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cp.paragraph_format.space_before = Pt(4)
            run_font(cp.add_run(cap_txt), SANS, SANS, self.p["font"] * .85, color=MUTED)
            run_font(cp.add_run("（入稿待ち）"), SANS, SANS, self.p["font"] * .85, color="B45309")
            self.prev_par = None
            return
        pp = ctr.par()
        pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pp.paragraph_format.space_before = Pt(self.p["font"] * .6)
        pp.paragraph_format.space_after = Pt(self.p["font"] * .3)
        pp.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        self.picture(pp, png, ctr.width)
        keep_all(pp)
        cp = ctr.par()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_after = Pt(self.p["font"] * .9)
        run_font(cp.add_run(fig.label), SANS, SANS, self.p["font"] * .85, bold=True, color=INK)
        run_font(cp.add_run(" " + fig.title if fig.title else ""), SANS, SANS, self.p["font"] * .85, color=MUTED)
        self.prev_par = None

    def picture(self, par, path: Path, max_w_mm: float) -> None:
        run = par.add_run()
        pic = run.add_picture(str(path))
        w, h = pic.width, pic.height
        max_w, max_h = Mm(max_w_mm), Mm(self.body_h_mm - 30)
        k = min(1.0, max_w / w, max_h / h)
        pic.width, pic.height = int(w * k), int(h * k)

    def rasterize(self, fig) -> Path | None:
        """SVG は Word で確実に表示できないため、Chrome/Edge で画像（PNG）にして埋め込む。"""
        key = fig.num
        if key in self.svg_cache:
            return self.svg_cache[key]
        self.svg_cache[key] = None
        if not self.browser:
            self.ctx.warn(f"{fig.label}: Chrome/Edge が無いため、SVGの図をWordに埋め込めず「入稿待ち」の枠にしました")
            return None
        svg = fig.svg
        head = re.match(r"<svg\b[^>]*>", svg, re.S).group(0)
        vb = re.search(r'viewBox="\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)', head)
        w = float(vb.group(1)) if vb else float(re.search(r'\bwidth="([\d.]+)', head).group(1)) if re.search(r'\bwidth="([\d.]+)', head) else 600.0
        h = float(vb.group(2)) if vb else float(re.search(r'\bheight="([\d.]+)', head).group(1)) if re.search(r'\bheight="([\d.]+)', head) else 300.0
        w, h = int(math.ceil(w)), int(math.ceil(h))
        newhead = re.sub(r'\s(?:width|height)="[^"]*"', "", head)
        newhead = newhead.replace("<svg", f'<svg width="{w}" height="{h}"', 1)
        if "xmlns=" not in newhead:
            newhead = newhead.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
        html = (f'<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#fff">'
                f'{svg.replace(head, newhead, 1)}</body></html>')
        src, out = self.tmp / f"{fig.file_stem}.html", self.tmp / f"{fig.file_stem}.png"
        src.write_text(html, encoding="utf-8")
        scale = 3
        prof = tempfile.mkdtemp(prefix="bookdocx-chrome-")
        try:
            subprocess.run([self.browser, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--hide-scrollbars",
                            f"--force-device-scale-factor={scale}", f"--window-size={max(w, 900)},{max(h, 700)}",
                            f"--screenshot={out}", src.as_uri()],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        except subprocess.TimeoutExpired:
            pass
        finally:
            shutil.rmtree(prof, ignore_errors=True)
        if not out.is_file():
            self.ctx.warn(f"{fig.label}: SVGを画像化できなかったため、Wordでは「入稿待ち」の枠にしました")
            return None
        try:  # ウィンドウが図より大きい場合の余白を切り落とす（Pillow がある場合）
            from PIL import Image
            with Image.open(out) as im:
                im.crop((0, 0, min(im.width, w * scale), min(im.height, h * scale))).save(out)
        except Exception:
            pass
        self.svg_cache[key] = out
        return out

    # ---------- HTML要素 → Word
    def render_node(self, ctr: Container, n: Node, bookmark: str | None, in_panel: str | None) -> None:
        t = n.tag
        f = self.p["font"]
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lvl = min(4, max(2, int(t[1])))
            if in_panel and t == "h2":
                par = ctr.par()
                par.alignment = WD_ALIGN_PARAGRAPH.LEFT
                par.paragraph_format.space_before, par.paragraph_format.space_after = Pt(f * .6), Pt(f * .4)
                run_font(par.add_run(node_text(n).strip()), SANS, SANS, f * 1.1, bold=True,
                         color="6F5612" if in_panel == "column" else INK)
                par.paragraph_format.keep_with_next = True
            else:
                par = ctr.par(style=f"Heading {lvl}") if ctr.is_doc else ctr.par()
                if ctr.is_doc:
                    par.add_run(node_text(n).strip())
                    if lvl == 2:
                        par_borders(par, bottom=(ACCENT, .8))
                else:
                    run_font(par.add_run(node_text(n).strip()), SANS, SANS, f * 1.1, bold=True)
                    par.paragraph_format.keep_with_next = True
            if bookmark:
                add_bookmark(par, bookmark, self.bid())
            self.prev_par = None
        elif t == "p":
            self.paragraph(ctr, n.children)
        elif t in ("ul", "ol"):
            self.list(ctr, n, 0)
            self.prev_par = None
        elif t == "table":
            self.keep_lead()
            self.table(ctr, n)
            self.prev_par = None
        elif t == "hr":
            par = ctr.par()
            tiny(par)
            par.paragraph_format.space_before = par.paragraph_format.space_after = Pt(f * .8)
            par_borders(par, bottom=(RULE, .6))
            self.prev_par = None
        elif t == "blockquote":
            for c in n.children:
                self.render_node(ctr, c, None, in_panel)
        elif t == "#text":
            if n.text.strip():
                self.paragraph(ctr, [n])
        elif t in ("div", "section", "figure", "details"):
            for c in n.children:
                self.render_node(ctr, c, None, in_panel)
        elif t in ("img", "a", "strong", "em", "code", "span", "b", "i", "kbd", "br"):
            self.paragraph(ctr, [n])
        # コメント・未知のブロック要素は表示しない（HTML/PDFと同じ扱い）

    def paragraph(self, ctr: Container, nodes, indent_mm: float = 0, hang_mm: float = 0, marker: str = "") -> None:
        par = ctr.par()
        pf = par.paragraph_format
        if not ctr.is_doc:
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.space_after = Pt(self.p["font"] * .5)
        if indent_mm or hang_mm:
            pf.left_indent, pf.first_line_indent = Mm(indent_mm + hang_mm), Mm(-hang_mm) if hang_mm else Mm(0)
            if hang_mm:
                pf.tab_stops.add_tab_stop(Mm(indent_mm + hang_mm))
        if marker:
            r = par.add_run(marker + "\t")
            run_font(r, SERIF, SERIF, color=ACCENT)
        self.cur_w = ctr.width
        self.inline(par, nodes, {})
        self.prev_par = par

    def list(self, ctr: Container, n: Node, level: int) -> None:
        ordered = n.tag == "ol"
        num = int(n.attrs.get("start", 1)) if ordered else 0
        for li in (c for c in n.children if c.tag == "li"):
            inline_nodes = [c for c in li.children if c.tag not in ("ul", "ol", "p", "table")
                            and not (c.tag == "#text" and not c.text.strip())]
            paras = [c for c in li.children if c.tag == "p"]
            if paras and not inline_nodes:       # 「疎なリスト」<li><p>…</p></li>
                inline_nodes, paras = paras[0].children, paras[1:]
            marker = f"{num}." if ordered else ("•" if level == 0 else "–")
            self.paragraph(ctr, inline_nodes, indent_mm=level * 5, hang_mm=5.5 if ordered else 4.5, marker=marker)
            self.prev_par.paragraph_format.space_after = Pt(self.p["font"] * .25)
            num += 1
            for c in li.children:
                if c.tag in ("ul", "ol"):
                    self.list(ctr, c, level + 1)
                elif c.tag == "p" and c in paras:
                    self.paragraph(ctr, c.children, indent_mm=level * 5 + (5.5 if ordered else 4.5))
                elif c.tag == "table":
                    self.table(ctr, c)

    def table(self, ctr: Container, n: Node) -> None:
        rows: list[list[tuple[bool, Node, str]]] = []
        for tr in self._find(n, "tr"):
            cells = []
            for c in tr.children:
                if c.tag in ("th", "td"):
                    al = re.search(r"text-align:\s*(left|center|right)", c.attrs.get("style", ""))
                    cells.append((c.tag == "th", c, al.group(1) if al else "left"))
            if cells:
                rows.append(cells)
        if not rows:
            return
        ncols = max(len(r) for r in rows)
        width = ctr.width
        weights = [max(6, *(len(node_text(r[i][1])) if i < len(r) else 0 for r in rows)) for i in range(ncols)]
        weights = [min(w, 40) for w in weights]
        total = sum(weights)
        cols = [max(width * 0.1, width * w / total) for w in weights]
        scale = width / sum(cols)
        cols = [c * scale for c in cols]
        self.gap(ctr)
        t = ctr.table(len(rows), ncols)
        table_setup(t, width, cols, borders={"bottom": (RULE, .5), "insideH": (RULE, .5)})
        f = self.p["font"] * .92
        # 表の高さを推定し、1ページに収まるものは途中で分割しない。ページより長い表だけ分割を許し、見出し行を繰り返す
        line_mm = f * self.p["lh"] * .95 * 0.3528
        est = 0.0
        for r in rows:
            lines = 1
            for ci, (_, node, _) in enumerate(r):
                em_per_line = max(1.0, cols[ci] - 4) / (f * 0.3528)   # セルの内側に入る全角文字数
                lines = max(lines, math.ceil(self.bf.display_width(node_text(node)) / 2 / em_per_line))
            est += lines * line_mm + 2.1
        keep = est <= self.body_h_mm * 0.92
        for ri, r in enumerate(rows):
            row_props(t.rows[ri], cant_split=True, header=(ri == 0 and r[0][0]))
            for ci in range(ncols):
                cell = t.cell(ri, ci)
                if ci >= len(r):
                    continue
                is_h, node, al = r[ci]
                cell_props(cell, fill="ECEFF2" if is_h else None, margins=(1, 2, 1, 2),
                           borders={"bottom": (ACCENT, 1.2) if is_h else (RULE, .5)})
                par = cell.paragraphs[0]
                par.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER,
                                 "right": WD_ALIGN_PARAGRAPH.RIGHT}[al]
                pf = par.paragraph_format
                pf.space_after = Pt(0)
                pf.line_spacing_rule, pf.line_spacing = WD_LINE_SPACING.EXACTLY, Pt(f * self.p["lh"] * .95)
                self.inline(par, node.children, {"bold": True} if is_h else {}, size=f, fonts=(SANS, SANS))
                if keep and ri < len(rows) - 1:
                    pf.keep_with_next = True
        self.spacer(ctr)

    def _find(self, n: Node, tag: str):
        for c in n.children:
            if c.tag == tag:
                yield c
            else:
                yield from self._find(c, tag)

    # ---------- インライン（太字・斜体・コード・リンク・画像）
    def inline(self, par, nodes, fmt: dict, size: float | None = None, fonts=None) -> None:
        bf = self.bf
        fonts = fonts or (SERIF, SERIF)
        for n in nodes:
            if n.tag == "#text":
                text = re.sub(rf"(?<=[{bf.CJK}])\n(?=[{bf.CJK}])", "", n.text).replace("\n", " ")
                if not text:
                    continue
                run = par.add_run(text)
                if fmt.get("code"):
                    run_font(run, MONO, MONO_JA, (size or self.p["font"]) * .88, bold=fmt.get("bold"), italic=fmt.get("italic"))
                    run_shade(run, "EFF1F4")
                else:
                    run_font(run, *fonts, size_pt=size, bold=fmt.get("bold"), italic=fmt.get("italic"), color=fmt.get("color"))
            elif n.tag in ("strong", "b"):
                self.inline(par, n.children, {**fmt, "bold": True}, size, fonts)
            elif n.tag in ("em", "i"):
                self.inline(par, n.children, {**fmt, "italic": True}, size, fonts)
            elif n.tag in ("code", "kbd"):
                self.inline(par, n.children, {**fmt, "code": True}, size, fonts)
            elif n.tag == "br":
                par.add_run().add_break()
            elif n.tag == "a":
                href = n.attrs.get("href", "")
                text = node_text(n)
                if re.match(r"^(https?:|mailto:)", href) and text:
                    add_link(par, text, url=href, size=size, fonts=fonts)
                else:
                    self.inline(par, n.children, {**fmt, "color": ACCENT}, size, fonts)
            elif n.tag == "img":
                src = n.attrs.get("src", "")
                p = (self.ctx.src_dir / unquote(src)).resolve()
                if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
                    par.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE   # 固定行間だと画像が切れる
                    par.alignment = WD_ALIGN_PARAGRAPH.LEFT                          # 両端揃えだと直前の行が間延びする
                    self.picture(par, p, self.cur_w)
                else:
                    self.ctx.warn(f"Word: 画像を埋め込めませんでした（{src}）")
            else:
                self.inline(par, n.children, fmt, size, fonts)

    # ---------------------------------------------------------- 全体
    def build(self, out: Path) -> Path:
        self.setup()
        self.cover()
        self.toc()
        for ch in self.chapters:
            self.chapter_opener(ch)
            self.chapter_body(ch)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(out))
        shutil.rmtree(self.tmp, ignore_errors=True)
        return out


def docx_text_blob(path: Path, bf) -> str:
    """生成した .docx から本文の文字を文書順に取り出し、内容チェック用に正規化する。"""
    doc = Document(str(path))
    return bf.norm("".join(t.text or "" for t in doc.element.body.iter(qn("w:t"))))


def build_docx(bf, chapters, meta, ctx, out_path: Path, browser: str | None) -> Path:
    return DocxBuilder(bf, chapters, meta, ctx, browser).build(out_path)
