// Textos da interface: a legenda (fala), os avisos, a gaveta (registro e sistema) e os cantos.

const $ = (id) => document.getElementById(id);

const horaAgora = () =>
  new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

// ---------- Legenda: uma linha só, de quem estiver falando ----------
const PALAVRAS_VISIVEIS = 18;  // ~2 linhas; o resto vai sumindo
const PALAVRAS_RECENTES = 11;  // estas ficam acesas; as anteriores ficam apagadas
const SEGURAR_LEGENDA_MS = 4500;

const legenda = () => $("legenda");
let timerSumir = null;

function mostrarLegenda(quem) {
  clearTimeout(timerSumir);
  const el = legenda();
  el.dataset.quem = quem;
  el.classList.remove("sumindo");
}

function sumirLegenda(depoisMs = SEGURAR_LEGENDA_MS) {
  clearTimeout(timerSumir);
  timerSumir = setTimeout(() => legenda().classList.add("sumindo"), depoisMs);
}

/** O que você está falando (enquanto ela não fala). */
export function mostrarTranscricao(final, parcial = "") {
  if (fala.ativa) return; // ela está falando: a legenda é dela
  const el = legenda();
  if (!final && !parcial) {
    if (el.dataset.quem === "voce") sumirLegenda(1200);
    return;
  }
  mostrarLegenda("voce");
  el.innerHTML = "";
  const f = document.createElement("span");
  f.className = "final";
  f.textContent = final;
  const p = document.createElement("span");
  p.textContent = (final && parcial ? " " : "") + parcial;
  el.append(f, p);
}

// ---------- A fala dela, no ritmo da voz ----------
// As palavras chegam mais rápido que a voz; revelamos conforme o áudio toca:
// palavras visíveis ≈ segundos já tocados × (palavras recebidas ÷ segundos de áudio recebidos).
let progressoAudio = () => ({ tocado: 0, agendado: 0, terminou: false });
export function definirProgressoAudio(fn) { progressoAudio = fn; }

const fala = { ativa: false, texto: "", mostradas: 0, fim: false, aoTerminar: null, desdeFim: 0, geracao: 0 };

export function iniciarResposta() {
  Object.assign(fala, { ativa: true, texto: "", mostradas: 0, fim: false, aoTerminar: null, desdeFim: 0 });
  mostrarLegenda("iris");
  legenda().innerHTML = "";
  const minha = ++fala.geracao;
  requestAnimationFrame(() => revelar(minha));
}

export function adicionarResposta(pedaco) {
  fala.texto += pedaco;
}

/** Chama `callback(textoCompleto)` quando a fala terminar de aparecer. */
export function finalizarResposta(callback) {
  if (!fala.ativa) return;
  fala.fim = true;
  fala.desdeFim = performance.now();
  fala.aoTerminar = callback;
}

/** Interrompe; devolve o texto que ela já tinha dito (ou "" se não estava falando). */
export function cancelarResposta() {
  if (!fala.ativa) return "";
  const dito = fala.texto.split(/\s+/).slice(0, Math.max(fala.mostradas, 1)).join(" ").trim();
  fala.ativa = false;
  fala.geracao++;
  sumirLegenda(600);
  return dito;
}

function palavrasProntas() {
  const palavras = fala.texto.trim().split(/\s+/).filter(Boolean);
  // a última pode estar pela metade (chegou em pedaços), a não ser que a fala já tenha terminado
  if (!fala.fim && !/\s$/.test(fala.texto)) palavras.pop();
  return palavras;
}

