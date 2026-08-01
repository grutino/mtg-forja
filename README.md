# MTG Forja

Analiza un mazo de **Magic: The Gathering** y genera tres cosas: una guía extensa de
sinergias, una chuleta imprimible de dos caras y un mapa interactivo navegable.

Funciona de tres maneras: como **servidor MCP** dentro de Claude, como **herramienta de
línea de comandos** y como **web** que corre entera en el navegador.

> La premisa: las interacciones se comprueban contra el texto de oráculo real que
> devuelve [Scryfall](https://scryfall.com), nunca contra lo que un modelo de lenguaje
> cree recordar. Los cuatro errores que originaron este proyecto —una carta que se creía
> que barajaba y mandaba al fondo, una tierra indestructible tomada por condicional— son
> exactamente los que el motor detecta bien.

---

## Qué genera

Pegas una lista de mazo y salen tres documentos HTML autónomos. Estas capturas son
salida real del mazo de ejemplo (45 cartas, 20 sinergias detectadas).

### El mapa del mazo

Un grafo de fuerzas navegable: cada círculo es una carta, su tamaño depende de cuántas
copias llevas y el grosor de la línea marca la fuerza de la sinergia. Las **líneas rojas
discontinuas** son cartas que se estorban entre sí. Puedes pulsar cualquier carta para
aislar sus conexiones, arrastrarlas, hacer zoom y filtrar por función.

![Mapa de sinergias del mazo](docs/capturas/mapa.png)

### La guía de sinergias

Página larga con cada jugada desarrollada: las piezas ilustradas, la secuencia numerada
de ejecución, los avisos y el mazo completo agrupado por función. Pensada para leerla
una vez y entender el mazo.

![Guía de sinergias](docs/capturas/guia.png)

### La chuleta

Dos caras A4 densas, sin literatura, para imprimir y tener al lado mientras juegas.
Cada línea es una interacción con sus cartas en miniatura y cuándo aplica.

![Chuleta imprimible](docs/capturas/chuleta.png)

---

## De qué se compone

| Pieza | Qué es | Su papel aquí |
|---|---|---|
| `reglas.json` | 37 patrones de interacción escritos a mano | **Lo que alguien enseñó.** Profundo pero estrecho: solo encuentra lo que está escrito. |
| `lexico.json` | 23 conceptos de recurso | **Lo que se deduce.** No describe parejas de cartas sino recursos: quién los produce, quién los premia y quién los rompe. Cubre cualquier mazo, aunque más en superficie. |
| El motor | `reglas.py` y su gemelo `motor.js` | Cruza el mazo con los patrones y devuelve las candidatas, cada una **con la frase de oráculo que la disparó**. |
| `scryfall.py` | Cliente de la API de Scryfall, con caché en disco | **La fuente de verdad.** Todo lo que se afirma sale de aquí, nunca de la memoria de un modelo. |
| Los renderizadores | `guia.js`, `chuleta.js`, `grafo.js` | Convierten el análisis en HTML autónomo. Una sola implementación, compartida por la web y la terminal. |
| El servidor MCP | `server.py` | **El enchufe con Claude.** Expone las herramientas para que el modelo pueda llamarlas. |
| Las herramientas | Ocho funciones — [tabla completa abajo](#herramientas-mcp) | Lo que Claude *puede hacer*: resolver, detectar, listar reglas, renderizar cada documento. |
| La skill | `skill/SKILL.md` | Lo que Claude *debe saber*: qué verificar antes de afirmar nada, qué documento pide cada situación, cómo redactar. |
| El CLI | `cli.py` | Los mismos tres documentos sin pasar por Claude. |
| La web | `docs/` | Todo lo anterior en el navegador, sin instalar nada. |

**Qué es MCP.** El Model Context Protocol es un estándar abierto para que un modelo pueda
llamar a programas externos. Aquí el reparto es deliberado: **el servidor aporta los
hechos, el modelo aporta el criterio.** Por eso `detectar_sinergias` no devuelve prosa
cerrada, sino candidatas con su evidencia: los datos los pone el motor, la redacción y el
juicio los pone Claude.

**Qué es la skill.** Un archivo de instrucciones que Claude lee cuando la tarea lo pide.
Si las herramientas le dan *capacidad*, la skill le da *criterio*: le prohíbe afirmar nada
de memoria, le dice cuándo generar cada documento y cómo escribir los pasos. Funciona sin
ella; con ella los análisis salen bastante mejor.

### Qué necesitas según cómo lo uses

| Si lo usas… | Te hace falta |
|---|---|
| Desde la web | Nada — solo el navegador |
| Desde la terminal | Python y el paquete |
| Desde Claude | Python, el paquete y el conector MCP · la skill es opcional y recomendada |

---

## Instalación

Elige el camino según cómo quieras usarlo. **La web no requiere instalar nada**; el resto
depende de si quieres usarlo desde Claude o desde la terminal.

| Quiero… | Ve a |
|---|---|
| Probarlo ahora mismo, sin instalar | [La web](#la-web-nada-que-instalar) |
| Pedírselo a Claude en lenguaje natural | [Claude Desktop](#claude-desktop) · [Claude Code](#claude-code) |
| Usarlo desde otro programa con soporte MCP | [Otros clientes MCP](#otros-clientes-mcp) |
| Generar los HTML desde la terminal | [Línea de comandos](#línea-de-comandos) |

### Requisito previo (salvo para la web)

Todo lo demás necesita **Python 3.10 o superior**. La forma más cómoda de ejecutarlo es
con [`uv`](https://docs.astral.sh/uv/), que descarga y aísla el proyecto por ti sin que
tengas que crear entornos a mano:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

En macOS también vale `brew install uv`. Si prefieres no instalar `uv`, más abajo tienes
[la alternativa con `pip`](#alternativa-sin-uv).

---

### La web (nada que instalar)

<https://grutino.github.io/mtg-forja/>

Pegas la lista, pulsas **Analizar mazo** y sale el mapa. Desde ahí, los botones **Guía** y
**Chuleta** generan los otros dos documentos. Todo ocurre en tu navegador; no se envía nada
a ningún servidor salvo la consulta de cartas a Scryfall. Es la forma más rápida de ver si
el proyecto te sirve.

> Los archivos que descarga la web son **exactamente los mismos** que genera la línea de
> comandos: el mismo renderizador, incrustado en un HTML autónomo.

---

### Claude Desktop

1. Abre el archivo de configuración de conectores:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

   Si no existe, créalo con ese contenido. Si ya tienes otros conectores, añade solo la
   entrada `"mtg-forja"` dentro del `mcpServers` que ya tengas.

2. Pega esto:

```json
{
  "mcpServers": {
    "mtg-forja": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/grutino/mtg-forja", "mtg-forja-mcp"],
      "env": { "MTG_FORJA_SALIDA": "/ruta/donde/quieres/los/html" }
    }
  }
}
```

   Cambia `/ruta/donde/quieres/los/html` por una carpeta tuya real (por ejemplo
   `/Users/tunombre/Documents/mazos`). Ahí es donde aparecerán los documentos generados.

3. **Cierra Claude Desktop del todo y vuelve a abrirlo.** No basta con cerrar la ventana.

4. Comprueba que ha cargado: en el icono de conectores debe aparecer `mtg-forja` con sus
   ocho herramientas. Si no sale, mira [Si algo falla](#si-algo-falla).

5. Instala además la skill de [`skill/SKILL.md`](skill/SKILL.md) para que Claude sepa
   **cómo** usar las herramientas: qué verificar, cómo redactar los pasos y cuándo
   generar cada documento. Sin ella funciona, pero con ella los textos salen bastante
   mejor.

---

### Claude Code

Desde la terminal, en cualquier carpeta:

```bash
claude mcp add mtg-forja --scope user --env MTG_FORJA_SALIDA=/ruta/donde/quieres/los/html -- uvx --from git+https://github.com/grutino/mtg-forja mtg-forja-mcp
```

`--scope user` lo deja disponible en todos tus proyectos. Si prefieres tenerlo solo en un
proyecto concreto, usa `--scope project`: se guardará en un `.mcp.json` en la raíz del
repositorio, que puedes commitear para que lo tenga todo tu equipo.

Ese `.mcp.json` es exactamente el mismo formato que el de Claude Desktop, así que también
puedes escribirlo a mano:

```json
{
  "mcpServers": {
    "mtg-forja": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/grutino/mtg-forja", "mtg-forja-mcp"],
      "env": { "MTG_FORJA_SALIDA": "/ruta/donde/quieres/los/html" }
    }
  }
}
```

---

### Otros clientes MCP

El servidor habla **MCP sobre stdio**, que es el transporte estándar. Sirve tal cual en
cualquier programa que soporte MCP —Cursor, Windsurf, Zed, VS Code con una extensión
compatible, LM Studio y demás—. Casi todos usan el mismo formato que Claude Desktop; si
el tuyo pide los campos por separado, esta es la equivalencia:

| Campo | Valor |
|---|---|
| Transporte | `stdio` |
| Comando | `uvx` |
| Argumentos | `--from` · `git+https://github.com/grutino/mtg-forja` · `mtg-forja-mcp` |
| Variable de entorno | `MTG_FORJA_SALIDA` = la carpeta donde quieres los HTML |

Consulta la documentación de tu cliente para saber dónde vive su archivo de configuración;
el bloque `mcpServers` de arriba suele copiarse sin cambios.

#### Alternativa sin `uv`

Si no quieres instalar `uv`, instala el paquete en un entorno propio y apunta al ejecutable
por su ruta absoluta:

```bash
python3 -m venv ~/.venvs/mtg-forja
~/.venvs/mtg-forja/bin/pip install git+https://github.com/grutino/mtg-forja
```

Y en la configuración, en lugar de `uvx`:

```json
{
  "mcpServers": {
    "mtg-forja": {
      "command": "/Users/tunombre/.venvs/mtg-forja/bin/mtg-forja-mcp",
      "args": [],
      "env": { "MTG_FORJA_SALIDA": "/ruta/donde/quieres/los/html" }
    }
  }
}
```

Usa siempre la ruta absoluta: los clientes MCP no heredan tu `PATH`, y ese es el motivo
más común de que un servidor no arranque.

---

### Línea de comandos

Sin instalar nada de forma permanente:

```bash
uvx --from git+https://github.com/grutino/mtg-forja mtg-forja mazo.txt -n "Mi mazo" -o salida
```

O instalándolo de una vez:

```bash
pip install git+https://github.com/grutino/mtg-forja
mtg-forja mazo.txt -n "Mi mazo" -o salida
```

Genera `salida/guia.html`, `salida/chuleta.html` y `salida/mapa.html`.

---

## Cómo se usa

### Desde Claude

Una vez instalado el conector, pídeselo en lenguaje natural y pégale la lista:

> «Analiza este mazo y hazme el mapa y la chuleta:
> 4 Cleansing Wildfire
> 4 Cascading Cataracts
> …»

Claude resolverá las cartas contra Scryfall, buscará los patrones de interacción y
generará los HTML en la carpeta que pusiste en `MTG_FORJA_SALIDA`. Vale el formato de
exportación de MTG Arena, Moxfield, Archidekt, MTGO, el CSV de ManaBox, o una carta por línea.

Cosas que puedes pedirle, ya que las herramientas están separadas a propósito:

- «¿Qué sinergias detecta este mazo?» — solo el análisis, sin generar documentos.
- «Enséñame las reglas que conoce el motor» — el catálogo de patrones.
- «Genérame solo la chuleta» — un único documento.
- «¿Por qué dice que estas dos cartas se estorban?» — cada sinergia viene con **la frase
  de oráculo exacta que la disparó**, así que puedes auditar el razonamiento.

### Desde la línea de comandos

```bash
mtg-forja mazo.txt -n "Mi mazo" -o salida
```

| Opción | Qué hace |
|---|---|
| `mazo.txt` | Archivo con la lista. Usa `-` para leer de la entrada estándar. |
| `-n`, `--nombre` | Nombre del mazo, el que sale en los títulos. |
| `-o`, `--salida` | Carpeta de destino. |
| `--json` | Vuelca además el documento en JSON, por si quieres procesarlo tú. |

Abre los tres HTML en el navegador. Son autónomos: puedes moverlos, enviarlos por correo
o imprimir la chuleta directamente desde el navegador.

### Desde la web

1. Entra en <https://grutino.github.io/mtg-forja/>
2. Pega la lista, o pulsa **Cargar ejemplo** para ver cómo funciona con un mazo de prueba.
3. Pulsa **Analizar mazo**.
4. Pulsa cualquier carta del grafo para aislar sus conexiones; arrastra para recolocar,
   rueda del ratón para acercar y los botones de arriba para filtrar por función.
5. Los botones **Guía** y **Chuleta**, arriba a la derecha, abren esos documentos en una
   pestaña nueva. Guárdalos con Ctrl/Cmd + S, o imprime la chuleta directamente: está
   maquetada en A4 y sale bien del navegador sin tocar nada.

---

## Si algo falla

| Síntoma | Causa habitual |
|---|---|
| El conector no aparece en Claude | No reiniciaste del todo la aplicación; ciérrala por completo y vuelve a abrirla. |
| «command not found: uvx» en los logs | `uv` no está instalado, o el cliente no ve tu `PATH`. Usa [la alternativa sin `uv`](#alternativa-sin-uv) con ruta absoluta. |
| El JSON no se acepta | Suele ser una coma de más o de menos. Pégalo en un validador de JSON. |
| Los HTML no aparecen | `MTG_FORJA_SALIDA` apunta a una carpeta que no existe. Créala o cambia la ruta. |
| Una carta sale «sin resolver» | Revisa la grafía del nombre. Los acentos no importan, pero un nombre mal escrito sí. |
| Las imágenes de carta tardan | Se piden a Scryfall según hacen falta. Con conexión lenta se ven en gris un momento. |

---

## Herramientas MCP

| Herramienta | Qué hace |
|---|---|
| `resolver_mazo` | Resuelve la lista contra Scryfall y devuelve el oráculo real. |
| `radiografia_del_mazo` | Los hechos objetivos: a quién alcanza cada efecto, qué tipos menciona, qué zonas toca, y si el mazo tiene fuentes de color para lo que él mismo exige. |
| `detectar_sinergias` | Busca patrones de interacción y devuelve candidatas **con la frase de oráculo que disparó cada una**. |
| `listar_reglas` | Enseña los patrones que conoce el motor. |
| `render_guia` / `render_chuleta` / `render_mapa` | Generan cada HTML a partir del documento. |
| `analizar` | Atajo: hace todo de una pasada con los textos automáticos. |

El reparto es deliberado: **el servidor aporta los hechos, el modelo aporta el criterio.**
Por eso `detectar_sinergias` devuelve borradores con evidencia en lugar de prosa cerrada.

---

## Cómo funciona el motor

`src/mtg_forja/reglas.json` es una lista de **patrones genéricos de interacción**. No sabe
nada de cartas concretas: describe formas. Por ejemplo, «una carta que destruye una tierra
y roba» más «una tierra indestructible» es una sinergia de rampa, se llamen como se llamen.

```json
{
  "id": "tierra-indestructible-cantrip",
  "nombre": "Rampa y robo con tierra indestructible",
  "fuerza": 3,
  "piezas": [
    {"rol": "a", "oracle": "destroy target land",
     "oracle2": "search their library for a basic land", "oracle3": "draw a card"},
    {"rol": "b", "tipo": "Land", "oracle": "indestructible"}
  ],
  "resumen": "{a} apuntado a tu propia {b} no la destruye, pero…"
}
```

Campos disponibles en cada pieza: `oracle`, `oracle2`, `oracle3`, `no_oracle`, `tipo`,
`no_tipo`, `coste`, `mv_min`, `mv_max`, `copias_min`, `copias_max`. A nivel de regla,
`conteo` permite condiciones sobre el mazo entero (`basicas`, `tierras`, `total`).

**Añadir una regla es añadir un objeto a esa lista.** Nada más. Se usa igual desde
Python y desde el navegador, porque las dos mitades leen el mismo archivo.

### Hasta dónde llega cada camino

Conviene decirlo claro, porque determina qué esperar:

| Camino | Alcance | Profundidad |
|---|---|---|
| Reglas escritas (`reglas.json`) | solo los arquetipos que alguien escribió | **alta** — ve asimetrías y casos raros |
| Léxico de recursos (`lexico.json`) | **cualquier mazo** | baja — solo flujos de recursos |
| Modelo vía MCP | **cualquier mazo** | **alta** — es como se hizo el análisis original |

Las reglas escritas no salieron de un motor: salieron de un modelo leyendo el oráculo de
cada carta y razonando, y luego alguien congeló esas conclusiones. Por eso ningún motor
de patrones las reproduce. Comprobado: sobre el mazo que originó el proyecto, el léxico
redescubre **1 de las 18** parejas escritas a mano.

Lo que ningún motor puede ver, y sí ve un modelo con el oráculo delante:

- «apaga los artefactos del rival, **pero no los tuyos**» — requiere entender la asimetría
- «el barrido no alcanza a tus planeswalkers» — requiere inferir qué queda **fuera**
- «esa tierra solo es criatura cuando la activas, así que sobrevive» — estados temporales
- «barajar descoloca la carta que pusiste arriba» — posición en la biblioteca

Por eso la herramienta `radiografia_del_mazo` existe: le da al modelo esos hechos —alcance,
tipos que menciona, zonas que toca— para que pueda razonar en vez de adivinar.

**Si quieres el análisis bueno de un mazo que nadie ha visto, usa el camino MCP.** El CLI
y la web no tienen un modelo detrás; ahí el léxico sirve de suelo, para que un mazo
desconocido nunca devuelva una página casi vacía.

### Dos límites que conviene conocer

**El motor solo encuentra lo que se le ha enseñado.** Si analizas un mazo y salen dos
sinergias, casi nunca es un fallo de resolución: es que el paquete no cubre ese
arquetipo todavía. Para comprobarlo, mira `cartas_sin_resolver` en la salida — si viene
vacío, las cartas se leyeron bien y lo que falta son patrones. Escribir la regla que
falta es el trabajo, y es el trabajo que hace crecer esto.

**El banquillo no entra en la detección.** Las cartas de reserva se resuelven contra
Scryfall y aparecen en el documento, pero las reglas solo cruzan el mazo principal. Una
sinergia que dependa de una carta del banquillo no se detecta.

Después de tocar `reglas.json` o cualquiera de los renderizadores `.js`, sincroniza la web:

```bash
python scripts/sync_docs.py
```

---

## Montarlo entero en tu máquina

Si quieres tenerlo **todo funcionando en local** —la web, la línea de comandos y el
servidor MCP— sin depender de GitHub Pages, estos son los pasos completos.

### Requisitos previos

| Necesitas | Para qué | Cómo comprobar que lo tienes |
|---|---|---|
| **Python 3.10 o superior** | El motor, el CLI y el servidor MCP | `python3 --version` |
| **git** | Clonar el repositorio | `git --version` |
| **Un navegador** | Ver la web y los documentos | Cualquiera moderno |
| **Conexión a internet** | Consultar cartas e imágenes en Scryfall | — |

No hace falta Node, ni npm, ni ningún servidor: la web es HTML y JavaScript estáticos, y
el único servidor que se levanta es el que trae Python de serie. Tampoco hace falta `uv`
para esto; `uv` solo simplifica el arranque del conector MCP.

> **Sobre la conexión**: aunque todo corra en tu máquina, los nombres de carta y las
> imágenes se piden a Scryfall. Sin internet, el motor no puede resolver el mazo. Para
> trabajar sin red existe `MTG_FORJA_FIXTURE`, pensado para las pruebas.

### Paso 1 — Clonar e instalar

```bash
git clone https://github.com/grutino/mtg-forja
cd mtg-forja
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

En Windows, la tercera y cuarta línea son `py -m venv .venv` y `.venv\Scripts\activate`.

> El `-e` instala en modo editable: si tocas el código, no hay que reinstalar. Si usas
> conda, crea igualmente el `venv`: mezclar ambos da problemas.

### Paso 2 — Comprobar que funciona

```bash
pip install pytest
pytest -q
```

Deben pasar las pruebas, y no tocan la red: usan el fixture de `ejemplos/`. Si fallan
aquí, no sigas: algo está mal en la instalación, no en tu mazo.

Ahora una prueba de verdad, contra Scryfall:

```bash
mtg-forja ejemplos/prueba.txt -n "Prueba" -o /tmp/forja-prueba
```

Debe imprimir un resumen del tipo `30 cartas · 12 sinergias` y dejar tres HTML en
`/tmp/forja-prueba`. Ábrelos en el navegador.

### Paso 3 — Levantar la web en local

```bash
python scripts/sync_docs.py
python -m http.server -d docs 8000
```

Y abre <http://localhost:8000>.

Eso es todo: ya tienes la web completa —mapa, guía y chuleta— corriendo en tu máquina, sin
pasar por GitHub. `sync_docs.py` copia a `docs/` el paquete de reglas y los renderizadores
que comparten las dos mitades del proyecto; **ejecútalo siempre que toques `reglas.json` o
cualquiera de los `.js` de `src/mtg_forja/render/`**, o la web se quedará con la versión
vieja.

Para parar el servidor, Ctrl + C.

### Paso 4 (opcional) — Conectar tu Claude a esta copia local

Si quieres que Claude use **tu** copia en lugar de descargarla de GitHub, apunta el
conector al ejecutable de tu entorno virtual, con ruta absoluta:

```json
{
  "mcpServers": {
    "mtg-forja": {
      "command": "/ruta/completa/a/mtg-forja/.venv/bin/mtg-forja-mcp",
      "args": [],
      "env": { "MTG_FORJA_SALIDA": "/ruta/donde/quieres/los/html" }
    }
  }
}
```

Averigua la ruta exacta con `which mtg-forja-mcp` (con el entorno activado). En Windows es
`.venv\Scripts\mtg-forja-mcp.exe`. Así los cambios que hagas en el código los ve Claude en
cuanto reinicies la aplicación.

### Resumen

```bash
git clone https://github.com/grutino/mtg-forja && cd mtg-forja
python3 -m venv .venv && source .venv/bin/activate
pip install -e . pytest
pytest -q                                    # 6 pruebas, sin red
python scripts/sync_docs.py                  # sincroniza reglas y renderizadores
python -m http.server -d docs 8000           # web completa en localhost:8000
```

---

## Desarrollo

```bash
# prueba sin red, con el fixture de ejemplo
MTG_FORJA_FIXTURE=ejemplos/fixture-pruebas.json mtg-forja ejemplos/prueba.txt -o /tmp/salida
```

Variables de entorno:

| | |
|---|---|
| `MTG_FORJA_CACHE` | Dónde cachear las cartas (por defecto `~/.cache/mtg-forja`). |
| `MTG_FORJA_SALIDA` | Carpeta por defecto de los HTML del servidor MCP. |
| `MTG_FORJA_FIXTURE` | Archivo JSON de cartas para trabajar sin red, en pruebas. |

### Publicar la web

En los ajustes del repositorio, **Pages → Source: Deploy from a branch → `main` / `docs`**.

---

## Estructura

```
src/mtg_forja/
  modelo.py        cartas, mazo, parseo de listas (Arena, Moxfield, Archidekt, ManaBox…)
  scryfall.py      resolución con caché en disco y modo sin red
  reglas.json      el paquete de patrones — aquí es donde se crece
  reglas.py        motor de detección
  render/
    comun.js       paleta y utilidades compartidas
    guia.js        \
    chuleta.js      >  el diseño de los tres documentos, en una sola implementación
    grafo.js       /
    guia.py        \
    chuleta.py      >  cáscaras: incrustan el JS y el documento en un HTML autónomo
    mapa.py        /
  server.py        servidor MCP
  cli.py           línea de comandos
docs/              web de GitHub Pages (lee los mismos reglas.json y renderizadores)
docs/capturas/     las imágenes de este README
skill/SKILL.md     cómo debe usar Claude todo lo anterior
```

**Los renderizadores no están duplicados.** El diseño de cada documento existe una sola
vez, en su `.js`. Python no lo reimplementa: incrusta ese archivo junto al documento en
JSON y deja que el navegador lo pinte. Por eso la web y la línea de comandos producen el
mismo archivo, byte a byte, y no pueden separarse con el tiempo. `sync_docs.py` es lo que
mantiene `docs/` al día.

---

## Créditos y licencia

Código bajo licencia MIT, en `LICENSE`.

Los datos y las imágenes de carta vienen de la API pública de Scryfall y se **enlazan**,
no se copian; las capturas de este README son la excepción, por necesidad. Magic: The
Gathering es propiedad de Wizards of the Coast. Este es un proyecto de aficionado sin
ánimo de lucro, amparado por la Fan Content Policy de Wizards, y no está patrocinado ni
respaldado por Wizards ni por Scryfall.

Si usas la API de Scryfall en tu propio despliegue, respeta su
[ritmo de peticiones](https://scryfall.com/docs/api) (una cada 50-100 ms).
