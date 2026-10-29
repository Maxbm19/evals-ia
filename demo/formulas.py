"""Las fórmulas de la charla, con los ejemplos que se muestran en las diapositivas.

Solo usa la biblioteca estándar. Correr:
  python demo/formulas.py
"""
import math

Z95 = 1.959964  # z para un IC del 95 %
Z80 = 0.841621  # z para un power del 80 %


def margen(p, n, z=Z95):
    """Margen de error (±) de un puntaje p medido sobre n preguntas independientes."""
    return z * math.sqrt(p * (1 - p) / n)


def wilson(k, n, z=Z95):
    """IC de Wilson para k aciertos en n. Se porta bien con n chico o p cerca de 0 o 1."""
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    medio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centro - medio, centro + medio


def mcnemar_exacto(b, c):
    """p-valor bilateral de McNemar exacto.

    b = preguntas que solo acierta el modelo A, c = las que solo acierta el B.
    Las que aciertan o fallan los dos no informan sobre la diferencia.
    """
    n = b + c
    if n == 0:
        return 1.0
    cola = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * cola)


def n_pareado(delta, discordantes, z_a=Z95, z_b=Z80):
    """Preguntas necesarias para detectar una diferencia delta entre dos modelos
    evaluados sobre las mismas preguntas (aproximación de Connor para McNemar).

    discordantes = proporción de preguntas en las que los modelos difieren.
    """
    psi = discordantes
    return math.ceil((z_a * math.sqrt(psi) + z_b * math.sqrt(psi - delta ** 2)) ** 2 / delta ** 2)


def n_independiente(delta, p, z_a=Z95, z_b=Z80):
    """Preguntas por modelo si cada uno se evalúa sobre preguntas distintas."""
    return math.ceil((z_a + z_b) ** 2 * 2 * p * (1 - p) / delta ** 2)


def rogan_gladen(p_obs, tpr, tnr):
    """Corrige la tasa de aprobados que reporta un juez imperfecto.

    tpr = de las respuestas buenas, cuántas aprueba el juez.
    tnr = de las respuestas malas, cuántas rechaza.
    """
    return (p_obs + tnr - 1) / (tpr + tnr - 1)


def pass_at_k(p, k):
    """Probabilidad de al menos un acierto en k intentos."""
    return 1 - (1 - p) ** k


def pass_hat_k(p, k):
    """Probabilidad de acertar los k intentos (pass^k): mide consistencia."""
    return p ** k


if __name__ == "__main__":
    print("1. Margen de error del puntaje (IC 95 %)")
    for p in (0.5, 0.8):
        fila = ", ".join(f"n={n}: ±{100 * margen(p, n):.1f} pp" for n in (50, 100, 200, 500, 1000))
        print(f"   p={p}: {fila}")

    print("\n2. IC de Wilson con pocas preguntas: 4 aciertos en 16")
    lo, hi = wilson(4, 16)
    print(f"   25 % ({100 * lo:.0f} % a {100 * hi:.0f} %)")

    print("\n3. McNemar exacto: A acierta 12 preguntas que B falla, B acierta 5 que A falla")
    print(f"   p = {mcnemar_exacto(12, 5):.3f}")

    print("\n4. Cuántas preguntas para detectar 3 pp (alfa 0,05, power 80 %)")
    for psi in (0.10, 0.20):
        print(f"   pareado, modelos que difieren en el {100 * psi:.0f} % de las preguntas: {n_pareado(0.03, psi)}")
    print(f"   independiente, p ~ 0,75: {n_independiente(0.03, 0.75)} por modelo")

    print("\n5. Rogan-Gladen: el juez aprueba el 80 %, con TPR 0,92 y TNR 0,88")
    print(f"   tasa corregida = {rogan_gladen(0.80, 0.92, 0.88):.2f}")

    print("\n6. Consistencia con 75 % de acierto por intento")
    print(f"   pass@3 = {pass_at_k(0.75, 3):.3f}, pass^3 = {pass_hat_k(0.75, 3):.3f}")
