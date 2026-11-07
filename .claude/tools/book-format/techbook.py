# -*- coding: utf-8 -*-
"""
techbook.py — format-template/ のデザインで書籍HTMLを組み立てる（book_format.py --theme techbook から呼ばれる）

  A4: format-template/techbook-a4.html の構造 + style-a4.css
  A5: format-template/techbook-a5.html の構造 + style-a5.css

- デザインの元はテンプレートのCSSそのもの（出力先にコピーして読み込む）。テンプレートのCSSを編集すれば出力に反映される。
- テンプレートにない要素（リスト・インラインコード・まとめ枠・TIP/DANGER など）と、Chrome で印刷するための補正は
  techbook-adapter.css に置き、テンプレートのCSSの後に読み込む。
- 柱（右ページの章名）: テンプレートは string-set（paged.js 用）を使うが Chrome は未対応のため、章ごとの名前付きページで出す。
- 目次のページ番号: 1回目のPDFのしおり（アウトライン）から各見出しのページを読み取り、2回目の出力で書き込む。
"""
from __future__ import annotations

import html as htmllib
import re
import shutil
import zlib
from pathlib import Path

import markdown as mdlib
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

TOOL_DIR = Path(__file__).resolve().parent
ADAPTER_CSS = TOOL_DIR / "techbook-adapter.css"
DEFAULT_TEMPLATE_DIR = TOOL_DIR.parents[2] / "format-template"

# css=テンプレートのCSS / small=章扉・枠内の小さい文字 / en=目次見出し横の「CONTENTS」の文字サイズ
SIZES = {
    "A4": dict(w=210, h=297, css="style-a4.css", small="9pt", en="10pt", author="8.5pt"),
    "A5": dict(w=148, h=210, css="style-a5.css", small="7.8pt", en="8pt", author="7pt"),
}
# コード行の桁数警告用（テンプレートの @page の左右余白と .code-body の文字サイズ）
PAPERS = {
    "A4": dict(w=210, h=297, inner=18, outer=18, code=8.5),
    "A5": dict(w=148, h=210, inner=14, outer=14, code=7.5),
}
TEACHER_NAMES = ("先生", "講師", "筆者", "著者", "メンター", "先輩", "博士", "編集部")
STUDENT_NAMES = ("生徒", "読者", "受講者", "学生", "新人", "後輩", "初心者")
PYGMENTS_STYLE = "one-dark"   # テンプレートのコードブロックは暗い背景（#1a202c）


def esc(s: str) -> str:
    return htmllib.escape(s, quote=True)


def md_inline(text: str) -> str:
    """1行ぶんの Markdown（太字・コード・リンク）を <p> なしの HTML にする。"""
    html = mdlib.markdown(text.strip()).strip()
    html = re.sub(r"</p>\s*<p>", "<br />", html)
    return re.sub(r"^<p>(.*)</p>$", r"\1", html, flags=re.S)


def title_html(line: str) -> str:
    """表紙の書名1行。**強調** の部分はテンプレートの .highlight（色違い）にする。"""
    parts = re.split(r"\*\*(.+?)\*\*", line)
    return "".join(f'<span class="highlight">{esc(p)}</span>' if i % 2 else esc(p) for i, p in enumerate(parts))


def split_first_list(html: str) -> tuple[str, str, str]:
    """最上位（囲み記事の外）にある最初のリストで HTML を (前, リスト, 後) に分ける。リストが無ければ (全体, "", "")。"""
    for m in re.finditer(r"<(ul|ol)\b[^>]*>", html):
        pre = html[:m.start()]
        if pre.count("<div") != pre.count("</div>"):
            continue
        depth = 0
        for t in re.finditer(r"<(/?)(?:ul|ol)\b[^>]*>", html[m.start():]):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                end = m.start() + t.end()
                return html[:m.start()], html[m.start():end], html[end:]
    return html, "", ""


def check_list(lst: str) -> str:
    """リストの項目にテンプレートの ✔（.goal-item / .goal-check）を付ける。入れ子のリストはそのまま。"""
    lst = re.sub(r"^<(ul|ol)\b[^>]*>", r'<\1 class="check-list">', lst)
    depth, out, pos = 0, [], 0
    for t in re.finditer(r"<(/?)(ul|ol|li)\b[^>]*>", lst):
        out.append(lst[pos:t.end()])
        pos = t.end()
        tag, closing = t.group(2), t.group(1)
        if tag in ("ul", "ol"):
            depth += -1 if closing else 1
        elif not closing and depth == 1:
            out[-1] = out[-1][:-len(t.group(0))] + '<li class="goal-item"><span class="goal-check">✔</span>'
    out.append(lst[pos:])
    return "".join(out)