function revelar(minha) {
  if (minha !== fala.geracao || !fala.ativa) return;
  const palavras = palavrasProntas();
  const { tocado, agendado, terminou } = progressoAudio();
  let alvo;
  if (agendado > 0.3) {
    const taxa = Math.min(4.5, Math.max(1.6, palavras.length / agendado));
    alvo = terminou ? palavras.length : Math.floor(tocado * taxa) + 1;
  } else {
    // ainda sem áudio (ou a voz falhou): segue no ritmo de fala comum, ~2,7 palavras/s depois do fim
    alvo = fala.fim ? Math.floor((performance.now() - fala.desdeFim) / 370) : 0;
  }
  alvo = Math.min(alvo, palavras.length);
  if (alvo > fala.mostradas) {
    fala.mostradas = alvo;
    desenharFala(palavras);
  }
  if (fala.fim && fala.mostradas >= palavras.length && (terminou || agendado <= 0.3)) {
    fala.ativa = false;
    const cb = fala.aoTerminar;
    fala.aoTerminar = null;
    sumirLegenda();
    cb?.(fala.texto.trim());
    return;
  }
  requestAnimationFrame(() => revelar(minha));
}

function desenharFala(palavras) {
  // só acrescenta as palavras novas e tira as velhas (recriar tudo faria as animações piscarem)
  const el = legenda();
  const inicio = Math.max(0, fala.mostradas - PALAVRAS_VISIVEIS);
  for (const s of [...el.children]) {
    if (s.dataset.i === undefined || Number(s.dataset.i) < inicio) s.remove();
  }
  const ultima = el.lastElementChild ? Number(el.lastElementChild.dataset.i) : inicio - 1;
  for (let i = Math.max(ultima + 1, inicio); i < fala.mostradas; i++) {
    const span = document.createElement("span");
    span.className = "p";
    span.dataset.i = i;
    span.textContent = palavras[i] + " ";
    el.appendChild(span);
  }
  for (const s of el.children) s.classList.toggle("antiga", Number(s.dataset.i) < fala.mostradas - PALAVRAS_RECENTES);
}

// ---------- Avisos rápidos ----------
export function avisar(texto) {
  const el = document.createElement("div");
  el.className = "aviso";
  el.textContent = texto;
  $("avisos").appendChild(el);
  while ($("avisos").children.length > 4) $("avisos").firstChild.remove();
  setTimeout(() => el.classList.add("saindo"), 5000);
  setTimeout(() => el.remove(), 6000);
}

// ---------- Rascunho esperando sua confirmação ----------
let timerRascunho = null;

/** Mostra o rascunho (ex.: e-mail) enquanto ela pergunta se pode enviar; `null` esconde. */
export function mostrarRascunho(dados) {
  clearTimeout(timerRascunho);
  if (!dados) {
    $("rascunho").hidden = true;
    return;
  }
  const [rotulo1, rotulo2] = dados.rotulos || ["Para", "Assunto"];
  $("rascunho-acao").textContent = dados.acao || "Rascunho";
  $("rascunho-rotulo1").textContent = rotulo1;
  $("rascunho-rotulo2").textContent = rotulo2;
  $("rascunho-para").textContent = dados.para || "";
  $("rascunho-assunto").textContent = dados.assunto || "";
  $("rascunho-texto").textContent = dados.texto || "";
  $("rascunho-dica").textContent = dados.dica || "Diga “pode enviar” ou “cancela”";
  $("rascunho").hidden = false;
  timerRascunho = setTimeout(() => ($("rascunho").hidden = true), 120000); // a confirmação expira em 2 min
}

// ---------- Memória (gaveta) ----------
/** Lista o que ela lembra; `aoApagar(tipo, id)` é chamado quando você clica no ×. */
export function mostrarMemoria({ fatos = [], assuntos = [] }, aoApagar) {
  const item = (texto, tipo, id, rotulo) => {
    const li = document.createElement("li");
    li.innerHTML = `${rotulo ? '<span class="tipo"></span>' : ""}<span class="texto"></span><button title="Esquecer">×</button>`;
    if (rotulo) li.querySelector(".tipo").textContent = rotulo;
    li.querySelector(".texto").textContent = texto;
    li.querySelector("button").addEventListener("click", (ev) => {
      ev.stopPropagation();
      li.remove();
      aoApagar(tipo, id);
    });
    return li;
  };
  $("memoria-assuntos").replaceChildren(...assuntos.map((a) => item(a.texto, "assunto", a.id, "EM ABERTO")));
  $("memoria-fatos").replaceChildren(...fatos.map((f) => item(f.texto, "fato", f.id)));
  const total = fatos.length + assuntos.length;
  $("memoria-total").textContent = total ? `· ${total}` : "";
  $("memoria-vazia").hidden = total > 0;
}

