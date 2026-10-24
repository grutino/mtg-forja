---
name: mtg-forja
description: Analiza mazos de Magic: The Gathering y produce guías de sinergias, chuletas imprimibles y mapas interactivos, con todas las interacciones verificadas contra el texto de oráculo real. Úsala siempre que aparezca una lista de mazo, una captura del gestor de mazos de MTG Arena, o cualquier pregunta sobre combos, sinergias, curva, base de maná o cómo se pilota un mazo concreto — aunque la persona no nombre la skill ni pida explícitamente un documento. También cuando pregunten "qué hace esta carta", "cómo juego esto" o "qué combina con qué".
---

# MTG Forja

Cómo analizar un mazo de Magic sin inventarse nada.

## El reparto

La forja **no analiza**. Trae los hechos (oráculo, tipos, costes, rulings oficiales de
Wizards vía Scryfall), comprueba el análisis y lo dibuja. **El análisis lo haces tú
como experto**, o el modelo que la persona indique, y lo firmas.

Antes la forja deducía sinergias con patrones de texto. Inventaba jugadas («Ganar vida
a escala de tu mano» para un planeswalker que no da vida), tomaba el texto
recordatorio por efectos reales y no entendía las mecánicas nuevas (*empower*,
*behold*). Por eso se quitó: un análisis que suena seguro y está mal es el peor
resultado posible.

## La regla que lo gobierna todo

**Nunca afirmes lo que hace una carta desde la memoria.** Lee su oráculo y sus rulings
con `datos_para_analisis`. Y **no te quedes solo en la carta**: hay muchísimo escrito
sobre cada mazo, mecánica y metajuego. Consúltalo.

## Flujo de trabajo

1. **Hechos.** `datos_para_analisis(lista)` (CLI: `mtg-forja datos LISTA`): por carta,
   oráculo, tipo, coste, palabras clave y rulings oficiales. Ninguna interpretación.
2. **Investigar.** Busca en internet antes de opinar, y guarda cada URL que uses:
   - **Reglas:** el oráculo y los rulings ya los tienes; para mecánicas nuevas, el
     artículo de mecánicas de la colección en magic.wizards.com.
   - **Listas reales:** MTGGoldfish, MTGDecks, MTGTop8, Untapped.gg (Arena), Moxfield.
     ¿Quién juega este arquetipo, con qué cartas y con qué resultados?
   - **Metajuego y análisis:** magic.gg (Metagame Mentor), Draftsim, Card Kingdom Blog,
     CoolStuffInc, 17Lands para limitado.
   - **Combos:** `combos_conocidos` (Commander Spellbook) es una fuente más.
   - **Legalidad:** comprueba el formato y la próxima rotación si aplica.
3. **Pensar como experto.** Con el oráculo delante:
   - ¿cómo gana el mazo, exactamente? ¿Qué cartas son el plan y cuáles lo protegen?
   - ¿a quién alcanza cada efecto, y a quién **no**? (los rulings lo dicen)
   - ¿qué se estorba entre sí? ¿qué secuencia de turnos hace que funcione?
   - ¿el texto que lees es efecto o es **texto recordatorio** entre paréntesis?
   - ¿cómo de bueno es el mazo frente al metajuego real, y por qué?
4. **Escribir `analisis.json`** (formato abajo).
5. **Validar.** `validar_analisis(lista, analisis)` devuelve los problemas. Corrígelos;
   no los esquives quitando citas.
6. **Forjar.** `forjar(lista, analisis, incrustar_imagenes=...)` (CLI:
   `mtg-forja forjar LISTA -a analisis.json [--incrustar-imagenes]`). Si el análisis no
   valida, no se genera nada. Usa `incrustar_imagenes` cuando el HTML se vaya a ver en
   el visor del chat, que bloquea las imágenes externas.

Si solo quieren una respuesta rápida en el chat, haz los pasos 1 a 3 y responde,
citando igualmente. No generes archivos que nadie ha pedido.

## La revisión experta

**Ningún resultado sale sin ella.** El validador la exige y los tres documentos la
muestran. `revisor` es quien ha hecho el análisis de verdad: tu nombre de modelo real
(«Claude Opus 5.5»), o el modelo o la persona que te indiquen. No firmes en nombre de
otro, y no firmes lo que no hayas comprobado.

`veredicto` es una **valoración**, no una descripción: qué tal es el mazo, contra qué
sufre, qué cambiarías. Si dependes de datos externos (porcentajes de victoria, listas
de referencia), cítalos en `fuentes`.

## El formato del análisis