def make_renderer(bf):
    """book_format.HtmlRenderer を継承し、テンプレートのクラス構造で出力するレンダラを作る。"""

    class TechbookRenderer(bf.HtmlRenderer):
        # ---- 部品
        def code_html(self, s) -> str:
            lang = s.lang.lower()
            lexer = TextLexer()
            if lang not in ("text", "txt", "plaintext", ""):
                try:
                    lexer = get_lexer_by_name(lang)
                except ClassNotFound:
                    pass
            body = highlight(s.code, lexer, self.formatter).rstrip("\n")
            fname, lname = bf.detect_filename(s.code), bf.lang_label(s.lang)
            head = ""
            if fname or lname:
                tag = f'<span class="file-tag">{esc(lname)}</span>' if lname else ""
                head = f'<div class="code-header sans">{tag}{esc(fname)}</div>'
            return f'<div class="code-block code-container">{head}<pre class="code-body"><code>{body}</code></pre></div>'

        def figure_html(self, fig) -> str:
            cap = (f'<figcaption class="figure-caption sans"><span class="caption-num">{esc(fig.label)}:</span>'
                   f'{esc(fig.title)}</figcaption>')
            if fig.svg:
                body = f'<div class="figure-frame">{bf.scope_svg_ids(fig.svg, fig.dom_id + "-")}</div>'
            elif fig.img:
                src = self.assets.add_file(fig.img)
                body = f'<div class="figure-frame"><img src="{esc(src)}" alt="{esc(fig.label + ": " + fig.title)}"></div>'
            else:
                kind = f"{esc(fig.kind)} — " if fig.kind else ""
                desc = f'<div class="ph-desc">{esc(fig.summary)}</div>' if fig.summary else ""  # 原稿の「内容の要点」を残す
                body = (f'<div class="figure-frame figure-missing sans"><div class="ph-title">{esc(fig.label)}: {esc(fig.title)}</div>'
                        f'{desc}<div class="ph-note">{kind}入稿待ち</div></div>')
                cap = cap.replace("</figcaption>", '<span class="figure-pending">（入稿待ち）</span></figcaption>')
            return f'<figure class="doc-figure" id="{fig.dom_id}">{body}{cap}</figure>'

        def dialogue_html(self, s) -> str:
            utter: list[list[str]] = []
            for line in s.text.split("\n"):
                m = bf.SPEAKER_RE.match(line.strip())
                if m:
                    utter.append([m.group("name").strip(), m.group("text")])
                elif line.strip() and utter:
                    utter[-1][1] += "\n" + line.strip()
                elif line.strip():
                    utter.append(["", line.strip()])
            order: list[str] = []
            rows = []
            for name, text in utter:
                badge = ""
                if name:
                    if name not in order:
                        order.append(name)
                    if any(k in name for k in TEACHER_NAMES):
                        cls = "avatar-teacher"
                    elif any(k in name for k in STUDENT_NAMES):
                        cls = "avatar-student"
                    else:   # 名前で決まらなければ、登場順に 生徒色 → 先生色 → …
                        cls = ("avatar-student", "avatar-teacher")[order.index(name) % 2]
                    badge = f'<span class="avatar-badge {cls}">{esc(name)}</span>'
                rows.append(f'<div class="dialogue-line">{badge}{md_inline(text)}</div>')
            return f'<!--dlg--><div class="dialogue-box sans">{"".join(rows)}</div><!--/dlg-->'

        def special_html(self, s) -> str:
            if s.kind in ("code", "figure"):
                return super().special_html(s)
            if s.kind == "callout" and s.ckind == "dialogue":
                return self.dialogue_html(s)
            inner = self.inline(s.body)
            if s.kind == "callout" and s.ckind == "step":
                desc = f'<div class="step-desc">{inner}</div>' if inner.strip() else ""
                return (f'<div class="step-card sans"><span class="step-badge">{esc(s.label)}</span>'
                        f'<strong>{md_inline(s.title)}</strong>{desc}</div>')
            if s.kind == "callout":
                box = "box-column" if s.ckind == "column" else f"doc-box box-{s.ckind}"
                title = f'<span class="doc-box-title"><span class="box-tag">{esc(s.label)}</span>{md_inline(s.title)}</span>'
                return f'<div class="{box} sans">{title}<div class="doc-box-body">{inner}</div></div>'
            return f'<blockquote class="doc-quote">{inner}</blockquote>'

        # ---- 章（章扉ページ + 本文）
        @staticmethod
        def lead_box(html: str) -> str:
            """章扉の概要枠。会話ボックスは枠に入れず、そのまま並べる。"""
            out = []
            for chunk in re.split(r"(<!--dlg-->.*?<!--/dlg-->)", html, flags=re.S):
                if chunk.startswith("<!--dlg-->"):
                    out.append(chunk)
                elif bf.strip_tags(chunk).strip() or "<img" in chunk or "<svg" in chunk:
                    out.append(f'<div class="divider-lead-box sans">{chunk}</div>')
            return "".join(out)

        def goals_card(self, h2: str, body: str, card: str) -> str:
            before, lst, after = split_first_list(body)
            box = f'<div class="{card} sans">{h2}{before}{check_list(lst) if lst else ""}</div>'
            return box + (self.lead_box(after) if lst else "")

        def chapter_html(self, ch) -> str:
            self.ctx.src_dir = ch.src.parent
            ch.toc = []
            html = self.inline(ch.segs)
            html = html.replace("<table>", '<table class="tech-table sans">')
            counter = [0]

            def head(m: re.Match) -> str:
                level, inner = int(m.group(1)), m.group(2)
                if level == 3:
                    return f'<h3 class="sub-h3 sans">{inner}</h3>'
                if level == 4:
                    return f'<h4 class="sub-h4 sans">{inner}</h4>'
                counter[0] += 1
                hid = f"{ch.dom_id}-s{counter[0]}"
                nm = re.match(r"^(\d+(?:\.\d+)+)[\s　]+(.*)$", inner, re.S)
                secno, rest = (nm.group(1), nm.group(2)) if nm else ("", inner)
                plain = bf.strip_tags(rest).strip()
                cls = bf.classify_h2(plain)
                if cls not in ("goals", "overview"):
                    ch.toc.append(dict(id=hid, secno=secno, title=plain, cls=cls))
                return f'<h2 id="{hid}" data-cls="{cls}" data-secno="{esc(secno)}">{rest}</h2>'

            html = re.sub(r"<h([2-4])>(.*?)</h\1>", head, html, flags=re.S)
            html = re.sub(r"<hr\s*/?>", '<hr class="rule">', html)

            divider, body, opening = [], [], True
            for idx, part in enumerate(re.split(r'(?=<h2 id=")', html)):
                part = re.sub(r'(\s*<hr class="rule">\s*)+$', "", part)  # 節の末尾の区切り線は、次の見出しが区切りを担うので省く
                if not part.strip():
                    continue
                hm = re.match(r'<h2 id="([^"]+)" data-cls="([^"]*)" data-secno="([^"]*)">(.*?)</h2>(.*)$', part, re.S)
                if not hm:   # 章見出しと最初の ## の間の文章 → 章扉の概要枠
                    (divider if opening else body).append(self.lead_box(part) if opening else part)
                    continue
                hid, cls, secno, rest, content = hm.groups()
                if cls == "goals":
                    block = self.goals_card(f'<h2 id="{hid}" class="goals-card-title">{rest}</h2>', content,
                                            "divider-goals-card")
                elif cls == "overview":   # 概要の枠。会話ボックスは枠の外（直後）に出す
                    dlg = re.findall(r"<!--dlg-->.*?<!--/dlg-->", content, flags=re.S)
                    text = re.sub(r"<!--dlg-->.*?<!--/dlg-->", "", content, flags=re.S)
                    block = (f'<div class="divider-lead-box sans"><h2 id="{hid}" class="lead-box-title">{rest}</h2>'
                             f"{text}</div>" + "".join(dlg))
                elif cls == "summary":
                    h2 = f'<h2 id="{hid}" class="sec-h2 sans">{rest}</h2>'
                    before, lst, after = split_first_list(content)
                    block = h2 + (f'<div class="summary-card sans">{before}{check_list(lst)}</div>{after}' if lst else content)
                elif cls == "column":
                    cm = re.match(r"^(コラム|Column|COLUMN)\s*[:：]?\s*(.*)$", rest, re.S)
                    tag, title = (cm.group(1), cm.group(2)) if cm else ("COLUMN", rest)
                    block = (f'<section class="box-column col-section sans"><h2 id="{hid}" class="doc-box-title">'
                             f'<span class="box-tag">{tag}</span>{title}</h2><div class="doc-box-body">{content}</div></section>')
                else:
                    badge = f'<span class="sec-h2-badge">{secno}</span>' if secno else ""
                    block = f'<h2 id="{hid}" class="sec-h2 sans">{badge}{rest}</h2>{content}'
                if opening and cls in ("goals", "overview"):
                    divider.append(block)
                else:
                    opening = False
                    body.append(block)

            badges = ""
            if ch.label:
                badges += f'<span class="divider-badge-chap">{esc(ch.label)}</span>'
            if ch.en_title:   # 英字ラベルは原稿の # EN-TITLE: があるときだけ出す
                en = f"CHAPTER {ch.num:02d} · {ch.en_title}" if ch.label else ch.en_title
                # 装飾なので本文の文字としては持たず、CSS（attr）で表示する（「第1章」と章タイトルの間に文字を挟まない）
                badges += f'<span class="divider-badge-en" data-en="{esc(en)}"></span>'
            tags = "".join(f'<span class="concept-tag">#{esc(t)}</span>' for t in ch.tags)
            header = (f'<div class="divider-header sans">' + (f"<div>{badges}</div>" if badges else "")
                      + f'<h1 class="divider-title">{esc(ch.title)}</h1>'
                      + (f'<div class="concept-tags">{tags}</div>' if tags else "") + "</div>")
            page = f"ch{ch.num}"
            out = (f'<section class="chapter-divider-page" id="{ch.dom_id}" style="page:{page}">{header}'
                   + "".join(divider) + "</section>")
            if body:
                out += f'<section class="body-section" style="page:{page}">' + "".join(body) + "</section>"
            return out.replace("<!--dlg-->", "").replace("<!--/dlg-->", "")

    return TechbookRenderer


