# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4"]
# ///
"""Migra una guía HTML de Atlas (guia/<x>-guia.html) a lecciones Markdown de Starlight.

Uso:
    uv run tools/migrate_guide.py guia/datos-guia.html datos

Genera site/src/content/docs/<slug>/NN-<id>.md, una lección por <section class="block">.
No sobrescribe archivos existentes (ya pueden tener quiz y práctica escritos a mano);
usa --force para regenerar.
"""

import re
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent


def pandoc(html: str) -> str:
    out = subprocess.run(
        ["pandoc", "-f", "html", "-t", "gfm-raw_html", "--wrap=none"],
        input=html, capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def transform(section, soup) -> tuple[str, dict[str, str]]:
    """Reescribe las clases propias de Atlas a HTML semántico que pandoc entiende."""
    asides: dict[str, str] = {}

    for tag in section.select(".sec-num, h2"):
        tag.decompose()

    # "por qué importa" y notas -> asides de Starlight (se insertan tras pandoc)
    for el in section.select(".why, .note"):
        kind = "tip" if "why" in el["class"] else "note"
        label_el = el.find("b") if kind == "tip" else el.find(class_="label")
        label = label_el.get_text(" ", strip=True) if label_el else ""
        if label_el:
            label_el.decompose()
        key = f"ASIDE{len(asides)}X"
        body = pandoc(el.decode_contents() if kind == "note" else f"<p>{el.decode_contents()}</p>")
        title = f"[{label[0].upper() + label[1:]}]" if label else ""
        asides[key] = f":::{kind}{title}\n{body}\n:::"
        p = soup.new_tag("p")
        p.string = key
        el.replace_with(p)

    # término de un concepto -> h3
    for term in section.select("p.term"):
        term.name = "h3"
        term.attrs = {}

    for h4 in section.select(".stage h4"):
        h4.name = "h3"

    # diagramas ASCII -> bloque de código sin lenguaje
    for d in section.select(".diagram"):
        pre = soup.new_tag("pre")
        code = soup.new_tag("code", attrs={"class": "language-text"})
        code.string = d.get_text()
        pre.append(code)
        d.replace_with(pre)

    # código con resaltado manual (<pre><span ...>) -> texto plano, pandoc lo cerca
    for pre in section.select("pre"):
        if pre.select_one("code.language-text"):
            continue
        text = pre.get_text()
        pre.clear()
        # ponytail: heurística python/sql; si una guía trae otros lenguajes, marcar a mano
        lang = "python" if re.search(r"^\s*(import|from \w+ import|def )|\bpd\.|\bpl\.", text, re.M) else "sql"
        code = soup.new_tag("code", attrs={"class": f"language-{lang}"})
        code.string = text
        pre.append(code)

    # libros del currículo -> lista
    for stage in section.select(".stage"):
        ul = soup.new_tag("ul")
        for book in stage.select(".book"):
            li = soup.new_tag("li")
            t, a, d = (book.select_one(c) for c in (".t", ".a", ".d"))
            tags = [x.get_text(strip=True) for x in book.select(".rl-tag")]
            head = f"<strong>{t.get_text(strip=True)}</strong>" if t else ""
            if a:
                head += f" — {a.get_text(strip=True)}"
            if tags:
                head += " · " + ", ".join(f"<em>{x}</em>" for x in tags)
            li.append(BeautifulSoup(head + (f"<br>{d.decode_contents()}" if d else ""), "html.parser"))
            ul.append(li)
            book.decompose()
        stage.append(ul)

    return pandoc(section.decode_contents()), asides


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    src, slug = ROOT / args[0], args[1]
    out_dir = ROOT / "site/src/content/docs" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    soup = BeautifulSoup(src.read_text(encoding="utf-8"), "html.parser")
    for n, section in enumerate(soup.select("section.block"), start=1):
        sec_id = section.get("id") or f"seccion-{n}"
        title = section.find("h2").get_text(" ", strip=True)
        lead = section.select_one("p.lead")
        description = re.sub(r"\s+", " ", lead.get_text(" ", strip=True)) if lead else ""
        description = description.split(". ")[0].rstrip(".") + "."

        path = out_dir / f"{n:02d}-{sec_id}.md"
        if path.exists() and not force:
            print(f"skip {path.relative_to(ROOT)} (existe)")
            continue

        body, asides = transform(section, soup)
        for key, block in asides.items():
            body = body.replace(key, block)

        front = [
            "---",
            f"title: {title!r}".replace("'", '"') if '"' not in title else f"title: '{title}'",
            f'description: "{description.replace(chr(34), chr(39))}"',
            f"sidebar:\n  order: {n}",
            f"lesson:\n  id: {slug}-{sec_id}\n  guide: {slug}\n  order: {n}",
            "---",
        ]
        path.write_text("\n".join(front) + "\n\n" + body + "\n", encoding="utf-8")
        print(f"ok   {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
