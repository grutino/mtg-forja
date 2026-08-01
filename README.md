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

| | |
|---|---|
| **Guía** | Página larga con cada sinergia desarrollada: piezas ilustradas, secuencia numerada de la jugada, avisos y el mazo completo agrupado por función. |
| **Chuleta** | Dos caras A4 densas, sin literatura, pensadas para imprimir y tener al lado mientras juegas. |
| **Mapa** | Grafo de fuerzas navegable: pulsas una carta y ves sus conexiones, con las líneas rojas discontinuas marcando lo que se estorba entre sí. |

---

## Uso rápido

### Web

No hay nada que instalar: <https://grutino.github.io/mtg-forja/>

Pegas la lista, pulsas y sale el mapa. Todo ocurre en tu navegador; no se envía nada
a ningún servidor salvo la consulta de cartas a Scryfall.

### Línea de comandos

```bash
uvx --from git+https://github.com/grutino/mtg-forja mtg-forja mazo.txt -n "Mi mazo" -o salida
```

Genera `salida/guia.html`, `salida/chuleta.html` y `salida/mapa.html`.

### Servidor MCP en Claude

Añade esto a la configuración de conectores de Claude Desktop
(`claude_desktop_config.json`):

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

Reinicia Claude y pídele algo como *«analiza este mazo»* pegando la lista.

Instala además la skill de `skill/SKILL.md` para que Claude sepa **cómo** usar las
herramientas: qué verificar, cómo redactar los pasos y cuándo generar cada documento.

---

## Herramientas MCP

| Herramienta | Qué hace |
|---|---|
| `resolver_mazo` | Resuelve la lista contra Scryfall y devuelve el oráculo real. |
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

Después de tocar `reglas.json` o `grafo.js`, sincroniza la web:

```bash
python scripts/sync_docs.py
```

---

## Desarrollo

```bash
git clone https://github.com/grutino/mtg-forja
cd mtg-forja
python -m venv .venv && source .venv/bin/activate
pip install -e .

# prueba sin red, con el fixture de ejemplo
MTG_FORJA_FIXTURE=ejemplos/fixture-pruebas.json mtg-forja ejemplos/prueba.txt -o /tmp/salida

# la web, en local
python scripts/sync_docs.py && python -m http.server -d docs 8000
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
  modelo.py        cartas, mazo, parseo de listas (Arena, Moxfield, texto suelto)
  scryfall.py      resolución con caché en disco y modo sin red
  reglas.json      el paquete de patrones — aquí es donde se crece
  reglas.py        motor de detección
  render/          guía, chuleta, mapa (+ grafo.js, compartido con la web)
  server.py        servidor MCP
  cli.py           línea de comandos
docs/              web de GitHub Pages (lee el mismo reglas.json)
skill/SKILL.md     cómo debe usar Claude todo lo anterior
```

---

## Créditos y licencia

Código bajo licencia MIT, en `LICENSE`.

Los datos y las imágenes de carta vienen de la API pública de Scryfall y se **enlazan**,
no se copian. Magic: The Gathering es propiedad de Wizards of the Coast. Este es un
proyecto de aficionado sin ánimo de lucro, amparado por la Fan Content Policy de Wizards,
y no está patrocinado ni respaldado por Wizards ni por Scryfall.

Si usas la API de Scryfall en tu propio despliegue, respeta su
[ritmo de peticiones](https://scryfall.com/docs/api) (una cada 50-100 ms).
