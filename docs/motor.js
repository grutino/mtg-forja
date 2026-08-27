/* MTG Forja — versión de navegador del motor.
   Es un puerto fiel de src/mtg_forja/{modelo,scryfall,reglas}.py y consume el
   MISMO reglas.json, para que la web y el servidor MCP nunca se contradigan. */
(function (global) {
  "use strict";

  /* Comparación por punto de código, como la de Python. localeCompare colaciona
     según el idioma del navegador y ordenaría las tildes distinto que el CLI. */
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

  const API = "https://api.scryfall.com/cards/collection";
  const LOTE = 75;
  const CABECERAS = new Set([
    "deck", "mazo", "sideboard", "banquillo", "reserva",
    "commander", "companion", "maybeboard", "about", "name",
  ]);
  // La sección "About" de Arena trae "Name <nombre del mazo>" en una línea suelta.
  // Exige que no haya cantidad delante para no comerse un "1 Nameless Inversion".
  const META_ARENA = /^(name|layout)\s+\S/i;
  const LINEA = /^\s*(?:(\d+)\s*[xX]?\s+)?([^([\n]+?)(?:\s*\([A-Za-z0-9_]{2,6}\)\s*[\w-]*)?\s*$/;

  const COLOR_ROL = {
    motor: { n: "Motor", c: "#D8B15E" },
    amenaza: { n: "Amenaza", c: "#C1462A" },
    respuesta: { n: "Respuesta", c: "#D9D0C0" },
    tierra: { n: "Tierra", c: "#7E8C5C" },
  };

  const MARCAS = /\*[A-Za-z]{1,2}\*/g;       // *F* / *E* de Moxfield
  const CATEGORIA = /\[([^\]]*)\]/g;          // [Burn] / [Maybeboard{noPrice}] de Archidekt
  const FUERA_DEL_MAZO = ["maybeboard", "sideboard", "considering"];

  /** Exportación de ManaBox y similares: cabecera con Name y Quantity. */
  function csv(texto) {
    const lineas = texto.split(/\r?\n/).filter((l) => l.trim());
    if (!lineas.length || !lineas[0].includes(",")) return null;
    const cab = lineas[0].split(",").map((c) => c.trim().replace(/^"|"$/g, "").toLowerCase());
    const iN = cab.indexOf("name");
    if (iN === -1) return null;
    const iC = ["quantity", "count", "qty"].map((c) => cab.indexOf(c)).find((i) => i !== -1);
    const iS = ["section", "board"].map((c) => cab.indexOf(c)).find((i) => i !== -1);
    const campos = (l) => (l.match(/("([^"]*)")|([^,]*)/g) || [])
      .filter((_, i) => i % 2 === 0).map((c) => c.replace(/^"|"$/g, "").trim());
    const salida = [];
    for (const l of lineas.slice(1)) {
      const f = campos(l);
      const nombre = (f[iN] || "").split("//")[0].trim();
      if (!nombre) continue;
      const n = iC !== undefined ? parseInt(f[iC], 10) : 1;
      salida.push({
        copias: Number.isFinite(n) && n > 0 ? n : 1,
        nombre,
        banquillo: iS !== undefined && FUERA_DEL_MAZO.includes((f[iS] || "").toLowerCase()),
      });
    }
    return salida.length ? salida : null;
  }

  function parsear(texto) {
    const enCsv = csv(texto);
    if (enCsv) return enCsv;

    const salida = [];
    let banquillo = false;
    for (const cruda of texto.split(/\r?\n/)) {
      let linea = cruda.trim();
      if (!linea || linea.startsWith("#") || linea.startsWith("//")) continue;
      const etiquetas = (linea.match(CATEGORIA) || []).join(" ").toLowerCase();
      const fuera = FUERA_DEL_MAZO.some((p) => etiquetas.includes(p));
      linea = linea.replace(CATEGORIA, " ").replace(MARCAS, " ").trim();
      if (!linea) continue;
      const clave = linea.toLowerCase().replace(/:$/, "");
      if (META_ARENA.test(linea)) continue;
      if (CABECERAS.has(clave)) {
        banquillo = ["sideboard", "banquillo", "reserva"].includes(clave);
        continue;
      }
      const m = LINEA.exec(linea);
      if (!m) continue;
      const nombre = m[2].split("//")[0].trim();
      if (!nombre) continue;
      salida.push({ copias: parseInt(m[1] || "1", 10), nombre, banquillo: banquillo || fuera });
    }
    return salida;
  }

  function rol(carta) {
    const t = carta.tipo, o = carta.oraculo;
    if (/Land/i.test(t)) {
      return /becomes? an? .{0,60}creature/i.test(o) ? "amenaza" : "tierra";
    }
    if (/Planeswalker/i.test(t)) return "amenaza";
    if (/you win the game/i.test(o)) return "amenaza";
    if (/\bdraw\b|scry|surveil|look at the top/i.test(o) &&
        /Artifact|Enchantment|Instant|Sorcery/i.test(t)) return "motor";
    if (/destroy|exile|damage to|counter target|-\d+\/-\d+/i.test(o)) return "respuesta";
    if (/Creature/i.test(t)) return "amenaza";
    return "motor";
  }

  function aplanar(bruto) {
    const caras = bruto.card_faces || [];
    if (caras.length && !bruto.oracle_text) {
      return {
        oraculo: caras.map((f) => f.oracle_text || "").join("\n//\n"),
        coste: caras[0].mana_cost || bruto.mana_cost || "",
        tipo: caras.map((f) => f.type_line || "").join(" // "),
      };
    }
    return {
      oraculo: bruto.oracle_text || "",
      coste: bruto.mana_cost || "",
      tipo: bruto.type_line || "",
    };
  }

  // Scryfall acepta el nombre sin tildes pero responde con la grafía canónica:
  // pides "Palantir of Orthanc" y te devuelve "Palantír of Orthanc". Comparados
  // como texto no casan y la carta se descarta, así que plegamos acentos y
  // puntuación para que las dos grafías caigan en la misma clave.
  function clave(nombre) {
    return nombre
      .normalize("NFKD")
      .replace(/\p{M}/gu, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  async function resolver(texto) {
    const entradas = parsear(texto);
    const unicos = [...new Set(entradas.map((e) => e.nombre))];
    const encontrados = new Map();

    for (let i = 0; i < unicos.length; i += LOTE) {
      const trozo = unicos.slice(i, i + LOTE);
      const r = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifiers: trozo.map((n) => ({ name: n })) }),
      });
      if (!r.ok) throw new Error("Scryfall ha respondido " + r.status);
      const datos = await r.json();
      for (const bruto of datos.data || []) {
        encontrados.set(clave(bruto.name.split("//")[0]), bruto);
      }
      if (i + LOTE < unicos.length) await new Promise((s) => setTimeout(s, 120));
    }

    const cartas = [];
    const vistos = new Map();
    const no_resueltas = [];
    for (const ent of entradas) {
      const bruto = encontrados.get(clave(ent.nombre));
      let carta;
      if (!bruto) {
        if (!no_resueltas.includes(ent.nombre)) no_resueltas.push(ent.nombre);
        continue;
      }
      const plano = aplanar(bruto);
      carta = {
        nombre: bruto.name.split("//")[0].trim(),
        copias: ent.copias,
        banquillo: ent.banquillo,
        coste: plano.coste,
        mv: bruto.cmc || 0,
        tipo: plano.tipo,
        oraculo: plano.oraculo,
        produce_mana: bruto.produced_mana || [],
      };
      carta.rol = rol(carta);
      carta.es_tierra = /Land/i.test(carta.tipo);
      carta.es_basica = carta.es_tierra && /Basic/i.test(carta.tipo);
      const k = clave(carta.nombre) + "|" + ent.banquillo;
      if (vistos.has(k)) vistos.get(k).copias += ent.copias;
      else { vistos.set(k, carta); cartas.push(carta); }
    }

    const principal = cartas.filter((c) => !c.banquillo);
    const suma = (f) => principal.filter(f).reduce((a, c) => a + c.copias, 0);
    const curva = {};
    for (const c of principal) {
      if (c.es_tierra) continue;
      const k = c.mv < 7 ? String(Math.trunc(c.mv)) : "7+";
      curva[k] = (curva[k] || 0) + c.copias;
    }
    return {
      cartas, principal, no_resueltas,
      total: suma(() => true),
      tierras: suma((c) => c.es_tierra),
      basicas: suma((c) => c.es_basica),
      curva: Object.fromEntries(Object.entries(curva).sort(
        (a, b) => (a[0] === "7+") - (b[0] === "7+") || a[0].localeCompare(b[0]))),
    };
  }

  let _reglas = null;
  async function reglas() {
    if (_reglas) return _reglas;
    const r = await fetch("reglas.json");
    if (!r.ok) throw new Error("No se ha podido cargar el paquete de reglas");
    _reglas = (await r.json()).reglas;
    return _reglas;
  }

  function frase(texto, patron) {
    const m = new RegExp(patron, "is").exec(texto);
    if (!m) return "";
    const ini = texto.lastIndexOf(".", m.index) + 1;
    let fin = texto.indexOf(".", m.index + m[0].length);
    fin = fin === -1 ? texto.length : fin + 1;
    return texto.slice(ini, fin).split(/\s+/).join(" ").trim().slice(0, 240);
  }

  function casa(carta, pieza) {
    const re = (p, s) => new RegExp(p, "is").test(s);
    if (pieza.tipo && !re(pieza.tipo, carta.tipo)) return null;
    if (pieza.no_tipo && re(pieza.no_tipo, carta.tipo)) return null;
    if (pieza.coste && !re(pieza.coste, carta.coste || "")) return null;
    if (pieza.mv_min !== undefined && carta.mv < pieza.mv_min) return null;
    if (pieza.mv_max !== undefined && carta.mv > pieza.mv_max) return null;
    if (pieza.fuerza_min !== undefined) {
      const f = parseFloat(carta.fuerza);
      // Fuerza variable ("*", "1+*"): no se puede afirmar el umbral.
      if (!Number.isFinite(f) || f < pieza.fuerza_min) return null;
    }
    if (pieza.copias_min !== undefined && carta.copias < pieza.copias_min) return null;
    if (pieza.copias_max !== undefined && carta.copias > pieza.copias_max) return null;
    let evidencia = "";
    for (const clave of ["oracle", "oracle2", "oracle3"]) {
      if (!pieza[clave]) continue;
      if (!re(pieza[clave], carta.oraculo)) return null;
      if (!evidencia) evidencia = frase(carta.oraculo, pieza[clave]);
    }
    if (pieza.no_oracle && re(pieza.no_oracle, carta.oraculo)) return null;
    if (pieza.fuerza_min !== undefined && !evidencia) {
      return `${carta.tipo} · fuerza ${carta.fuerza}`;
    }
    return evidencia || carta.oraculo.split(/\s+/).join(" ").slice(0, 200) || carta.tipo;
  }

  function detectar(mazo, listaReglas) {
    const salida = [];
    const valores = { basicas: mazo.basicas, tierras: mazo.tierras, total: mazo.total };

    for (const regla of listaReglas) {
      if (regla.conteo && !regla.conteo.every((c) => {
        const v = valores[c.que] || 0;
        return (c.max === undefined || v <= c.max) && (c.min === undefined || v >= c.min);
      })) continue;

      const porRol = {};
      let completa = true;
      for (const pieza of regla.piezas) {
        const aciertos = [];
        for (const carta of mazo.principal) {
          const ev = casa(carta, pieza);
          if (ev !== null) aciertos.push({ carta, ev });
        }
        if (!aciertos.length) { completa = false; break; }
        porRol[pieza.rol] = aciertos;
      }
      if (!completa) continue;

      // Una regla puede aplicarse a varias cartas a la vez. Emitir solo la pareja
      // "mejor" escondía el resto: con Cleansing Wildfire, Cascading Cataracts se
      // llevaba la única línea y Rustvale Bridge —cuatro copias, igual de
      // indestructible— se quedaba suelto. El orden es el de reglas.py.
      const roles = regla.piezas.map((p) => p.rol);
      const opciones = roles.map((r) => porRol[r].slice().sort(
        (x, y) => y.carta.copias - x.carta.copias ||
                  x.carta.mv - y.carta.mv ||
                  cmp(x.carta.nombre, y.carta.nombre)));

      const vistas = new Set();
      let combo = new Array(opciones.length).fill(0);
      const total = opciones.reduce((n, o) => n * o.length, 1);
      for (let k = 0; k < total; k++) {
        // índice k desplegado en el mismo orden que itertools.product: el último rol
        // es el que más rápido varía.
        let resto = k;
        for (let i = opciones.length - 1; i >= 0; i--) {
          combo[i] = resto % opciones[i].length;
          resto = Math.floor(resto / opciones[i].length);
        }
        const elegidas = opciones.map((o, i) => o[combo[i]]);
        const nombres = elegidas.map((e) => e.carta.nombre);
        if (new Set(nombres).size < nombres.length) continue;
        const clave = nombres.slice().sort(cmp).join(" ");
        if (vistas.has(clave)) continue;
        vistas.add(clave);

        const sust = {};
        roles.forEach((r, i) => { sust[r] = nombres[i]; });
        const fmt = (t) => (t || "").replace(/\{(\w+)\}/g, (m, kk) => sust[kk] !== undefined ? sust[kk] : m);
        const evidencia = {};
        elegidas.forEach((e) => { evidencia[e.carta.nombre] = e.ev; });

        salida.push({
          id: [regla.id, ...nombres].join("::"),
          nombre: regla.nombre, bloque: regla.bloque || "Otros",
          tipo: regla.tipo || "sinergia", fuerza: regla.fuerza || 2, turno: regla.turno || "",
          piezas: nombres,
          resumen: fmt(regla.resumen), pasos: (regla.pasos || []).map(fmt), evidencia,
        });
        // Hay reglas que hablan del mazo entero, no de una pareja.
        if (regla.una_vez || vistas.size >= TOPE_POR_REGLA) break;
      }
    }
    const orden = { sinergia: 0, aviso: 1, conflicto: 2 };
    // Las tres claves y el criterio de cadena son los de reglas.py: sin el
    // desempate por bloque, la web ordenaba las sinergias distinto que el CLI.
    salida.sort((a, b) => (orden[a.tipo] ?? 3) - (orden[b.tipo] ?? 3) ||
                          b.fuerza - a.fuerza || cmp(a.bloque, b.bloque));
    return salida;
  }

  function documento(mazo, sinergias, titulo) {
    return {
      titulo: titulo || "Mazo",
      subtitulo: `${mazo.total} cartas · ${mazo.tierras} tierras`,
      curva: mazo.curva,
      cartas: mazo.principal.map((c) => ({
        nombre: c.nombre, copias: c.copias, coste: c.coste, mv: c.mv,
        tipo: c.tipo, rol: c.rol, produce_mana: c.produce_mana || [], estrategia: "",
      })),
      sinergias, orden: [], reglas_oro: [], no_resueltas: mazo.no_resueltas,
    };
  }

  function datosGrafo(doc) {
    const idx = Object.fromEntries(doc.cartas.map((c) => [c.nombre, c]));
    const usadas = new Set();
    doc.sinergias.forEach((s) => s.piezas.forEach((p) => usadas.add(p)));
    // Todas las cartas entran, tengan sinergia o no: una carta suelta también
    // dice algo del mazo, y antes desaparecía sin más.
    doc.cartas.forEach((c) => usadas.add(c.nombre));

    const cartas = {};
    for (const nombre of [...usadas].sort()) {
      const c = idx[nombre] || {};
      let evidencia = "";
      for (const s of doc.sinergias) {
        if (s.evidencia && s.evidencia[nombre]) { evidencia = s.evidencia[nombre]; break; }
      }
      let corto = nombre.split(",")[0];
      if (corto.length > 20) corto = corto.slice(0, 19) + "…";
      cartas[nombre] = {
        copias: c.copias || 1, coste: c.coste || "", tipo: c.tipo || "",
        rol: c.rol || "motor", corto, estrategia: c.estrategia || "", evidencia,
        };
    }

    const enlaces = [];
    for (const s of doc.sinergias) {
      for (let i = 0; i + 1 < s.piezas.length; i++) {
        enlaces.push({
          a: s.piezas[i], b: s.piezas[i + 1], f: s.fuerza, t: s.nombre, d: s.resumen,
          r: (s.tipo === "conflicto" || s.tipo === "aviso") ? 1 : 0,
        });
      }
    }
    return { cartas, enlaces, roles: COLOR_ROL };
  }


  /* ---- Motor deductivo: puerto fiel de src/mtg_forja/lexico.py ----------------
     Las reglas con nombre solo encuentran lo que alguien escribió. Esto deduce
     sinergias cruzando quién produce un recurso con quién lo premia, y conflictos
     cruzando quién lo rompe con quién depende de él. Cualquier cambio aquí tiene
     que ir también en lexico.py: la prueba de paridad compara las dos salidas. */

  /* Los topes evitan la maraña, pero no deben esconder el motor del mazo: una carta
   que premia cada hechizo que lanzas SÍ tiene sinergia con los diez. El límite es
   por carta, no por concepto, y se cuenta aparte para sinergias y conflictos. */
// Tope de parejas por regla, igual que reglas.py.
const TOPE_POR_REGLA = 12;
const TOPE_SINERGIAS = 40, TOPE_CONFLICTOS = 10, POR_CARTA = 12;
  const RECORDATORIO = /\([^)]*\)/g;
  let _lexico = null;

  async function lexico() {
    if (_lexico) return _lexico;
    const r = await fetch("lexico.json");
    if (!r.ok) throw new Error("No se ha podido cargar el léxico de recursos");
    _lexico = (await r.json()).conceptos;
    return _lexico;
  }

  function textoReglas(oraculo, nombre) {
    let t = String(oraculo || "").replace(RECORDATORIO, " ");
    const formas = [...new Set([nombre, String(nombre || "").split(",")[0].trim()])]
      .filter(Boolean).sort((a, b) => b.length - a.length);
    for (const f of formas) {
      t = t.replace(new RegExp("\\b" + f.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "g"),
                    " esta carta ");
    }
    return t.split(/\s+/).filter(Boolean).join(" ");
  }

  function fraseDe(texto, indice, largo) {
    const ini = texto.lastIndexOf(".", indice) + 1;
    let fin = texto.indexOf(".", indice + largo);
    fin = fin === -1 ? texto.length : fin + 1;
    return texto.slice(ini, fin).split(/\s+/).filter(Boolean).join(" ").slice(0, 240);
  }

  function encajaConcepto(carta, bloque, oraculo) {
    if (!bloque) return "";
    const re = (p, s) => new RegExp(p, "is").test(s);
    if (bloque.tipo && !re(bloque.tipo, carta.tipo)) return "";
    if (bloque.no_tipo && re(bloque.no_tipo, carta.tipo)) return "";
    if (bloque.mv_min !== undefined && carta.mv < bloque.mv_min) return "";
    if (bloque.mv_max !== undefined && carta.mv > bloque.mv_max) return "";
    if (bloque.fuerza_min !== undefined) {
      const f = parseFloat(carta.fuerza);
      // Fuerza variable ("*", "1+*"): no se puede afirmar el umbral.
      if (!Number.isFinite(f) || f < bloque.fuerza_min) return "";
    }
    if (bloque.no_oracle && re(bloque.no_oracle, oraculo)) return "";
    const patrones = bloque.oracle || [];
    if (!patrones.length) {
      if (bloque.fuerza_min !== undefined) return `${carta.tipo} · fuerza ${carta.fuerza}`;
      return (bloque.tipo || bloque.mv_min !== undefined || bloque.mv_max !== undefined)
        ? carta.tipo : "";
    }
    for (const p of patrones) {
      const m = new RegExp(p, "is").exec(oraculo);
      if (m) return fraseDe(oraculo, m.index, m[0].length);
    }
    return "";
  }

  const BLOQUE_LEX = { sinergia: "Motor", conflicto: "Conflictos" };

  const TIPOS = ["artifact", "enchantment", "creature", "planeswalker",
                 "instant", "sorcery", "land", "battle"];

  /** Los tipos de carta de una línea, sin subtipos ni supertipos. */
  function tipos(tipo) {
    const cabeza = tipo.split("—")[0].toLowerCase();
    return TIPOS.filter((t) => cabeza.includes(t));
  }

  /** Los subtipos de una línea de tipo: lo que va tras el guion largo. */
  function subtipos(tipo) {
    if (!tipo.includes("—")) return [];
    return tipo.split("—").pop().split(/\s+/).filter(Boolean).map((x) => x.toLowerCase());
  }

  function detectarLexico(mazo, conceptos) {
    const limpio = {};
    for (const c of mazo.principal) limpio[c.nombre] = textoReglas(c.oraculo, c.nombre);

    const salida = [];
    for (const c of conceptos) {
      const reparto = { produce: [], premia: [], rompe: [] };
      for (const papel of ["produce", "premia", "rompe"]) {
        for (const carta of mazo.principal) {
          const ev = encajaConcepto(carta, c[papel], limpio[carta.nombre]);
          if (ev) reparto[papel].push([carta, ev]);
        }
      }
      // Un concepto tribal no puede casar cualquier criatura con cualquier premio:
      // el subtipo de la carta tiene que ser el que menciona la otra. Sin esto, un
      // Human Monk salía emparejado con un premio a los Dragones.
      const emparejar = c.emparejar_subtipo;
      // Y un tutor solo encuentra lo que dice buscar: "an artifact or enchantment
      // card" casa con Worship, no con Savannah Lions.
      const emparejarTipo = c.emparejar_tipo_buscado;
      const parejas = [];
      for (const [a, eva] of reparto.produce)
        for (const [b, evb] of reparto.premia) {
          if (emparejar && !subtipos(a.tipo).some((s) => evb.toLowerCase().includes(s))) continue;
          if (emparejarTipo && !tipos(b.tipo).some((x) => eva.toLowerCase().includes(x))) continue;
          parejas.push([a, eva, b, evb, "sinergia", "produce", "premia"]);
        }
      for (const [a, eva] of reparto.rompe)
        for (const [b, evb] of reparto.premia) parejas.push([a, eva, b, evb, "conflicto", "rompe", "premia"]);

      for (const [a, eva, b, evb, tipo, blA, blB] of parejas) {
        if (a.nombre === b.nombre) continue;
        const ev = {}; ev[a.nombre] = eva; ev[b.nombre] = evb;
        salida.push({
          id: `${c.id}::${tipo}::${a.nombre}::${b.nombre}`,
          nombre: `${a.nombre} y ${b.nombre}`,
          bloque: BLOQUE_LEX[tipo] || "Motor",
          tipo, turno: "", piezas: [a.nombre, b.nombre], pasos: [], evidencia: ev,
          fuerza: Math.min(4, (c.fuerza || 2) + (Math.min(a.copias, b.copias) >= 3 ? 1 : 0)),
          resumen: `{a} ${(c[blA] || {}).texto || "aporta"} y {b} ${(c[blB] || {}).texto || "lo aprovecha"}.`,
        });
      }
    }

    /* Los conflictos primero, igual que lexico.py: si una pareja sale a la vez como
       sinergia y como conflicto, gana el aviso. */
    salida.sort((x, y) => (x.tipo === "conflicto" ? 0 : 1) - (y.tipo === "conflicto" ? 0 : 1) ||
                          y.fuerza - x.fuerza || cmp(x.id, y.id));
    return podar(salida);
  }

  function podar(lista) {
    const vistas = new Set(), veces = {};
    const cupo = { sinergia: TOPE_SINERGIAS, conflicto: TOPE_CONFLICTOS };
    const fuera = [];
    for (const s of lista) {
      const par = [...s.piezas].sort(cmp).join(" ");
      if (vistas.has(par) || (cupo[s.tipo] || 0) <= 0) continue;
      if (s.piezas.some((n) => (veces[n + "|" + s.tipo] || 0) >= POR_CARTA)) continue;
      vistas.add(par);
      cupo[s.tipo] -= 1;
      for (const n of s.piezas) veces[n + "|" + s.tipo] = (veces[n + "|" + s.tipo] || 0) + 1;
      fuera.push(s);
    }
    return fuera;
  }

  /** El análisis entero: primero lo escrito, después lo deducido. */
  function completo(mazo, listaReglas, conceptos) {
    const nombradas = detectar(mazo, listaReglas);
    const cubiertas = new Set(nombradas.map((s) => [...s.piezas].sort(cmp).join(" ")));
    const deducidas = detectarLexico(mazo, conceptos)
      .filter((s) => !cubiertas.has([...s.piezas].sort(cmp).join(" ")));
    return nombradas.concat(deducidas);
  }

  global.Forja = { parsear, resolver, reglas, lexico, detectar, detectarLexico,
                   completo, documento, datosGrafo, textoReglas };
})(typeof window !== "undefined" ? window : globalThis);
