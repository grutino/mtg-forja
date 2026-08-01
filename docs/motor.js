/* MTG Forja — versión de navegador del motor.
   Es un puerto fiel de src/mtg_forja/{modelo,scryfall,reglas}.py y consume el
   MISMO reglas.json, para que la web y el servidor MCP nunca se contradigan. */
(function (global) {
  "use strict";

  const API = "https://api.scryfall.com/cards/collection";
  const LOTE = 75;
  const CABECERAS = new Set([
    "deck", "mazo", "sideboard", "banquillo", "reserva",
    "commander", "companion", "maybeboard", "about", "name",
  ]);
  const LINEA = /^\s*(?:(\d+)\s*[xX]?\s+)?([^([\n]+?)(?:\s*\([A-Za-z0-9_]{2,6}\)\s*[\w-]*)?\s*$/;

  const COLOR_ROL = {
    motor: { n: "Motor", c: "#D8B15E" },
    amenaza: { n: "Amenaza", c: "#C1462A" },
    respuesta: { n: "Respuesta", c: "#D9D0C0" },
    tierra: { n: "Tierra", c: "#7E8C5C" },
  };

  function parsear(texto) {
    const salida = [];
    let banquillo = false;
    for (const cruda of texto.split(/\r?\n/)) {
      const linea = cruda.trim();
      if (!linea || linea.startsWith("#") || linea.startsWith("//")) continue;
      const clave = linea.toLowerCase().replace(/:$/, "");
      if (CABECERAS.has(clave)) {
        banquillo = ["sideboard", "banquillo", "reserva"].includes(clave);
        continue;
      }
      const m = LINEA.exec(linea);
      if (!m) continue;
      const nombre = m[2].split("//")[0].trim();
      if (!nombre) continue;
      salida.push({ copias: parseInt(m[1] || "1", 10), nombre, banquillo });
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
    if (pieza.copias_min !== undefined && carta.copias < pieza.copias_min) return null;
    if (pieza.copias_max !== undefined && carta.copias > pieza.copias_max) return null;
    let evidencia = "";
    for (const clave of ["oracle", "oracle2", "oracle3"]) {
      if (!pieza[clave]) continue;
      if (!re(pieza[clave], carta.oraculo)) return null;
      if (!evidencia) evidencia = frase(carta.oraculo, pieza[clave]);
    }
    if (pieza.no_oracle && re(pieza.no_oracle, carta.oraculo)) return null;
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

      const usadas = new Set();
      const elegidas = [];
      for (const pieza of regla.piezas) {
        const libres = porRol[pieza.rol].filter((a) => !usadas.has(a.carta.nombre));
        const pool = libres.length ? libres : porRol[pieza.rol];
        pool.sort((x, y) => y.carta.copias - x.carta.copias ||
                            x.carta.mv - y.carta.mv ||
                            x.carta.nombre.localeCompare(y.carta.nombre));
        elegidas.push({ rol: pieza.rol, ...pool[0] });
        usadas.add(pool[0].carta.nombre);
      }
      if (new Set(elegidas.map((e) => e.carta.nombre)).size < elegidas.length) continue;

      const sust = {};
      elegidas.forEach((e) => { sust[e.rol] = e.carta.nombre; });
      const fmt = (t) => (t || "").replace(/\{(\w+)\}/g, (m, k) => sust[k] !== undefined ? sust[k] : m);
      const evidencia = {};
      elegidas.forEach((e) => { evidencia[e.carta.nombre] = e.ev; });

      salida.push({
        id: regla.id, nombre: regla.nombre, bloque: regla.bloque || "Otros",
        tipo: regla.tipo || "sinergia", fuerza: regla.fuerza || 2, turno: regla.turno || "",
        piezas: elegidas.map((e) => e.carta.nombre),
        resumen: fmt(regla.resumen), pasos: (regla.pasos || []).map(fmt), evidencia,
      });
    }
    const orden = { sinergia: 0, aviso: 1, conflicto: 2 };
    salida.sort((a, b) => (orden[a.tipo] ?? 3) - (orden[b.tipo] ?? 3) || b.fuerza - a.fuerza);
    return salida;
  }

  function documento(mazo, sinergias, titulo) {
    return {
      titulo: titulo || "Mazo",
      subtitulo: `${mazo.total} cartas · ${mazo.tierras} tierras`,
      curva: mazo.curva,
      cartas: mazo.principal.map((c) => ({
        nombre: c.nombre, copias: c.copias, coste: c.coste, mv: c.mv,
        tipo: c.tipo, rol: c.rol, estrategia: "",
      })),
      sinergias, orden: [], reglas_oro: [], no_resueltas: mazo.no_resueltas,
    };
  }

  function datosGrafo(doc) {
    const idx = Object.fromEntries(doc.cartas.map((c) => [c.nombre, c]));
    const usadas = new Set();
    doc.sinergias.forEach((s) => s.piezas.forEach((p) => usadas.add(p)));

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

  global.Forja = { parsear, resolver, reglas, detectar, documento, datosGrafo };
})(window);