// ---------- Pendências e Pensamentos (vigília) ----------
/** Pendências da vigília; `aoDescartar(id)` quando você clica no ×. */
export function mostrarPendencias(itens, aoDescartar) {
  const lista = itens.map((p) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="tipo"></span><span class="texto"></span><button title="Descartar">×</button>`;
    const tipo = li.querySelector(".tipo");
    tipo.textContent = p.urgente ? "URGENTE" : `P${p.prioridade}`;
    tipo.classList.toggle("urgente", p.urgente);
    li.querySelector(".texto").textContent = p.texto;
    li.querySelector("button").addEventListener("click", (ev) => {
      ev.stopPropagation();
      li.remove();
      aoDescartar(p.id);
    });
    return li;
  });
  $("pendencias").replaceChildren(...lista);
  $("pendencias-total").textContent = itens.length ? `· ${itens.length}` : "";
  $("pendencias-vazia").hidden = itens.length > 0;
}

/** Um pensamento da vigília (o mais novo fica em cima). */
export function adicionarPensamento({ hora, texto }) {
  const li = document.createElement("li");
  li.innerHTML = `<span class="hora"></span><span class="texto"></span>`;
  li.querySelector(".hora").textContent = hora;
  li.querySelector(".texto").textContent = texto;
  li.style.gridTemplateColumns = "auto 1fr";
  $("pensamentos").prepend(li);
  while ($("pensamentos").children.length > 40) $("pensamentos").lastChild.remove();
  $("pensamentos-vazio").hidden = true;
}

// ---------- Registro (gaveta) ----------
const ROTULOS = { voce: "VOCÊ", iris: "IRIS", sistema: "SISTEMA" };

export function registrarLog(quem, texto, comAviso = true) {
  const li = document.createElement("li");
  li.innerHTML = `<span class="hora"></span><span class="quem ${quem}"></span><span class="texto"></span>`;
  li.querySelector(".hora").textContent = horaAgora();
  li.querySelector(".quem").textContent = ROTULOS[quem] || quem;
  li.querySelector(".texto").textContent = texto;
  const log = $("log");
  log.appendChild(li);
  while (log.children.length > 300) log.firstChild.remove();
  log.scrollTop = log.scrollHeight;
  if (quem === "sistema" && comAviso) avisar(texto);
}

export function alternarGaveta(abrir) {
  const aberta = $("gaveta").classList.toggle("aberta", abrir);
  document.body.classList.toggle("gaveta-aberta", aberta);
}

// ---------- Habilidades (gaveta) ----------
/** Propostas (com Ver / Aprovar / Recusar) e ativas (com Ver). `acao(tipo, nome)`: "ver", "ver_proposta", "aprovar", "recusar". */
export function mostrarHabilidades({ ativas = [], propostas = [] }, acao) {
  const item = (h, proposta) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="tipo"></span><span class="texto"></span><span class="botoes"></span>`;
    const tipo = li.querySelector(".tipo");
    tipo.textContent = proposta ? `NOVA v${h.versao}` : "ATIVA";
    tipo.classList.add(proposta ? "proposta" : "ativa");
    li.querySelector(".texto").textContent = `${h.nome} — ${h.descricao}`;
    const botoes = proposta
      ? [["Ver", "ver_proposta", ""], ["Aprovar", "aprovar", "aprovar"], ["Recusar", "recusar", "recusar"]]
      : [["Ver", "ver", ""]];
    for (const [rotulo, tipoAcao, classe] of botoes) {
      const b = document.createElement("button");
      b.textContent = rotulo;
      if (classe) b.className = classe;
      b.addEventListener("click", (ev) => {
        ev.stopPropagation();
        acao(tipoAcao, h.nome);
      });
      li.querySelector(".botoes").appendChild(b);
    }
    return li;
  };
  $("habilidades-propostas").replaceChildren(...propostas.map((h) => item(h, true)));
  $("habilidades-ativas").replaceChildren(...ativas.map((h) => item(h, false)));
  const total = ativas.length + propostas.length;
  $("habilidades-total").textContent = total ? `· ${ativas.length} ativas${propostas.length ? `, ${propostas.length} nova(s)` : ""}` : "";
}

