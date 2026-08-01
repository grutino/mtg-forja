/* MTG Forja — paleta, tipografía y utilidades compartidas por los renderizadores.
   Puerto fiel de src/mtg_forja/render/comun.py. Lo consumen tanto la web como los
   HTML que genera Python, que incrustan este archivo tal cual: una sola fuente de
   verdad para el diseño, igual que reglas.json lo es para los patrones. */
(function (global) {
  "use strict";

  const PALETA = `
:root{
  --ceniza:#1B1714;--fondo:#1E1A16;--pergamino:#E5DFD1;--papel:#EFEADF;
  --brasa:#A8321A;--laton:#9C7A22;--tinta:#2A241F;--humo:#7C7266;--lin:#C8BFAC;
  --serif:"Charter","Bitstream Charter",Georgia,"Times New Roman",serif;
  --cond:"Avenir Next Condensed","DejaVu Sans Condensed","Arial Narrow",sans-serif;
}
`;

/* El pip incoloro se llama `inc`, no `c`: la guía usa `.c` para la ficha de
   carta (118px de ancho) y, al definirse después con la misma especificidad,
   ganaba y convertía el círculo del maná genérico en un óvalo. */
  const PIPS = `
.pip{display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;
 border-radius:50%;font-family:var(--cond);font-size:9.5px;font-weight:700;line-height:1;
 border:1px solid rgba(0,0,0,.3);flex:0 0 auto}
.pip.w{background:#F5F1E4;color:#57503f}.pip.u{background:#8FBEDC;color:#22333d}
.pip.b{background:#3B3238;color:#e7dfe2}.pip.r{background:#C4472A;color:#fff8f0}
.pip.g{background:#7E9B6A;color:#1f2a19}.pip.inc{background:#C3BAA8;color:#3d382f}
`;

  const CSS_CURVA = `
.curva{display:flex;gap:5px;align-items:flex-end}
.cb{width:16px;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;
 height:100%;position:relative}
.cb b{width:100%;background:linear-gradient(180deg,#C9A144,#A8321A);border-radius:2px 2px 0 0}
.cb i{font-style:normal;font-family:var(--cond);font-size:9px;color:var(--humo);
 position:absolute;bottom:-13px}
.cb u{text-decoration:none;font-family:var(--cond);font-size:10px;font-weight:700;margin-bottom:2px}
`;

  const COLOR_ROL = {
    motor: "#D8B15E",
    amenaza: "#C1462A",
    respuesta: "#D9D0C0",
    tierra: "#7E8C5C",
  };
  const NOMBRE_ROL = {
    motor: "Motor", amenaza: "Amenaza", respuesta: "Respuesta", tierra: "Tierra",
  };

  const IMG = "https://api.scryfall.com/cards/named?fuzzy={q}&format=image&version={v}&face=front";

  /** Equivalente de html.escape(s, quote=True) de Python. */
  function e(t) {
    return String(t === null || t === undefined ? "" : t)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  }

  /** Nombre de carta -> parámetro fuzzy de la API de Scryfall. */
  function consulta(nombre) {
    const limpio = String(nombre).split("//")[0].replace(/[^\p{L}\p{N}_\s'-]/gu, " ");
    return limpio.split(/\s+/).filter(Boolean).join("+");
  }

  function imagen(nombre, version) {
    return IMG.replace("{q}", consulta(nombre)).replace("{v}", version || "normal");
  }

  /** Convierte {2}{W}{W} en círculos de color. */
  function pips(coste) {
    if (!coste) return "";
    const fuera = [];
    for (const m of String(coste).matchAll(/\{([^}]+)\}/g)) {
      const s = m[1].toUpperCase();
      if (s.length === 1 && "WUBRG".includes(s)) {
        fuera.push(`<i class="pip ${s.toLowerCase()}">${s}</i>`);
      } else if (/^\d+$/.test(s) || s === "X") {
        fuera.push(`<i class="pip inc">${s}</i>`);
      } else {
        fuera.push(`<i class="pip inc">${s[0]}</i>`);
      }
    }
    return fuera.join("");
  }

  function indice(documento) {
    const idx = {};
    for (const c of documento.cartas || []) idx[c.nombre] = c;
    return idx;
  }

  /** Agrupa las sinergias por bloque conservando el orden de aparición. */
  function bloques(documento) {
    const grupos = new Map();
    for (const s of documento.sinergias || []) {
      const b = s.bloque || "Otros";
      if (!grupos.has(b)) grupos.set(b, []);
      grupos.get(b).push(s);
    }
    return [...grupos.entries()];
  }

  /** Barras de la curva de maná, en HTML puro para que imprima bien. */
  function curvaSvg(curva, alto) {
    const claves = Object.keys(curva || {});
    if (!claves.length) return "";
    const tope = Math.max(...claves.map((k) => curva[k])) || 1;
    const cols = claves.map((k) =>
      `<span class="cb"><u>${curva[k]}</u>` +
      `<b style="height:${Math.round(100 * curva[k] / tope)}%"></b>` +
      `<i>${e(k)}</i></span>`).join("");
    return `<div class="curva" style="height:${alto || 42}px">${cols}</div>`;
  }

  function pie(documento) {
    let aviso = "";
    const sr = documento.no_resueltas || [];
    if (sr.length) aviso = " · sin resolver: " + e(sr.slice(0, 5).join(", "));
    return "<footer><span>" + e(documento.titulo || "") + aviso + "</span>" +
      "<span>Generado con MTG Forja · imágenes de Scryfall · " +
      "Magic: The Gathering © Wizards of the Coast</span></footer>";
  }

  /** Inyecta el CSS y pinta el cuerpo. Lo usan los HTML generados por Python. */
  function montar(css, html) {
    document.head.insertAdjacentHTML("beforeend", "<style>" + css + "</style>");
    document.body.innerHTML = html;
  }

  global.ForjaComun = {
    PALETA, PIPS, CSS_CURVA, COLOR_ROL, NOMBRE_ROL,
    e, consulta, imagen, pips, indice, bloques, curvaSvg, pie, montar,
  };
})(typeof window !== "undefined" ? window : globalThis);
