#!/usr/bin/env python3
"""Build the book's Markdown and HTML reading editions."""
from pathlib import Path
import argparse
import html
import re
from urllib.parse import unquote

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "资料证明/引用资料与事实核验.md"
MD = MarkdownIt("commonmark", {"html": True}).enable("table")
PARTS = sorted((ROOT / "正文").glob("*.md"))
SOURCE_PATTERN = (
    r'<a id="source-(\d+)"></a>\s*\n'
    r'### (?:\[cite:\d+\]|\d+\.) (.*?)\n(.*?)(?=\n<a id=|\n## |\Z)'
)


def format_markdown():
    """Give repository readers readable citations and stable chapter anchors."""
    chapter = 0
    for path in PARTS:
        text = path.read_text()
        text = re.sub(
            r"\[cite:(\d+)\]",
            lambda m: f"[{m[1]}](../资料证明/引用资料与事实核验.md#source-{m[1]})",
            text,
        )
        lines = text.splitlines()
        output = []
        for line in lines:
            if re.match(r"^## 第.+章", line):
                chapter += 1
                anchor = f'<a id="chapter-{chapter}"></a>'
                if not any(anchor == value for value in output[-3:]):
                    output.extend([anchor, ""])
            output.append(line)
        path.write_text("\n".join(output) + "\n")
    proof = PROOF.read_text()
    proof = re.sub(r"^### \[cite:(\d+)\] ", r"### \1. ", proof, flags=re.M)
    proof = re.sub(r"\[cite:(\d+)\]", lambda m: f"[{m[1]}](#source-{m[1]})", proof)
    proof = proof.replace(
        "正文中的 `[cite:N]` 对应下列编号。",
        "正文中的引用数字对应下列编号。",
    )
    PROOF.write_text(proof)