# ============================================================ 表紙・目次・ページ設定

def cover_html(meta) -> str:
    top = []
    if meta.series:
        top.append(f'<div class="cover-series-badge sans">{esc(meta.series)}</div>')
    if meta.cover_subtitle_lines:
        top.append('<div class="cover-subtitle sans">' + "<br />".join(esc(s) for s in meta.cover_subtitle_lines) + "</div>")
    top.append('<h1 class="cover-main-title sans">' + "<br />".join(title_html(l) for l in meta.title_lines) + "</h1>")
    if meta.description:
        top.append('<p class="sans cover-desc no-indent">' + "<br />".join(esc(d) for d in meta.description) + "</p>")
    parts = [f'<div class="cover-top">{"".join(top)}</div>']
    if meta.features:
        parts.append('<div class="cover-middle sans">'
                     + "".join(f'<div class="cover-feature-item">{esc(f)}</div>' for f in meta.features) + "</div>")
    else:
        parts.append("<div></div>")   # 下部の著者欄を紙面の下に置くための空き
    bottom = ""
    if meta.author or meta.date:
        label = '<span class="cover-author-label">著者</span>' if meta.author else ""
        date = f'<span class="cover-date">{esc(meta.date)}</span>' if meta.date else ""
        names = "<br />".join(esc(a) for a in meta.cover_author_lines)   # AUTHOR を複数行書くと行ごとに改行
        bottom += f'<div class="cover-author">{label}{names}{date}</div>'
    if meta.publisher:
        bottom += f'<div class="cover-publisher">{esc(meta.publisher)}</div>'
    if bottom:
        parts.append(f'<div class="cover-bottom sans">{bottom}</div>')
    return f'<section class="cover-page" style="page:cover">{"".join(parts)}</section>'


