"""Evaluar un LLM que extrae datos de texto: 60 avisos de empleo, 8 campos, dos prompts.

Sigue los capítulos 3 y 4 de AI Engineering (Chip Huyen):
  1. ¿Devuelve lo que se pidió? JSON válido y conforme al esquema (seguir instrucciones).
  2. ¿Es correcto? Comparación con la respuesta de referencia, campo por campo (evaluación exacta).
  3. ¿Qué tan estricta es la comparación? Exacta, normalizada o difusa: cada una da otro puntaje.
  4. ¿Mejoró el prompt v2? Aviso completo correcto, con IC de Wilson y McNemar pareado.

Por defecto evalúa las salidas reales de Claude (ejemplos/salidas_claude_*.jsonl), generadas
con demo/extraer_con_claude.py. Acepta otros dos archivos de salidas como argumentos (A y B).

Solo usa la biblioteca estándar. Correr desde la raíz del repo:
  python demo/extraccion.py
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

from formulas import mcnemar_exacto, wilson

CAMPOS = ["cargo", "ciudad", "modalidad", "salario_min", "salario_max", "moneda", "experiencia_anios", "fecha_cierre"]
NUMERICOS = {"salario_min", "salario_max", "experiencia_anios"}
TEXTO_LIBRE = {"cargo", "ciudad"}  # la comparación difusa solo tiene sentido acá; en una fecha aceptaría un día de error
ENUMS = {"modalidad": {"presencial", "remoto", "hibrido"}, "moneda": {"BOB", "USD"}}
MONEDAS = {"bob": "BOB", "bs": "BOB", "bs.": "BOB", "bolivianos": "BOB", "usd": "USD", "$us": "USD", "$": "USD", "dolares": "USD"}
MESES = {m: i for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                     "septiembre", "octubre", "noviembre", "diciembre"], 1)}


def leer(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


# 1. Formato ---------------------------------------------------------------

def parsear(texto, tolerante):
    """Estricto: la salida entera tiene que ser JSON. Tolerante: saca el bloque ``` o el texto de alrededor."""
    if tolerante:
        texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip())
        ini, fin = texto.find("{"), texto.rfind("}")
        texto = texto[ini:fin + 1] if ini != -1 and fin > ini else texto
    try:
        d = json.loads(texto)
    except json.JSONDecodeError:
        return None
    return d if isinstance(d, dict) else None


def cumple_esquema(d):
    if d is None or set(d) != set(CAMPOS) or not isinstance(d["cargo"], str):
        return False
    for c in CAMPOS[1:]:
        v = d[c]
        if v is None:
            continue
        if c in NUMERICOS and (isinstance(v, bool) or not isinstance(v, (int, float))):
            return False
        if c in ENUMS and v not in ENUMS[c]:
            return False
        if c == "fecha_cierre" and not (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)):
            return False
        if c == "ciudad" and not isinstance(v, str):
            return False
    return True


# 2 y 3. Contenido -----------------------------------------------------------

def sin_tildes(s):
    s = unicodedata.normalize("NFKD", str(s).lower())
    return " ".join("".join(ch for ch in s if not unicodedata.combining(ch)).split())


def numero(v):
    """'Bs 10.000' -> 10000. Un número que ya vino mal (7.2 en vez de 7200) no se arregla."""
    if v is None or isinstance(v, (int, float)):
        return v
    s = re.sub(r"[^\d.,]", "", str(v))
    s = re.sub(r"[.,](?=\d{3}\b)", "", s).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return str(v)


def fecha(v):
    """'15/11/2026', '28/11' o '20 de noviembre de 2026' -> AAAA-MM-DD (año 2026 si falta)."""
    if v is None:
        return None
    s = sin_tildes(v)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?", s)
    if m:
        return f"{m[3] or 2026}-{int(m[2]):02d}-{int(m[1]):02d}"
    m = re.fullmatch(r"(\d{1,2}) de (\w+)(?: de (\d{4}))?", s)
    if m and m[2] in MESES:
        return f"{m[3] or 2026}-{MESES[m[2]]:02d}-{int(m[1]):02d}"
    return s


def normalizar(campo, v):
    if v is None:
        return None
    if campo in NUMERICOS:
        return numero(v)
    if campo == "moneda":
        return MONEDAS.get(sin_tildes(v), v)
    if campo == "fecha_cierre":
        return fecha(v)
    return sin_tildes(v)


def igual(campo, pred, gold, nivel):
    if nivel == "exacta":
        return pred == gold
    p, g = normalizar(campo, pred), normalizar(campo, gold)
    if nivel == "difusa" and campo in TEXTO_LIBRE and isinstance(p, str) and isinstance(g, str):
        return SequenceMatcher(None, p, g).ratio() >= 0.8
    return p == g


def evaluar(avisos, salidas):
    """Por aviso: formato y, para cada campo, si acierta y si es TP, FP o FN."""
    por_id = {s["id"]: s["salida"] for s in salidas}
    filas = []
    for a in avisos:
        texto = por_id.get(a["id"], "")
        estricto, tolerante = parsear(texto, False), parsear(texto, True)
        pred = tolerante or {}  # si no se puede leer, cuenta como si no hubiera extraído nada
        fila = {"id": a["id"], "estricto": estricto is not None, "tolerante": tolerante is not None,
                "esquema": cumple_esquema(estricto), "pred": pred, "gold": a["gold"]}
        for nivel in ("exacta", "normalizada", "difusa"):
            fila[nivel] = {c: igual(c, pred.get(c), a["gold"][c], nivel) for c in CAMPOS}
        filas.append(fila)
    return filas


def prf(filas, campo):
    """Precisión y recall de un campo. Inventar un valor es un FP; omitirlo, un FN; equivocarlo, las dos cosas."""
    tp = fp = fn = 0
    for f in filas:
        p, g = f["pred"].get(campo), f["gold"][campo]
        ok = f["normalizada"][campo]
        tp += p is not None and g is not None and ok
        fp += p is not None and not ok
        fn += g is not None and not ok
    pr = tp / (tp + fp) if tp + fp else float("nan")
    re_ = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * pr * re_ / (pr + re_) if pr + re_ else float("nan")
    return pr, re_, f1


def pct(k, n):
    lo, hi = wilson(k, n)
    return f"{k:>2}/{n} {100 * k / n:3.0f} % ({100 * lo:.0f}–{100 * hi:.0f})"


def todo_bien(f, nivel):
    return all(f[nivel].values())


if __name__ == "__main__":
    ruta_a = sys.argv[1] if len(sys.argv) > 1 else "ejemplos/salidas_claude_v1.jsonl"
    ruta_b = sys.argv[2] if len(sys.argv) > 2 else "ejemplos/salidas_claude_v2.jsonl"
    avisos = leer("ejemplos/avisos.jsonl")
    salidas_a, salidas_b = leer(ruta_a), leer(ruta_b)
    con_salida = {s["id"] for s in salidas_a} | {s["id"] for s in salidas_b}
    sin_salida = [a["id"] for a in avisos if a["id"] not in con_salida]
    if sin_salida:
        print(f"Nota: {len(sin_salida)} avisos no tienen salida en ninguno de los dos archivos y se omiten "
              f"(un aviso sin salida en solo uno de los archivos sí cuenta, como fallo).\n")
        avisos = [a for a in avisos if a["id"] in con_salida]
    A, B = evaluar(avisos, salidas_a), evaluar(avisos, salidas_b)
    n = len(avisos)
    print(f"Extracción de {n} avisos de empleo, {len(CAMPOS)} campos. A = {ruta_a}, B = {ruta_b}")
    print("Entre paréntesis, IC de Wilson al 95 %.\n")

    print("1. ¿Devuelve lo que se pidió?")
    for clave, nombre in (("estricto", "JSON válido (estricto)"), ("tolerante", "JSON válido (tolerante)"),
                          ("esquema", "Cumple el esquema")):
        print(f"   {nombre:<24} A {pct(sum(f[clave] for f in A), n)}   B {pct(sum(f[clave] for f in B), n)}")

    print("\n2. ¿Es correcto? Acierto por campo (comparación normalizada)")
    print(f"   {'campo':<18} {'A':>5} {'B':>5}  B mejor  A mejor  McNemar p")
    for c in CAMPOS:
        a = [f["normalizada"][c] for f in A]
        b = [f["normalizada"][c] for f in B]
        solo_b = sum(y and not x for x, y in zip(a, b))
        solo_a = sum(x and not y for x, y in zip(a, b))
        print(f"   {c:<18} {sum(a):>5} {sum(b):>5}  {solo_b:>7}  {solo_a:>7}  {mcnemar_exacto(solo_b, solo_a):>9.3f}")

    print("\n   Precisión y recall por campo (inventar baja la precisión; omitir baja el recall)")
    for c in CAMPOS:
        (pa, ra, _), (pb, rb, _) = prf(A, c), prf(B, c)
        print(f"   {c:<18} A  P {pa:.2f}  R {ra:.2f}    B  P {pb:.2f}  R {rb:.2f}")

    print("\n3. La regla de comparación cambia el puntaje")
    for nivel in ("exacta", "normalizada", "difusa"):
        ca = sum(f[nivel]["cargo"] for f in A)
        ta, tb = sum(todo_bien(f, nivel) for f in A), sum(todo_bien(f, nivel) for f in B)
        print(f"   {nivel:<12} cargo A {ca:>2}/{n}   aviso completo A {ta:>2}/{n}  B {tb:>2}/{n}")

    print(f"\n4. ¿B es mejor que A? Aviso completo correcto (normalizada), mismos {n} avisos")
    ta = [todo_bien(f, "normalizada") for f in A]
    tb = [todo_bien(f, "normalizada") for f in B]
    solo_b = sum(y and not x for x, y in zip(ta, tb))
    solo_a = sum(x and not y for x, y in zip(ta, tb))
    print(f"   A {pct(sum(ta), n)}   B {pct(sum(tb), n)}")
    print(f"   solo B acierta: {solo_b}, solo A acierta: {solo_a}, McNemar p = {mcnemar_exacto(solo_b, solo_a):.4f}")

    print("\n5. Matriz de confusión de modalidad en A (filas: correcta, columnas: extraída)")
    cats = ["presencial", "remoto", "hibrido", None]
    conteo = Counter((f["gold"]["modalidad"], f["pred"].get("modalidad")) for f in A)
    otras = sorted({p for _, p in conteo if p not in cats})
    cols = cats + otras
    print("   " + " " * 11 + "".join(f"{str(c):>11}" for c in cols))
    for g in cats:
        print(f"   {str(g):<11}" + "".join(f"{conteo[(g, p)]:>11}" for p in cols))
