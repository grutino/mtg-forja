---
name: mtg-forja
description: Analiza mazos de Magic: The Gathering y produce guías de sinergias, chuletas imprimibles y mapas interactivos, con todas las interacciones verificadas contra el texto de oráculo real. Úsala siempre que aparezca una lista de mazo, una captura del gestor de mazos de MTG Arena, o cualquier pregunta sobre combos, sinergias, curva, base de maná o cómo se pilota un mazo concreto — aunque la persona no nombre la skill ni pida explícitamente un documento. También cuando pregunten "qué hace esta carta", "cómo juego esto" o "qué combina con qué".
---

# MTG Forja

Cómo analizar un mazo de Magic sin inventarse nada.

## La regla que lo gobierna todo

**Nunca afirmes lo que hace una carta desde la memoria.** El texto de oráculo cambia
con las erratas, las cartas se parecen entre sí y la confianza no correlaciona con
el acierto. Antes de escribir una sola frase sobre una interacción, resuelve el mazo
con `resolver_mazo` o `detectar_sinergias` y lee el oráculo que devuelven.

Esto no es una precaución teórica. Errores reales cometidos por no hacerlo:

- Afirmar que una carta baraja la biblioteca cuando en realidad manda cartas al fondo.
  El efecto sobre el plan de victoria era el contrario del descrito.
- Dar por hecho que una tierra entraba girada bajo condición, cuando era indestructible
  y siempre entraba girada. Se perdió la mitad de un motor del mazo.
- Clasificar un planeswalker como artefacto porque el mazo iba de artefactos.

Si no tienes las herramientas del servidor disponibles, búscalo en la web o dilo
claramente. Escribir de memoria y sonar seguro es el peor de los resultados.

## Lo que el motor NO puede ver

Esto es lo primero que hay que entender, porque determina todo lo demás.

El motor de patrones solo encuentra **lo que alguien escribió antes**. El léxico de
recursos añade lo que se deduce de flujos («A llena el cementerio, B lo aprovecha»),
que es real pero superficial. Ninguno de los dos puede razonar sobre las reglas del
juego, y ahí es donde está el análisis que merece la pena:

| Lo que hay que ver | Por qué ningún motor lo ve |
|---|---|
| «Apaga los artefactos del rival, **pero no los tuyos**» | requiere entender la asimetría de un efecto |
| «El barrido no alcanza a tus planeswalkers» | requiere inferir qué queda **fuera** del efecto |
| «Esa tierra solo es criatura cuando la activas, así que sobrevive» | requiere razonar sobre estados temporales |
| «Barajar descoloca la carta que habías puesto arriba» | requiere modelar posición en la biblioteca |

**Eso lo pones tú, leyendo el oráculo.** Si te limitas a redactar las candidatas del
motor, el análisis será correcto y vacío.

## Flujo de trabajo

0. **Radiografiar.** `radiografia_del_mazo(lista)` te da los hechos objetivos: el
   oráculo de cada carta y, por carta, `alcance` (simétrico / asimétrico / solo tuyo /
   solo del rival), `tipos_que_menciona`, `zonas_que_toca` y `velocidad`. A nivel de
   mazo: curva, reparto por tipo, copias únicas y si hay fuentes de color para lo que
   el propio mazo exige. **Empieza siempre por aquí**, y en especial con un mazo de un
   arquetipo que no reconozcas: es lo único que te deja ver las cuatro cosas de la
   tabla de arriba.
0b. **Comprobar cobertura si el mazo trae cartas recientes.**
   `cobertura_del_analisis(lista)` te dice si el motor **entiende** el mazo o solo
   lo lee. Resolver contra Scryfall funciona siempre, incluso con colecciones que
   aún no han salido; entenderlas es otra cosa. Si salen `mecanicas_sin_concepto`
   o `cartas_invisibles`, **el recuento de sinergias no significa nada**: esas
   cartas no van a aparecer por mucho que insistas. Lee su oráculo en la
   radiografía y razona tú la interacción — para eso estás.

1. **Resolver.** `detectar_sinergias(lista)` devuelve las cartas con su oráculo, la
   curva y las sinergias candidatas que ha encontrado el motor de reglas.
   Opcionalmente, `combos_conocidos(lista)` trae combos ya catalogados por Commander
   Spellbook, con sus pasos redactados. **Léete el aviso de abajo antes de usarlo.**
1b. **Consultar los rulings antes de afirmar un límite.** `rulings_oficiales(lista)`
   trae las aclaraciones de Wizards —el contenido de Gatherer— para las cartas del
   mazo. Es fuente verificada, no comunidad. Consúltalas **siempre que vayas a decir
   a quién alcanza un efecto, dónde funciona o cuándo se aplica**: ahí es donde se
   cometen los errores. «Karn's first ability affects only artifacts on the
   battlefield» está escrito por el fabricante; no hace falta que lo deduzcas.