def toc_html(chapters, pages: dict | None, size: str) -> str:
    def page(key: str, cls: str) -> str:
        n = pages.get(key) if pages else None
        if n:
            return f'<span class="{cls}">P. {n}</span>'
        return f'<span class="{cls} toc-page-pending">P. 000</span>'   # 2回目の出力で番号が入っても行の幅が変わらないよう場所を取っておく

    out = [f'<section class="toc-section" style="page:front"><div class="toc-header sans">'
           f'<div class="toc-main-title">目次</div><span class="toc-en" style="font-size:{SIZES[size]["en"]}">CONTENTS</span></div>']
    for ch in chapters:
        num = f'<span class="toc-chap-num">{esc(ch.label)}</span>' if ch.label else ""
        out.append(f'<div class="toc-chapter-block sans"><a class="toc-chap-row" href="#{ch.dom_id}">{num}'
                   f'<span class="toc-chap-name">{esc(ch.title)}</span>{page(ch.dom_id, "toc-chap-page")}</a>')
        subs = [t for t in ch.toc if t["title"]]
        if subs:
            out.append('<div class="toc-sec-list">')
            for t in subs:
                no = f'<span class="toc-sec-num">{esc(t["secno"])}</span>' if t["secno"] else ""
                out.append(f'<a class="toc-sec-item toc-{t["cls"] or "sec"}" href="#{t["id"]}">{no}'
                           f'<span>{esc(t["title"])}</span>{page(t["id"], "toc-sec-page")}</a>')
            out.append("</div>")
        out.append("</div>")
    out.append("</section>")
    return "".join(out)


