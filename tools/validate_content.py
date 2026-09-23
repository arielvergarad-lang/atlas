# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Revisa reglas de Atlas que el esquema de Astro no puede ver (cruzan archivos o miran el cuerpo).

Uso:  uv run tools/validate_content.py        (sale con código 1 si algo falla)

- toda lección tiene quiz y sección de práctica
- lesson.id es único por idioma
- una traducción usa el mismo lesson.id y el mismo número de preguntas que el original
"""

import re
import sys
from pathlib import Path

import yaml

DOCS = Path(__file__).resolve().parent.parent / "site/src/content/docs"
LOCALES = {"en": "## Practice"}  # locale -> encabezado de práctica; la raíz es español
ROOT_PRACTICE = "## Práctica"


def parse(path: Path) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n(.*)", path.read_text(encoding="utf-8"), re.S)
    return (yaml.safe_load(m.group(1)) or {}, m.group(2)) if m else ({}, "")


def main() -> int:
    errors: list[str] = []
    by_locale: dict[str, dict[str, tuple[Path, dict]]] = {}

    for path in sorted(DOCS.rglob("*.md*")):
        rel = path.relative_to(DOCS)
        locale = rel.parts[0] if rel.parts[0] in LOCALES else ""
        data, body = parse(path)
        lesson = data.get("lesson")
        if not lesson:
            continue
        practice = LOCALES.get(locale, ROOT_PRACTICE)
        if not data.get("quiz"):
            errors.append(f"{rel}: lección sin quiz")
        if practice not in body:
            errors.append(f"{rel}: lección sin sección '{practice}'")
        seen = by_locale.setdefault(locale, {})
        if lesson["id"] in seen:
            errors.append(f"{rel}: lesson.id '{lesson['id']}' repetido (ya en {seen[lesson['id']][0].relative_to(DOCS)})")
        seen[lesson["id"]] = (path, data)

    root = by_locale.get("", {})
    root_by_path = {p.relative_to(DOCS): (p, d) for p, d in root.values()}
    for locale in LOCALES:
        for path, data in by_locale.get(locale, {}).values():
            rel = path.relative_to(DOCS)
            original = root_by_path.get(Path(*rel.parts[1:]))
            if not original:
                errors.append(f"{rel}: traducción sin original en español en la misma ruta")
                continue
            if original[1]["lesson"]["id"] != data["lesson"]["id"]:
                errors.append(f"{rel}: lesson.id distinto al original")
            if len(original[1].get("quiz", [])) != len(data.get("quiz", [])):
                errors.append(f"{rel}: número de preguntas distinto al original")

    total = sum(len(v) for v in by_locale.values())
    for e in errors:
        print("✗", e)
    print(f"{total} lecciones revisadas ({', '.join(f'{k or 'es'}: {len(v)}' for k, v in by_locale.items())}), {len(errors)} errores")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
