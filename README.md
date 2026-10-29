# ¿Cómo saber si una IA responde bien?

**Evaluar modelos de lenguaje es hacer estadística.** Material de la charla preparada para la Semana Aniversario de la Carrera de Estadística de la UMSA (26 al 29 de octubre de 2026): las fórmulas y una demo completa de evaluación de un LLM, con salidas reales de Claude.

## La idea en una frase

Evaluar un modelo de lenguaje es hacer un experimento estadístico con un instrumento de medición imperfecto. El puntaje es una estimación con error, las preguntas no siempre son independientes y el que califica (una persona, un script u otro LLM) también se equivoca.

## Cómo correrlo

```sh
python demo/formulas.py       # las fórmulas de la charla
python demo/extraccion.py     # el reporte completo de la demo, en texto
```

Los dos usan solo la biblioteca estándar y corren desde la raíz del repo. La demo también está como [notebook ya ejecutado](demo_extraccion.ipynb), con gráficos: se puede leer en GitHub sin instalar nada. Para re-ejecutarlo hace falta `matplotlib` (`pip install -r requirements.txt`).

## Qué hay en el repo

| Archivo | Qué es |
| --- | --- |
| [`demo_extraccion.ipynb`](demo_extraccion.ipynb) | La demo como notebook ya ejecutado: los tres evals, con gráficos calculados desde los datos |
| [`demo/extraccion.py`](demo/extraccion.py) | El mismo reporte en texto: formato, acierto por campo, precisión y recall, Wilson y McNemar |
| [`demo/formulas.py`](demo/formulas.py) | Margen de error, IC de Wilson, McNemar exacto, tamaño de muestra, Rogan–Gladen, pass@k |
| [`demo/extraer_con_claude.py`](demo/extraer_con_claude.py) | Opcional: genera las salidas con la API de Claude (requiere clave y cuesta plata) |
| [`ejemplos/avisos.jsonl`](ejemplos/avisos.jsonl) | 60 avisos de empleo bolivianos sintéticos, con su respuesta correcta |
| [`ejemplos/guia_anotacion.md`](ejemplos/guia_anotacion.md) | Las reglas para anotar los avisos, que también son el prompt v2 |
| `ejemplos/salidas_claude_v1.jsonl`, `_guia`, `_v2` | Salidas **reales** de Claude (`claude-opus-5-5`, 29/10/2026) para las tres versiones del prompt |
| [`.env.ejemplo`](.env.ejemplo) | Plantilla para la clave de la API (copiar a `.env`, que está en el gitignore) |

## Temario de la charla

1. **Por qué es difícil** (4 min). La anécdota del modelo que llevaba un año en producción y nadie sabía si acertaba.
2. **Qué es un eval y cómo se califica** (7 min). Los tres caminos: ejecutar, comparar con una referencia y pedir un juicio (el juez LLM y sus sesgos).
3. **Demo con salidas reales** (9 min). El prompt tal cual y el notebook `demo_extraccion.ipynb`: el formato, la correctitud contra la referencia bajo tres reglas y la comparación pareada (v2 gana 30 a 0), más leer los 3 errores que quedan.
4. **La estadística detrás** (3 min). Estimación con error, experimento pareado y un juez que se valida contra personas: lo que ya saben, con otro nombre.
5. **Cierre y preguntas** (7 min).

## Vocabulario mínimo

