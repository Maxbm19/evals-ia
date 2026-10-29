# Guía de anotación: avisos de empleo

Estas reglas sirvieron para escribir la respuesta correcta (`gold`) de cada aviso en `avisos.jsonl`. El prompt v2 de `demo/extraer_con_claude.py` es la sección **Reglas**, tal cual: lo que se le pide a una persona que anota y lo que se le pide al modelo es lo mismo.

## Reglas

De cada aviso se extraen 8 campos. Si el aviso no dice algo, el campo va en `null`. No hay que inventar ni deducir lo que el aviso no dice.

| Campo | Tipo | Regla |
| --- | --- | --- |
| `cargo` | texto | El nombre del puesto tal como aparece, sin la empresa ni la tecnología entre paréntesis. |
| `ciudad` | texto o `null` | La ciudad de Bolivia donde se trabaja. `null` si el trabajo es remoto y no nombra una ciudad. El país del cliente no es la ciudad. |
| `modalidad` | `presencial`, `remoto`, `hibrido` o `null` | Solo si el aviso lo dice. "Mixta" o "algunos días en oficina" cuentan como `hibrido`. "Presentar documentos en oficinas" no dice nada sobre la modalidad. |
| `salario_min`, `salario_max` | número o `null` | Monto mensual. Un solo monto va en los dos campos. "Desde X" llena solo el mínimo y "hasta X" solo el máximo. "A convenir" o "competitivo" van en `null`. Un monto total por varios meses se divide por la cantidad de meses. |
| `moneda` | `BOB`, `USD` o `null` | Bs, Bs. y bolivianos son `BOB`. $us, USD, $ y dólares son `USD`. Va en `null` si no hay un monto. |
| `experiencia_anios` | número o `null` | El mínimo de años pedido. "Sin experiencia" o "recién egresados" es 0. Seis meses es 0,5. Si la experiencia "se valora" pero no se exige, va en `null`. |
| `fecha_cierre` | `AAAA-MM-DD` o `null` | La fecha límite para postular. Si no dice el año, es 2026. |

Los números van sin separador de miles: "Bs 8.000" es 8000 y "USD 1,500" es 1500.

## Casos dudosos

Algunos casos quedaron dudosos aun con la guía, y eso también es un dato:

- **Aviso 11**, "startup cruceña": se anotó Santa Cruz porque el puesto es presencial y la empresa es de allí, pero el aviso no nombra la ciudad.
- **Aviso 37**, "aplicar antes del 10/12": se anotó el 10 de diciembre, pero alguien podría anotar el 9.

Cuando dos personas anotan distinto un mismo caso, se arregla la guía, no el modelo.

Esta sección no va en el prompt. Si el modelo la leyera, vería parte de las respuestas del examen: es la misma contaminación que infla los puntajes de los benchmarks públicos.