def page_css(bf, size: str, meta, chapters) -> str:
    s = SIZES[size]
    css = [f"/* ---- 自動生成: 用紙 {size} のページ設定・柱（ヘッダー） ---- */",
           f":root {{ --page-w: {s['w']}mm; --page-h: {s['h']}mm; --small-fs: {s['small']}; --author-fs: {s['author']}; }}",
           f'@page {{ size: {size} portrait; @top-left {{ content: "{bf.css_str(meta.running)}"; }} }}',
           "@page cover { margin: 0; @top-left { content: none } @top-right { content: none } @bottom-center { content: none } }",
           "@page front { @top-right { content: none } }"]
    for ch in chapters:   # 右上の柱＝章タイトル（テンプレートの string(chapter-title) の代わり）
        css.append(f'@page ch{ch.num} {{ @top-right {{ content: "{bf.css_str(ch.title)}"; }} }}')
    return "\n".join(css) + "\n"


# ============================================================ 組み立て

def build_html(bf, chapters, meta, ctx, out_dir: Path, template_dir: Path, pages: dict | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    size = ctx.size
    tpl_css = template_dir / SIZES[size]["css"]
    if not tpl_css.is_file():
        raise FileNotFoundError(f"デザインのCSSが見つかりません: {tpl_css}")
    assets = bf.Assets(out_dir)
    r = make_renderer(bf)(ctx, assets)
    chapter_html = [r.chapter_html(ch) for ch in chapters]
    for ch, html in zip(chapters, chapter_html):  # 原稿の文字が1行も欠けていないか確認する
        miss = bf.find_missing(ch.raw, bf.norm(bf.strip_tags(html)))
        key = f"HTML: {ch.label or ch.title}"
        if miss:
            ctx.missing[key] = miss
        else:
            ctx.missing.pop(key, None)

    shutil.copyfile(tpl_css, out_dir / tpl_css.name)   # テンプレートのCSSは手を加えずにそのまま使う
    pyg = HtmlFormatter(style=PYGMENTS_STYLE).get_style_defs(".code-body")
    (out_dir / "book.css").write_text(
        '@charset "UTF-8";\n' + page_css(bf, size, meta, chapters)
        + "\n/* ---- テンプレートにない要素・Chrome印刷用の補正（techbook-adapter.css） ---- */\n"
        + ADAPTER_CSS.read_text(encoding="utf-8")
        + "\n/* ---- シンタックスハイライト（Pygments） ---- */\n" + pyg
        + "\n.code-body, .code-body pre { background: transparent !important; }\n", encoding="utf-8")

    doc = (f'<!DOCTYPE html>\n<html lang="ja" data-theme="light">\n<head>\n<meta charset="utf-8" />\n'
           f'<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
           f"<title>{esc(meta.title)}</title>\n"
           f'<!-- デザイン: format-template/{tpl_css.name}（コピー） + book.css（補正・ページ設定） -->\n'
           f'<link rel="stylesheet" href="{tpl_css.name}" />\n<link rel="stylesheet" href="book.css" />\n</head>\n'
           f'<body class="techbook size-{size}">\n{cover_html(meta)}\n{toc_html(chapters, pages, size)}\n'
           + "\n".join(chapter_html) + "\n</body>\n</html>\n")
    (out_dir / "index.html").write_text(doc, encoding="utf-8")
    return out_dir / "index.html"


# ============================================================ PDF のしおりから見出しのページ番号を読む

def _pdf_objects(data: bytes) -> dict[int, bytes]:
    objs: dict[int, bytes] = {}
    for m in re.finditer(rb"(?<![\d])(\d+)\s+0\s+obj\b(.*?)\bendobj", data, re.S):
        objs[int(m.group(1))] = m.group(2)
    for body in list(objs.values()):   # 圧縮されたオブジェクトストリーム（/ObjStm）も展開する
        if b"/ObjStm" not in body:
            continue
        sm = re.search(rb"stream\r?\n(.*?)\r?\n?endstream", body, re.S)
        first = re.search(rb"/First\s+(\d+)", body)
        if not sm or not first:
            continue
        try:
            raw = zlib.decompress(sm.group(1))
        except zlib.error:
            continue
        head = raw[:int(first.group(1))].split()
        offs = [(int(head[i]), int(head[i + 1])) for i in range(0, len(head) - 1, 2)]
        for k, (num, off) in enumerate(offs):
            end = offs[k + 1][1] if k + 1 < len(offs) else len(raw) - int(first.group(1))
            objs.setdefault(num, raw[int(first.group(1)) + off:int(first.group(1)) + end])
    return objs


def _pdf_string(raw: bytes) -> str:
    raw = raw.strip()
    if raw.startswith(b"<"):
        b = bytes.fromhex(re.sub(rb"[^0-9A-Fa-f]", b"", raw[1:-1]).decode())
    else:
        s = raw[1:-1]
        s = re.sub(rb"\\([0-7]{1,3})", lambda m: bytes([int(m.group(1), 8) & 0xFF]), s)
        s = re.sub(rb"\\(.)", lambda m: {b"n": b"\n", b"r": b"\r", b"t": b"\t"}.get(m.group(1), m.group(1)), s, flags=re.S)
        b = s
    if b.startswith(b"\xfe\xff"):
        return b[2:].decode("utf-16-be", errors="replace")
    return b.decode("latin-1")


def pdf_outline(pdf_path: Path) -> list[tuple[str, int]]:
    """PDFのしおりを文書順に (見出しの文字列, ページ番号(1始まり)) で返す。読めなければ空リスト。"""
    try:
        objs = _pdf_objects(pdf_path.read_bytes())
        cat = next(b for b in objs.values() if re.search(rb"/Type\s*/Catalog", b))
        order: list[int] = []

        def walk_pages(n: int, depth: int = 0) -> None:
            body = objs.get(n, b"")
            kids = re.search(rb"/Kids\s*\[([^\]]*)\]", body)
            if kids and depth < 50:
                for k in re.findall(rb"(\d+)\s+0\s+R", kids.group(1)):
                    walk_pages(int(k), depth + 1)
            else:
                order.append(n)
        walk_pages(int(re.search(rb"/Pages\s+(\d+)\s+0\s+R", cat).group(1)))
        page_no = {n: i + 1 for i, n in enumerate(order)}
        om = re.search(rb"/Outlines\s+(\d+)\s+0\s+R", cat)
        if not om:
            return []
        items: list[tuple[str, int]] = []

        def ref(body: bytes, key: bytes) -> int | None:
            m = re.search(rb"/" + key + rb"\s+(\d+)\s+0\s+R", body)
            return int(m.group(1)) if m else None

        def walk_items(n: int | None, depth: int = 0) -> None:
            seen = 0
            while n is not None and seen < 10000 and depth < 20:
                body = objs.get(n, b"")
                tm = re.search(rb"/Title\s*(<[0-9A-Fa-f\s]*>|\((?:\\.|[^\\)])*\))", body, re.S)
                dm = re.search(rb"/(?:Dest|D)\s*\[\s*(\d+)\s+0\s+R", body)
                if tm and dm and int(dm.group(1)) in page_no:
                    items.append((_pdf_string(tm.group(1)), page_no[int(dm.group(1))]))
                walk_items(ref(body, b"First"), depth + 1)
                n = ref(body, b"Next")
                seen += 1
        walk_items(ref(objs[int(om.group(1))], b"First"))
        return items
    except Exception:
        return []


def page_numbers(bf, chapters, pdf_path: Path) -> dict[str, int]:
    """1回目のPDFのしおりと章・節の見出しを文書順に照合し、{DOM id: ページ番号} を返す。"""
    items = [(bf.norm(t), p) for t, p in pdf_outline(pdf_path)]
    pages: dict[str, int] = {}
    i = 0
    for ch in chapters:
        j = next((k for k in range(i, len(items)) if items[k][0] == bf.norm(ch.title)), None)
        if j is None:
            continue
        pages[ch.dom_id], i = items[j][1], j + 1
        for t in ch.toc:
            key = bf.norm(t["secno"] + t["title"])
            j = next((k for k in range(i, len(items)) if items[k][0] == key), None)
            if j is not None:
                pages[t["id"]], i = items[j][1], j + 1
    return pages