```json
{
  "titulo": "Jace monoazul",
  "subtitulo": "Estándar · 60 cartas · control de contrahechizos",
  "revision_experta": {
    "revisor": "Claude Opus 5.5", "fecha": "2026-10-23",
    "titular": "Control sólido con un final muy lento",
    "veredicto": "…", "fortalezas": ["…"], "debilidades": ["…"],
    "confianza": "media", "fuentes": ["mtgdecks"]
  },
  "fuentes": [{"id": "mtgdecks", "titulo": "…", "url": "https://…"}],
  "cartas": {
    "Countersculpt": {"rol": "respuesta", "estrategia": "…", "fuentes": []}
  },
  "planes": [{"titulo": "…", "texto": "…", "fuentes": []}],
  "sinergias": [{
    "nombre": "…", "bloque": "El motor", "tipo": "sinergia", "fuerza": 3,
    "turno": "T3", "piezas": ["A", "B"], "resumen": "…", "pasos": ["…"],
    "aviso": "…",
    "citas": [{"carta": "A", "texto": "frase literal del oráculo o de un ruling"},
              {"carta": "B", "texto": "…"}],
    "fuentes": []
  }],
  "orden": [{"turno": "T2", "carta": "…", "resumen": "…"}],
  "reglas_oro": ["…"],
  "formato": "standard",
  "plataforma": "arena",
  "mejoras": [{
    "titulo": "…", "nivel": "clara",
    "sale": [{"carta": "A", "copias": 2}],
    "entra": [{"carta": "C", "copias": 2}],
    "motivo": "…", "aviso": "…",
    "citas": [{"carta": "C", "texto": "frase literal"}],
    "fuentes": []
  }]
}
```

Lo que comprueba el validador:

| Regla | Por qué |
|---|---|
| `revision_experta` con `revisor`, `fecha` y `veredicto` | Nada sale sin valoración experta firmada |
| `rol` de cada carta que no sea tierra (`motor`, `amenaza`, `respuesta`, `tierra`) | La clasificación es criterio, no un regex |
| Cada pieza de cada jugada lleva al menos una cita **literal** de su oráculo o de un ruling | Que no se pueda atribuir a una carta lo que no dice |
| Toda carta nombrada está en el mazo | Ni piezas fantasma ni combos a medias |
| Cada fuente citada existe y tiene URL | Lo externo se puede comprobar |
| `mejoras`: máximo 5, `nivel` `clara` o `razonable`, y `formato` presente | Solo cambios evidentes, nunca una lista de deseos |
| Lo que sale está en el mazo; lo que entra existe en Scryfall, es legal en `formato` y, con `plataforma: arena`, está en Arena | Una mejora que no se puede jugar no es una mejora |
| Salen y entran las mismas cartas, nadie pasa de 4 copias salvo las básicas | El mazo sigue siendo legal |
| Cada mejora lleva una cita literal (del mazo o de la carta que entra) o una fuente | El porqué se puede comprobar |

`tipo`: `sinergia`, `conflicto` o `aviso`. `fuerza`: 1 a 3. `turno`: `T2`, `Tarde`,
`Reacción`, `Ojo`. Puedes usar `<b>` en `resumen`, `pasos`, `aviso`, `veredicto` y `texto`.

**Mejoras propuestas.** Salen en la guía, en su propio apartado. Propón solo cambios
muy claros (un fallo de maná, una carta que no encaja con el plan) o muy razonables
(lo que hacen las listas de referencia, con fuente). Si no ves ninguno así, deja
`mejoras` fuera: no hay que rellenar. Usa `aviso` para decir cuándo no conviene.

**Ojo con las citas de texto recordatorio.** Son literales y el validador las acepta,
pero el recordatorio describe una mecánica, no un efecto extra de la carta. Cita la
línea que de verdad sostiene la jugada.

## Qué documento pide cada situación

| Piden | Genera |
|---|---|
| "¿qué combos tiene?", una duda concreta | Nada. Contesta en el chat, con citas. |
| "explícame el mazo a fondo" | Forja y entrega la guía |
| "algo para tener al lado mientras juego" | La chuleta |
| "quiero ver cómo encaja todo" | El mapa |
| "prepáramelo todo" | Los tres |

## Cómo se escribe un buen análisis

**Los pasos son una secuencia real, no una descripción.** Mal: «esta carta combina
bien con la otra». Bien: «ten X en mesa → lanza Y apuntando a X → como es
indestructible sobrevive, pero igualmente robas».

**Di cuándo, no solo qué.** Una sinergia de turno 2 y una de turno 8 se juegan distinto.

**Los conflictos valen tanto como las sinergias.** Qué se lleva por delante tu propio
motor, qué orden de juego arruina el plan.

**Cuenta las copias.** «Llevas una sola copia de la carta que gana» es accionable.

**Nada de relleno.** Si una sección no aporta, quítala.

## Límites

- La forja comprueba que las citas son literales, no que tu razonamiento sea correcto.
  Eso es responsabilidad de quien firma la revisión.
- Los datos de metajuego caducan: pon fecha y fuente.
- Las imágenes se enlazan a Scryfall salvo que pidas incrustarlas.