| Término | En una línea |
| --- | --- |
| **Eval** | Un conjunto de entradas y una forma de calificar las salidas que da un puntaje. |
| **Offline / online** | Offline corre sobre un conjunto fijo antes de lanzar ("¿se puede lanzar?"). Online corre sobre uso real ("¿funcionó?"). |
| **Golden set** | Entradas curadas con su respuesta correcta o una rúbrica: versionado, estratificado por modo de falla y con casos donde lo correcto es no responder. |
| **LLM como juez** | Un LLM califica las salidas de otro: una sola, de a pares o con rúbrica. Un veredicto binario con su justificación funciona mejor que una escala del 1 al 5. |
| **Error analysis** | Leer unas 100 salidas, anotar la primera falla de cada una, agruparlas y contarlas. Las métricas salen de ahí. |
| **Regresión / capacidad** | Una suite de regresión pasa casi al 100 % y frena un cambio si algo se rompe. Una de capacidad empieza baja y mide si el sistema aprende a hacer algo nuevo. |
| **Contaminación** | Las preguntas del examen estuvieron en los datos de entrenamiento del modelo. |
| **pass@k / pass^k** | pass@k pide al menos un acierto en k intentos; pass^k pide los k. El segundo mide consistencia. |
| **RAG evals** | Evaluar por separado la búsqueda de documentos (¿trajo los correctos?) y la respuesta (¿se basa en ellos?). |

## El ángulo estadístico

### El puntaje es una estimación

Si un modelo acierta una proporción *p* de *n* preguntas independientes, el error estándar es `sqrt(p(1−p)/n)` y el IC 95 % es ±1,96 veces eso:

| Preguntas | p = 0,5 | p = 0,8 |
| --- | --- | --- |
| 50 | ±13,9 pp | ±11,1 pp |
| 100 | ±9,8 pp | ±7,8 pp |
| 200 | ±6,9 pp | ±5,5 pp |
| 500 | ±4,4 pp | ±3,5 pp |
| 1000 | ±3,1 pp | ±2,5 pp |

Con pocas preguntas o con *p* cerca de 0 o 1 conviene el IC de Wilson: 4 aciertos en 16 son un 25 %, pero el intervalo va del 10 % al 49 %.

### Las preguntas no siempre son independientes