def build():
    sources = {}
    for match in re.finditer(SOURCE_PATTERN, PROOF.read_text(), re.S):
        number, title, body = match.groups()
        sources[int(number)] = {
            "title": title,
            "body": body,
            "urls": re.findall(r"<(https?://[^>]+)>", body),
        }
    assert sorted(sources) == list(range(1, 44)), "Expected 43 source entries"
    contents, combined, toc = [], [], []
    chapter_number = 0
    for part_number, path in enumerate(PARTS):
        text = path.read_text().split("\n", 2)[2]
        text = re.sub(r"\n---\n\n参考资料：.*", "", text, flags=re.S).strip()
        combined.append(text)
        render_text = re.sub(r'<a id="chapter-\d+"></a>\s*\n', "", text)
        tokens = MD.parse(render_text)
        for index, token in enumerate(tokens):
            if token.type == "html_block" and re.fullmatch(
                r'<a id="chapter-\d+"></a>\s*', token.content
            ):
                token.content = ""
            if token.type != "heading_open":
                continue
            title = tokens[index + 1].content
            if token.tag == "h1":
                token.tag = tokens[index + 2].tag = "h2"
                anchor = f"part-{part_number}"
                token.attrSet("id", anchor)
                toc.append((1, anchor, title))
            elif token.tag == "h2":
                token.tag = tokens[index + 2].tag = "h3"
                if re.match(r"^第.+章", title):
                    chapter_number += 1
                    anchor = f"chapter-{chapter_number}"
                else:
                    anchor = f"appendix-{len([x for x in toc if x[1].startswith('appendix-')]) + 1}"
                token.attrSet("id", anchor)
                toc.append((2, anchor, title))
            else:
                token.tag = tokens[index + 2].tag = "h4"
                token.attrSet("class", "scene-break")
        rendered = MD.renderer.render(tokens, MD.options, {})
        def citation_link(match):
            destination, label = match.groups()
            decoded = unquote(destination)
            citation = re.fullmatch(
                r"\.\./资料证明/引用资料与事实核验.md#source-(\d+)", decoded
            )
            if citation and label.isdigit():
                number = citation[1]
                return (
                    f'<sup><a href="#cite-{number}" aria-label="资料{number}">'
                    f'[{number}]</a></sup>'
                )
            if decoded == "../资料证明/引用资料与事实核验.md":
                return f'<a href="#proof">{label}</a>'
            return match[0]

        rendered = re.sub(r'<a href="([^"]+)">([^<]+)</a>', citation_link, rendered)
        rendered = re.sub(
            r"<table>(.*?)</table>",
            r'<div class="table-wrap"><table>\1</table></div>',
            rendered,
            flags=re.S,
        )
        contents.append(f'<section class="book-part">{rendered}</section>')
    assert chapter_number == 30, "Expected 30 chapters"
    rights = (
        "© 2026 yjd953 账号运营者。保留所有权利。免费供在线阅读；"
        "其他使用按许可及适用法律执行。"
    )
    manuscript = (
        "# 流量与筹码：孙宇晨与加密时代\n\n"
        "> 一部以公开资料为骨架的传记小说。\n\n"
        "六部三十章 · 资料截止 2026 年 10 月 11 日\n\n"
        + rights
        + "\n\n"
        + "\n\n---\n\n".join(
            re.sub(r"^(#{1,3}) ", r"\1# ", text, flags=re.M) for text in combined
        )
    )
    manuscript = manuscript.replace("../资料证明/", "资料证明/")
    manuscript += (
        "\n\n---\n\n## 资料证明\n\n"
        "[完整来源与核验说明](资料证明/引用资料与事实核验.md)\n\n"
        "[版权声明](COPYRIGHT.md) · [许可](LICENSE)\n"
    )
    (ROOT / "流量与筹码-全书.md").write_text(manuscript)
    toc_html = "\n".join(
        f'<a class="toc-level-{level}" href="#{anchor}">{html.escape(title)}</a>'
        for level, anchor, title in toc
    )
    source_html = []
    for number, source in sorted(sources.items()):
        urls = "".join(
            f'<a class="src-url" href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(url)}</a>'
            for url in source["urls"]
        )
        body = MD.render(source["body"])
        body = re.sub(r'href="#source-(\d+)"', r'href="#cite-\1"', body)
        source_html.append(
            f'<li id="cite-{number}"><span class="src-title">{html.escape(source["title"])}</span>'
            f'{urls}<details><summary>来源说明</summary>{body}</details></li>'
        )
    styles = """
@font-face{font-family:'Crimson Pro';src:url('./_shared/fonts/CrimsonPro-Regular.ttf') format('truetype');font-display:swap}
@font-face{font-family:'DM Mono';src:url('./_shared/fonts/DMMono-Regular.ttf') format('truetype');font-display:swap}
:root{--bg:#f7f5ef;--bg2:#ebe8df;--ink:#24231f;--muted:#66645d;--rule:#d4d0c5;--accent:#a43729;--accent2:#55534d;--font:'Crimson Pro','Songti SC','STSong','SimSun',serif;--ui:system-ui,-apple-system,'PingFang SC',sans-serif;--mono:'DM Mono',monospace;--body-size:19px;--max:660px}
:root.night{--bg:#1b1b19;--bg2:#262624;--ink:#e7e4dc;--muted:#a9a69e;--rule:#494740;--accent:#e29686;--accent2:#b5b1a8}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:85px}body{margin:0;color:var(--ink);background:var(--bg);font-family:var(--font);font-size:var(--body-size);line-height:2}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}button{font:inherit;cursor:pointer;color:var(--ink);background:var(--bg);border:1px solid var(--rule);border-radius:3px;padding:6px 11px}button:hover{background:var(--bg2)}button:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.toolbar{position:fixed;top:0;right:0;left:250px;height:56px;z-index:4;border-bottom:1px solid var(--rule);background:var(--bg);display:flex;align-items:center;justify-content:space-between;padding:0 28px;font:13px var(--ui);gap:12px}.tools{display:flex;gap:6px}.current{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:55%}.menu-toggle{display:none}
.toc{position:fixed;inset:0 auto 0 0;width:250px;padding:32px 22px;overflow:auto;border-right:1px solid var(--rule);z-index:6;background:var(--bg);font:13px/1.7 var(--ui)}.toc .brand{font-family:var(--font);font-size:25px;letter-spacing:3px;padding-bottom:24px;border-bottom:1px solid var(--rule);margin-bottom:24px}.toc a{display:block;color:var(--muted);padding:6px 0}.toc .toc-level-1{margin-top:18px;color:var(--ink);font-weight:600}.toc .toc-level-2{padding-left:12px;font-size:12px}.toc a.active{color:var(--accent)}.toc-close{display:none}.toc-footer{margin-top:30px;padding-top:18px;border-top:1px solid var(--rule)}
.page{margin-left:250px;padding:80px 44px 100px}.page>header,.page>main,.page>footer{max-width:var(--max);margin:auto}.cover{min-height:calc(100vh - 150px);display:flex;flex-direction:column;justify-content:center;padding:80px 0}.cover h1{font-size:clamp(48px,6.4vw,80px);line-height:1.2;letter-spacing:6px;font-weight:600;margin:0}.cover .subtitle{font-size:24px;letter-spacing:2px;margin:22px 0 12px}.cover .description{max-width:31em;font-size:17px;color:var(--muted);line-height:1.9}.cover .meta{font:12px/2 var(--ui);color:var(--muted);border-top:1px solid var(--rule);padding-top:24px;margin-top:40px}.start{display:inline-block;align-self:flex-start;border-bottom:1px solid var(--accent);margin-top:24px;font:14px var(--ui);padding-bottom:6px}
.book-part{margin-top:110px}h2{font-size:36px;line-height:1.5;font-weight:600;margin:0 0 32px;border-top:1px solid var(--accent);padding-top:35px;letter-spacing:2px}h3{font-size:27px;line-height:1.65;margin:70px 0 30px;font-weight:600}h4.scene-break{font-family:var(--ui);font-size:12px;font-weight:400;color:var(--muted);margin:36px 0 28px;text-align:center;letter-spacing:5px}p{margin:0 0 1.2em;text-align:justify;text-justify:inter-ideograph}blockquote{margin:0 0 40px;padding:2px 0 2px 20px;border-left:2px solid var(--rule);color:var(--muted);font-size:17px}blockquote p{margin:0}strong{font-weight:700}hr{border:0;border-top:1px solid var(--rule);margin:50px 0}sup{line-height:0;white-space:nowrap}sup a{color:var(--accent);font:10px var(--ui);padding-left:2px}
.table-wrap{overflow-x:auto;overflow-y:auto;max-height:600px;margin:25px 0 45px;border-top:1px solid var(--rule)}table{border-collapse:collapse;width:100%;font:14px/1.8 var(--ui)}th,td{text-align:left;border-bottom:1px solid var(--rule);padding:12px 10px;vertical-align:top}th{font-weight:600;background:var(--bg2)}ul,ol{padding-left:1.4em}li{margin-bottom:.6em}
footer{border-top:1px solid var(--accent);padding-top:45px;margin-top:120px!important;font-family:var(--ui)}footer h2{border:0;padding-top:0;font-family:var(--font)}footer .sources ol{padding-left:1.2rem;font-size:14px;color:var(--muted)}footer .sources li{margin-bottom:30px;overflow-wrap:break-word;word-break:break-all;scroll-margin-top:85px}footer .src-title{color:var(--ink);word-break:normal;font-weight:600}footer .src-url{display:block;margin-top:5px;font-size:12px;color:var(--accent);word-break:break-all}footer details{margin-top:10px}footer summary{color:var(--muted);font-size:12px;cursor:pointer}footer details p,footer details li{text-align:left;font-size:13px;line-height:1.85;font-weight:400}footer details ul{padding-left:16px}.sources-intro{font-size:14px;color:var(--muted)}.back-top{position:fixed;right:24px;bottom:24px;font:12px var(--ui);padding:10px 14px;border:1px solid var(--rule);background:var(--bg)}
.legal-section{font:14px/1.9 var(--ui);margin-top:80px;border-top:1px solid var(--rule);padding-top:35px}.legal-section h2{font-size:27px}.legal-section p{text-align:left}.print-notice{display:none}
@media(max-width:980px){.toc{transform:translateX(-100%);transition:transform .2s}.toc.open{transform:translateX(0)}.toc-close{display:block;margin-bottom:18px;font:12px var(--ui)}.toolbar{left:0;padding:0 15px}.menu-toggle{display:inline-block}.current{max-width:40%;font-size:12px}.page{margin-left:0;padding:75px 24px 80px}.cover{min-height:80vh;padding:65px 0}.cover h1{font-size:54px}.cover .subtitle{font-size:20px}table{min-width:580px}h2{font-size:30px}h3{font-size:25px}.back-top{right:12px;bottom:12px}}
@media(max-width:480px){.page{padding-left:20px;padding-right:20px}.cover h1{font-size:47px;letter-spacing:3px}.cover .subtitle{font-size:18px;letter-spacing:1px}.tools button{padding:5px 7px}.current{display:none}.cover .meta{font-size:11px}.book-part{margin-top:80px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.toc{transition:none}}
@media print{body>.toc,body>.toolbar,body>.page,body>.back-top{display:none!important}.print-notice{display:block!important;font:14pt/1.8 var(--ui);padding:30mm;color:var(--ink);background:var(--bg)}}
"""
    copyright_html = (
        '<h2>版权与使用声明</h2><p>© 2026 yjd953 账号运营者。保留所有权利。</p>'
        "<p>本书免费供在线阅读。未经明确书面许可，不授予主动长期保存、打印、转载、改编或售卖的权利。"
        "法定例外、必要技术缓存及平台内权限按许可执行。</p>"
        '<p>完整条款见 <a href="../LICENSE">许可正文</a>、'
        '<a href="../COPYRIGHT.md">版权声明</a>及 '
        '<a href="../THIRD_PARTY_NOTICES.md">第三方权利说明</a>。</p>'
    )
    output = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="流量与筹码：孙宇晨与加密时代。从惠州考场到全球市场，从巴菲特饭桌到特朗普牌桌。"><meta name="copyright" content="© 2026 yjd953 账号运营者。保留所有权利。"><meta name="robots" content="noarchive"><link rel="license" href="../LICENSE"><title>流量与筹码 · 孙宇晨与加密时代</title><style>{styles}</style></head>