/** Gaveta → Personalidade: propostas (Ver/Aprovar/Recusar) e o jeito aprendido (× esquece). */
export function mostrarPersonalidade({ propostas = [], jeitos = [] }, acao) {
  const item = (rotulo, classeTipo, texto, botoes, id) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="tipo"></span><span class="texto"></span><span class="botoes"></span>`;
    const tipo = li.querySelector(".tipo");
    tipo.textContent = rotulo;
    tipo.classList.add(classeTipo);
    li.querySelector(".texto").textContent = texto;
    for (const [nome, tipoAcao, classe] of botoes) {
      const b = document.createElement("button");
      b.textContent = nome;
      if (classe) b.className = classe;
      b.addEventListener("click", (ev) => {
        ev.stopPropagation();
        acao(tipoAcao, id);
      });
      li.querySelector(".botoes").appendChild(b);
    }
    return li;
  };
  $("personalidade-propostas").replaceChildren(
    ...propostas.map((p) =>
      item("PROPOSTA", "proposta", p.motivo ? `${p.texto} — ${p.motivo}` : p.texto,
        [["Ver", "ver_personalidade", ""], ["Aprovar", "aprovar_personalidade", "aprovar"], ["Recusar", "recusar_personalidade", "recusar"]], p.id),
    ),
  );
  $("personalidade-jeitos").replaceChildren(
    ...jeitos.map((j) => item("JEITO", "ativa", j.texto, [["×", "esquecer_jeito", "recusar"]], j.id)),
  );
  $("personalidade-vazia").hidden = propostas.length + jeitos.length > 0;
  $("personalidade-total").textContent = propostas.length + jeitos.length
    ? `· ${jeitos.length} aprendido(s)${propostas.length ? `, ${propostas.length} proposta(s)` : ""}`
    : "";
}

export const gavetaAberta = () => $("gaveta").classList.contains("aberta");

// ---------- Estado e status ----------
const ESTADOS_TEXTO = {
  IDLE: "em espera",
  OUVINDO: "ouvindo",
  PENSANDO: "pensando",
  FALANDO: "falando",
};

export function mostrarEstado(estado, emConversa = false) {
  document.body.dataset.estado = estado;
  $("estado-texto").textContent = estado === "IDLE" ? (emConversa ? "em conversa" : "em espera") : ESTADOS_TEXTO[estado] || estado;
  $("status-estado").textContent = estado;
  $("status-modo").textContent = emConversa ? "conversa" : "espera";
}

export function mostrarStatus({ cpu, ram, provedor, conexao }) {
  $("valor-cpu").textContent = `${cpu}%`;
  $("barra-cpu").style.width = `${cpu}%`;
  $("valor-ram").textContent = `${ram}%`;
  $("barra-ram").style.width = `${ram}%`;
  $("ponto-ia").className = "ponto" + (conexao === "ok" ? " ok" : conexao === "reserva" ? " alerta" : "");
  $("ponto-ia").title = conexao === "offline" ? "IA offline" : `IA: ${provedor}`;
  $("status-ia").textContent = conexao === "offline" ? "offline" : `${provedor}${conexao === "reserva" ? " (reserva)" : ""}`;
}

export function mostrarConexao(conectado) {
  $("status-ws").textContent = conectado ? "online" : "reconectando";
}

export function mostrarSaudacao() {}

export function iniciarRelogio() {
  const tick = () => ($("relogio").textContent = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }));
  tick();
  setInterval(tick, 10000);
}