2. **Juzgar.** Las candidatas son un borrador mecánico, no el análisis. Tu trabajo:
   - **Descartar** las que técnicamente casan pero no importan en la práctica.
   - **Reordenar** por lo que de verdad decide partidas, no por la puntuación del motor.
   - **Añadir** lo que el motor no ve. Esta es la parte que importa. Recorre la
     radiografía carta a carta y pregúntate, con el oráculo delante:
     · ¿a quién alcanza este efecto, y a quién **no**?
     · ¿qué cartas de este mazo **sobreviven** a mi propio barrido, y por qué?
     · ¿hay algo aquí que apague o estorbe a otra carta del mazo?
     · ¿qué secuencia de turnos hace que estas cartas funcionen juntas?
     · ¿el mazo puede lanzar sus propias cartas con las fuentes que lleva?
     Y añade lo de siempre: planes de juego, emparejamientos, por qué está cada carta,
     qué le sobra y qué le falta.
   - **Comprobar** cada candidata contra su campo `evidencia`, que es la frase exacta
     del oráculo que disparó la regla. Si la evidencia no sostiene la afirmación, fuera.
3. **Escribir.** Rellena el documento con tus textos y pásalo a los renderizadores.
4. **Renderizar.** `render_guia`, `render_chuleta`, `render_mapa`.

Si solo quieren una respuesta rápida en el chat, quédate en el paso 2 y responde.
No generes archivos que nadie ha pedido.

## La única fuente que no es oráculo

`combos_conocidos` es la excepción a toda la regla de arriba: sus datos vienen de
**Commander Spellbook**, una base curada por su comunidad, no de Scryfall. Es valiosa
—trae combos con nombre propio y sus pasos, que ningún motor deduce— pero no está
verificada contra el texto de la carta.

Antes de meter uno de esos combos en un documento:

1. **Contrasta.** Comprueba con `resolver_mazo` o `radiografia_del_mazo` que las cartas
   hacen de verdad lo que el combo dice. Presta atención a si el mazo lleva de verdad
   todas las piezas, y a si el combo asume reglas de Commander que aquí no aplican.
2. **Descarta sin pena** si el oráculo real no sostiene los pasos. Un combo mal copiado
   es peor que ningún combo.
3. **Cita la fuente** cuando lo uses: «según Commander Spellbook».

Y no lo uses como muleta: la mayoría de mazos no llevan combos catalogados, y el
análisis bueno sigue saliendo de leer las cartas.

## Qué documento pide cada situación

| Piden | Genera |
|---|---|
| "¿qué combos tiene?", una duda concreta | Nada. Contesta en el chat. |
| "explícame el mazo a fondo" | `render_guia` |
| "algo para tener al lado mientras juego" | `render_chuleta` (dos caras A4) |
| "quiero ver cómo encaja todo" | `render_mapa` |
| "prepáramelo todo" | Los tres |

## El documento

Los tres renderizadores consumen la misma estructura. Los campos que rellenas tú:

- `titulo`, `subtitulo` — nombre del mazo y una línea de contexto (formato, cartas).
- `cartas[].estrategia` — una o dos frases sobre el papel de esa carta *en este mazo*.
- `sinergias[]` — `nombre` (corto y concreto), `turno` (cuándo entra en juego: `T2`,
  `Tarde`, `Reacción`, `Ojo`), `resumen` (una frase), `pasos` (la secuencia real de la
  jugada), `aviso` (opcional, dónde se tuerce), `tipo` (`sinergia`, `conflicto`, `aviso`),
  `fuerza` (1 a 3), `bloque` (el agrupador que aparece como sección).
- `orden[]` — `{turno, carta, resumen}`, la curva de juego turno a turno.
- `reglas_oro[]` — principios que no cambian de partida a partida.

Puedes usar `<b>` para destacar dentro de `resumen`, `pasos` y `aviso`.

## Cómo se escribe un buen análisis

**Los pasos son una secuencia real, no una descripción.** Mal: «esta carta combina
bien con la otra». Bien: «ten X en mesa → lanza Y apuntando a X → como es
indestructible sobrevive, pero igualmente buscas y robas».

**Di cuándo, no solo qué.** El turno en que una sinergia entra en juego es la mitad
de la información útil. Una sinergia de turno 2 y una de turno 8 se juegan distinto.

**Los conflictos valen tanto como las sinergias.** Qué carta se lleva por delante tu
propio motor, qué orden de juego arruina el plan, qué modo de un hechizo modal te
perjudica. Es lo que nadie pone en las guías y lo que más partidas cuesta.

**Cuenta las copias.** «Llevas una sola copia de la carta que gana la partida» es un
dato accionable. Las cantidades cambian el consejo.

**Nada de relleno.** Si una sección no aporta, quítala. La chuleta cabe en dos caras
precisamente porque no hay literatura.

## Añadir reglas al motor

`reglas.json` es una lista de patrones genéricos: cada uno describe piezas que deben
existir en el mazo (por texto de oráculo, tipo, coste, valor de maná o número de
copias) y qué explicar cuando aparecen juntas. `listar_reglas` enseña las que hay.

Si detectas a mano una interacción que el motor no vio y el patrón es **general**
—no específico de dos cartas concretas— propón añadirla. El valor del proyecto está
en que las reglas sirvan para mazos que nadie ha visto todavía.

## Límites

- El motor casa patrones de texto: encuentra interacciones plausibles, no verdades.
  La comprobación final la haces tú contra el oráculo.
- No conoce el metajuego, ni precios, ni legalidad por formato más allá de lo que
  devuelva Scryfall.
- Las imágenes de carta se enlazan a Scryfall; no se copian a los documentos.