<body><aside class="toc" id="toc"><button class="toc-close" id="close-menu">关闭目录</button><div class="brand">流量与筹码</div><nav aria-label="章节目录">{toc_html}</nav><div class="toc-footer"><a href="#proof">资料证明 · {len(sources)} 项</a><a href="#copyright">版权与许可</a></div></aside>
<div class="toolbar"><button class="menu-toggle" id="open-menu" aria-expanded="false" aria-controls="toc">目录</button><span class="current" id="current">流量与筹码</span><div class="tools"><button id="smaller" aria-label="缩小字号">A−</button><button id="larger" aria-label="放大字号">A＋</button><button id="theme" aria-pressed="false">夜读</button></div></div>
<article class="page"><header class="cover" id="top"><h1>流量<br>与筹码</h1><p class="subtitle">孙宇晨与加密时代</p><p class="description">从惠州考场到全球市场，从巴菲特饭桌到特朗普牌桌。一部以公开资料为骨架的传记小说。</p><div class="meta">六部 · 三十章<br>资料截止 2026 年 10 月 11 日</div><a class="start" href="#part-0">开始阅读 →</a></header><main>{''.join(contents)}</main><footer id="proof"><div class="sources"><h2>资料证明</h2><p class="sources-intro">点击正文引用数字即可跳到对应来源。原文链接与来源说明收录如下。</p><ol>{''.join(source_html)}</ol></div><section class="legal-section" id="copyright">{copyright_html}</section></footer></article>
<section class="print-notice">本书仅许可在线阅读。未经权利人书面许可，不授予打印或复制书稿的权利；法定例外另行判断。© 2026 yjd953 账号运营者。完整条款见 LICENSE。</section>
<a class="back-top" href="#top">回到封面 ↑</a><script src="./_shared/js/echarts.min.js"></script><script src="./assets/reader.js?v=20261011-1"></script></body></html>"""
    (ROOT / "阅读版/阅读版.html").write_text(output)
    root_output = output.replace("./_shared/", "./阅读版/_shared/")
    root_output = root_output.replace("./assets/", "./阅读版/assets/")
    root_output = root_output.replace('href="../', 'href="')
    (ROOT / "index.html").write_text(root_output)
    print(
        {
            "chapters": chapter_number,
            "sources": len(sources),
            "body_hanzi": sum(
                sum(
                    len(re.findall(r"[\u3400-\u9fff]", child.content))
                    for child in token.children or []
                    if child.type == "text"
                )
                for text in combined[:7]
                for token in MD.parse(text)
                if token.type == "inline"
            ),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--format-markdown", action="store_true")
    args = parser.parse_args()
    if args.format_markdown:
        format_markdown()
    build()