Cuando varias preguntas comparten un mismo texto o una misma fuente, son conglomerados y el error estándar se calcula por cluster. En el benchmark DROP, el SE por clusters salió 3,05 veces el ingenuo ([Miller, 2024](https://arxiv.org/abs/2411.00640)).

### Comparar dos modelos: siempre de a pares

Si los dos modelos responden las mismas preguntas, los datos son pareados y se comparan con McNemar o un bootstrap pareado. Solo informan las preguntas en las que difieren. Si A acierta 12 que B falla y B acierta 5 que A falla, la diferencia parece clara, pero McNemar da p = 0,14.

Parear también ahorra preguntas. Para detectar 3 pp con α = 0,05 y potencia del 80 %:

| Diseño | Preguntas |
| --- | --- |
| Pareado, los modelos difieren en el 10 % de las preguntas | 870 |
| Pareado, difieren en el 20 % | 1.742 |
| Independiente, con p ≈ 0,75 | 3.271 por modelo |

Si se miran muchas slices (por tema, por idioma, por largo), se corrige con Holm o Benjamini–Hochberg, o se fija de antemano una métrica primaria.

### El juez es un test diagnóstico

Un LLM que califica es un instrumento con sensibilidad y especificidad:

- Se reporta la **TPR** (de las salidas buenas, cuántas aprueba) y la **TNR** (de las malas, cuántas rechaza), no la accuracy. Si el 90 % de las salidas son buenas, un juez que aprueba todo tiene 90 % de accuracy y no sirve para nada.
- El acuerdo con humanos se mide con la **κ de Cohen**, y el acuerdo entre dos humanos es el techo.
- Las etiquetas humanas se separan como en cualquier modelo: un 10–20 % para ajustar el prompt del juez, un 40–45 % para desarrollo y un 40–45 % para la medición final.
- Con TPR y TNR conocidas, la **corrección de Rogan–Gladen** ajusta la tasa observada: si el juez aprueba el 80 % con TPR 0,92 y TNR 0,88, la tasa corregida es 0,85. [`judgy`](https://github.com/ai-evals-course/judgy) la calcula con IC.
- Los jueces tienen sesgos conocidos: prefieren la primera respuesta (se juzga en los dos órdenes), la más larga y las de su misma familia de modelos. En [Zheng et al. (2023)](https://arxiv.org/abs/2306.05685), GPT-4 como juez coincidió con expertos en más del 80 % de los casos, lo mismo que dos expertos entre sí.

### Consistencia y contaminación

Con un 75 % de acierto por intento, pass@3 es 98,4 % y pass^3 es 42,2 %. La primera métrica sirve si una persona elige entre tres opciones; la segunda, si el sistema tiene que acertar siempre.

La contaminación es la fuga de información entre entrenamiento y prueba. En modelos cerrados se puede detectar con un test de permutación sobre el orden de las preguntas ([Oren et al., 2023](https://arxiv.org/abs/2310.17623)).

### Lo que ya saben de estadística, con otro nombre

| En estadística | En evals |
| --- | --- |
| Error estándar e IC de una proporción | El ± de un puntaje |
| Muestreo por conglomerados | SE por clusters para preguntas que comparten fuente |
| Datos pareados y McNemar | Comparar dos modelos en las mismas preguntas |
| Potencia y tamaño de muestra | Cuántas preguntas necesita la suite |
| Comparaciones múltiples | Mirar muchas slices |
| Sensibilidad y especificidad | TPR y TNR del juez |
| Prevalencia y valor predictivo | Por qué la accuracy del juez engaña cuando casi todo pasa |
| Corrección por error de medición | Rogan–Gladen sobre la tasa del juez |
| Acuerdo entre evaluadores | κ juez–humano |
| Muestreo estratificado | Golden set por modo de falla |
| Codificación abierta y axial | Error analysis |
| Fuga de información | Contaminación |
| Experimento A/B | Eval online |

## La demo: evaluar un LLM que extrae datos

Muchas aplicaciones de LLMs en empresas no conversan: leen texto y llenan una tabla. La demo evalúa a Claude extrayendo 8 campos (cargo, ciudad, modalidad, salario mínimo y máximo, moneda, años de experiencia y fecha de cierre) de 60 avisos de empleo bolivianos sintéticos, con dos versiones del prompt:

- **v1:** un pedido corto con la lista de campos.
- **v2:** las reglas de la [guía de anotación](ejemplos/guia_anotacion.md) más un JSON Schema que obliga a responder JSON válido.

Las salidas son reales: generadas el 29/10/2026 con `demo/extraer_con_claude.py` (`claude-opus-5-5`, 180 llamadas, menos de un dólar). Generar se paga una vez; calificar es gratis y offline. Sigue los capítulos 3 y 4 de *AI Engineering* de Chip Huyen.

### Los tres evals

**Eval 1 — Formato: ¿devuelve lo que se pidió?** v1 da 0/60 de JSON estricto (envuelve todo en un bloque de código) y 0/60 de esquema; un parser tolerante rescata los 60. v2 da 60/60 en los tres criterios, pero ese 100 % no es mérito del prompt: lo garantiza la API con salidas estructuradas. El formato se califica aparte del contenido, y va primero.

**Eval 2 — Correctitud contra la referencia.** Las mismas salidas de v1 dan 3, 27 o 27 avisos completos de 60 según la comparación sea exacta, normalizada o difusa (v2: 56, 57 y 58). La regla de comparación es parte de la métrica y se elige antes de medir. Por campo, el que más mueve es modalidad (v2 acierta 20 avisos que v1 falla, y v1 ninguno); le sigue el cargo (9 a 1, p = 0,021).

**Eval 3 — ¿v2 es mejor? La comparación pareada.** Aviso completo con comparación normalizada: v1 27/60 (45 %, IC de Wilson 33–58) contra v2 57/60 (95 %, IC 86–98). Solo v2 acierta 30 avisos, solo v1 acierta 0: McNemar da p < 0,0001. No es azar.

Dos notas:

- **La ablación separa causas.** v2 cambió dos cosas a la vez, así que hay una tercera corrida (`salidas_claude_guia.jsonl`): las reglas sin esquema. En contenido, guia 56/60 y v2 57/60 empatan (p = 1); en formato, guia 5/60 contra 60/60. La guía arregla el contenido; el esquema arregla el formato.
- **Los 3 errores que quedan son el mismo error.** Los tres son el cargo con calificativos que la guía dice recortar ("freelance", "para tesis", "en encuestas de opinión"). La comparación difusa aceptaría uno de los tres. El puntaje dice cuánto falla; leer las salidas dice por qué.

### La guía de anotación es el prompt

La sección "Reglas" de la guía es lo que se le pide a una persona que anota y es también el prompt v2, tal cual. La sección "Casos dudosos" queda afuera del prompt: si el modelo la viera, conocería parte de las respuestas del examen. Es contaminación en chiquito.

## Receta para evaluar un sistema con LLMs

1. Leer unas 100 salidas reales y anotar la primera falla de cada una.
2. Agrupar las fallas en categorías y contarlas. Las métricas salen de ahí.
3. Armar un golden set estratificado por modo de falla, con una guía de anotación y casos donde lo correcto es no responder.
4. Calificar con código todo lo que se pueda: formato, esquema, coincidencia, ejecución. El juez LLM queda para lo subjetivo.
5. Si hay juez, validarlo contra etiquetas humanas con TPR, TNR y κ, con el acuerdo entre humanos como techo.
6. Reportar con IC y comparar versiones de a pares, sobre las mismas preguntas, con una métrica primaria fijada de antemano.
7. Correr la suite en cada cambio de prompt, modelo o datos, y confirmar con uso real lo que se ve offline.

## Para leer más

- Chip Huyen, *AI Engineering* (O'Reilly, 2025), capítulos 3 (metodología de evaluación) y 4 (evaluar sistemas de IA).
- Hamel Husain y Shreya Shankar, [AI Evals FAQ](https://hamel.dev/blog/posts/evals-faq/): el proceso completo, de error analysis a jueces.
- Evan Miller, [Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640) (2024), y su versión corta en el blog de Anthropic, [A statistical approach to model evaluations](https://www.anthropic.com/research/statistical-approach-to-model-evals).
- Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents): agentes, pass@k y pass^k.
- Zheng et al., [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) (2023): jueces LLM contra expertos humanos.
- Eugene Yan, [Evaluating the Effectiveness of LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/): la literatura sobre jueces, resumida.
- Oren et al., [Proving Test Set Contamination in Black Box Language Models](https://arxiv.org/abs/2310.17623) (2023).
- Hugging Face, [The Evaluation Guidebook](https://huggingface.co/spaces/OpenEvals/evaluation-guidebook): benchmarks, contaminación y reproducibilidad.
- Es et al., [Ragas](https://arxiv.org/abs/2309.15217) (2023): métricas para sistemas RAG.

Herramientas para llevar esto a un proyecto: [Inspect](https://inspect.aisi.org.uk/), [DeepEval](https://deepeval.com), [promptfoo](https://www.promptfoo.dev/) y [Ragas](https://docs.ragas.io/en/stable/). Alcanza con manejar una y entender los conceptos.

## Autor

Max Baldiviezo, Data Scientist y ML Engineer en Santa Cruz, Bolivia. [GitHub](https://github.com/Maxbm19).

## Datos

Los avisos de empleo son sintéticos. Cualquier parecido con un aviso real es casualidad.

## In English

Talk materials on evaluating LLMs as a statistics problem, prepared for the Statistics department of Universidad Mayor de San Andrés (La Paz, Bolivia). A complete worked example of evaluating an LLM on a data-extraction task with real Claude outputs: format checks, reference-based scoring under three comparison rules, Wilson intervals and paired McNemar tests for comparing prompt versions, plus an ablation. The code and comments are in Spanish.
