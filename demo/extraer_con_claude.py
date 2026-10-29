"""Generar salidas reales de Claude para evaluarlas con demo/extraccion.py. Opcional: cuesta plata.

Necesita `pip install anthropic` y la variable ANTHROPIC_API_KEY. Correr desde la raíz del repo:
  python demo/extraer_con_claude.py v1 datos/salidas_claude_v1.jsonl
  python demo/extraer_con_claude.py v2 datos/salidas_claude_v2.jsonl
  python demo/extraccion.py datos/salidas_claude_v1.jsonl datos/salidas_claude_v2.jsonl

Versiones del prompt:
  v1    un pedido corto con la lista de campos
  guia  las reglas de ejemplos/guia_anotacion.md, sin esquema
  v2    las mismas reglas más un JSON Schema que obliga a responder JSON válido

v2 cambia dos cosas a la vez respecto de v1. Correr también `guia` muestra cuánto aporta cada una.
Cada versión son 40 llamadas, una por aviso.
"""
import json
import pathlib
import sys

import anthropic

MODELO = "claude-opus-5-5"
CAMPOS = ["cargo", "ciudad", "modalidad", "salario_min", "salario_max", "moneda", "experiencia_anios", "fecha_cierre"]

PROMPT_V1 = f"Extrae del aviso de empleo estos campos y responde en JSON: {', '.join(CAMPOS)}."


def nulable(tipo, **extra):
    return {"anyOf": [{"type": tipo, **extra}, {"type": "null"}]}


ESQUEMA = {
    "type": "object",
    "properties": {
        "cargo": {"type": "string"},
        "ciudad": nulable("string"),
        "modalidad": nulable("string", enum=["presencial", "remoto", "hibrido"]),
        "salario_min": nulable("number"),
        "salario_max": nulable("number"),
        "moneda": nulable("string", enum=["BOB", "USD"]),
        "experiencia_anios": nulable("number"),
        "fecha_cierre": nulable("string", format="date"),
    },
    "required": CAMPOS,
    "additionalProperties": False,
}


def reglas():
    """La sección Reglas de la guía de anotación, tal cual. Los casos dudosos quedan afuera."""
    guia = pathlib.Path("ejemplos/guia_anotacion.md").read_text(encoding="utf-8")
    return guia.split("## Reglas", 1)[1].split("## Casos dudosos", 1)[0].strip()


def extraer(client, texto, system, con_esquema):
    config = {"effort": "low"}  # extraer campos no necesita pensar mucho; baja el costo
    if con_esquema:
        config["format"] = {"type": "json_schema", "schema": ESQUEMA}
    r = client.beta.messages.create(
        model=MODELO,
        max_tokens=4000,
        # Si el modelo rechaza el pedido, la API lo reintenta con otro modelo. Se puede quitar.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        messages=[{"role": "user", "content": texto}],
        output_config=config,
    )
    if r.stop_reason == "refusal":
        return ""  # cuenta como salida inválida
    return "".join(b.text for b in r.content if b.type == "text")


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "v2"
    salida = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else f"datos/salidas_claude_{version}.jsonl")
    pedido = "Extrae los datos de este aviso de empleo y responde solo con un objeto JSON.\n\n"
    system, con_esquema = {"v1": (PROMPT_V1, False),
                           "guia": (pedido + reglas(), False),
                           "v2": (pedido + reglas(), True)}[version]

    client = anthropic.Anthropic()
    with open("ejemplos/avisos.jsonl", encoding="utf-8") as f:
        avisos = [json.loads(linea) for linea in f if linea.strip()]
    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        for a in avisos:
            texto = extraer(client, a["texto"], system, con_esquema)
            f.write(json.dumps({"id": a["id"], "salida": texto}, ensure_ascii=False) + "\n")
            print(f"aviso {a['id']:>2}: {texto[:70]!r}")
    print(f"\n{len(avisos)} salidas en {salida}")
