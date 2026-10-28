// Cérebro da interface: conecta no servidor por WebSocket e coordena
// ouvido, voz, núcleo e painéis.
//
// Dois modos de conversa:
//   Live (principal): depois do "Iris", o microfone vai direto para a Gemini Live,
//     que ouve, pensa e responde em voz; dá para interromper falando.
//   Clássico (reserva): o navegador transcreve (+ Whisper), o cérebro responde em
//     texto e a voz é sintetizada à parte.

import { Nucleo } from "./nucleo.js";
import { Ouvinte } from "./ouvir.js";
import * as audio from "./audio.js";
import * as painel from "./painel.js";

/** A íris 3D (precisa do Three.js da internet); se falhar, usa o núcleo 2D. */
async function criarPresenca(canvas) {
  try {
    const { Olho } = await import("./olho.js");
    return new Olho(canvas);
  } catch (erro) {
    console.warn("Íris 3D indisponível, usando o núcleo 2D", erro);
    return new Nucleo(canvas);
  }
}

const nucleo = await criarPresenca(document.getElementById("orbe"));
const reprodutor = new audio.Reprodutor();
painel.definirProgressoAudio(() => reprodutor.progresso());
const microfone = new audio.Microfone();
const gravador = new audio.Gravador();
let ouvinte = null;
let usarWhisper = false;
let ativadoPorVoz = false; // o áudio gravado começa com "Iris" (que tiramos do texto)
let ws = null;
let estado = "IDLE";
let config = { nome: "", voz: "" };
let jaPerguntouNome = false;

// Live
let liveAtiva = false;       // conversa Live aberta (ou abrindo)
let liveFalhouAte = 0;       // se a Live falhou, usa o modo clássico até este horário
let timerConversa = null;    // encerra a conversa depois de um tempo em silêncio
let falaPendente = false;    // você falou e ela ainda não respondeu (para mostrar PENSANDO)
let gravadorPronto = Promise.resolve(false); // vira true quando o gravador do microfone liga
let silencioDesde = 0;

const emConversa = () => liveAtiva || Boolean(ouvinte?.emConversa);

// ---------- Estado ----------
function definirEstado(novo) {
  estado = novo;
  nucleo.definirEstado(novo);
  painel.mostrarEstado(novo, emConversa());
}

// Frases curtas que encerram a conversa ("valeu", "tchau", "era só isso"...)
const DESPEDIDA = /^((ok|beleza|show|certo) )?(valeu|obrigad[oa]|brigad[oa]|tchau|ate (mais|logo|depois)|pode parar|para de ouvir|(era )?so isso|encerra|chega)( (iris|obrigad[oa]|valeu|tchau))*$/;
const normalizar = (t) =>
  t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z ]/g, "").replace(/\s+/g, " ").trim();
let encerrarDepois = false;
let conversaClassica = false; // houve conversa pelo modo reserva (o servidor precisa saber quando ela acaba)

/** Fim de um ciclo (respondeu, interrompeu ou desistiu).
 *  Em conversa: já volta a ouvir o próximo pedido. Fora dela: espera o "Iris". */
function voltarAoIdle() {
  if (liveAtiva) {
    if (encerrarDepois) {
      encerrarDepois = false;
      encerrarLive("Conversa encerrada. Diga “Iris” para chamar de novo.");
    } else {
      definirEstado("OUVINDO");
      renovarConversa();
    }
    tentarAlertar();
    return;
  }
  if (encerrarDepois) {
    encerrarDepois = false;
    ouvinte?.encerrarConversa();
  }
  if (ouvinte?.emConversa) {
    definirEstado("OUVINDO");
    painel.mostrarTranscricao("", "");
    ativadoPorVoz = false;
    adiantado = null;
    gravador.marcar(0.3);
    ouvinte.continuarConversa();
  } else {
    definirEstado("IDLE");
    ouvinte?.retomar();
    if (conversaClassica) {
      // a conversa do modo reserva acabou: o servidor atualiza a memória
      conversaClassica = false;
      enviar("conversa_fim");
    }
    tentarAlertar();
  }
}

// ---------- Aviso proativo (vigília achou algo urgente) ----------
// Ela só fala quando estiver livre: em espera, ou ouvindo numa conversa sem você estar falando.
const alertasPendentes = [];

function tentarAlertar() {
  if (!alertasPendentes.length || dialogo.open) return;
  const livreEmEspera = estado === "IDLE" && !liveAtiva && podeUsarLive();
  const livreEmConversa = liveAtiva && estado === "OUVINDO" && !falaPendente;
  if (!livreEmEspera && !livreEmConversa) return; // tenta de novo quando ela voltar a ficar livre
  const p = alertasPendentes.shift();
  if (livreEmEspera) {
    audio.bip();
    iniciarLive(false); // abre a conversa: você já pode responder
  }
  painel.avisar(`Aviso: ${p.resumo}`);
  enviar("live_aviso", {
    texto:
      `[Aviso da sua vigília — isto NÃO foi dito por ele] Algo urgente: ${p.resumo}. ` +
      `Sugestão: ${p.acao || "—"}. (Pendência ${p.id}.) Ele não te chamou: avise agora, de forma curta e ` +
      `natural, e pergunte o que ele quer fazer.`,
  });
}

function encerrarConversa() {
  if (liveAtiva) {
    reprodutor.parar();
    const parcial = painel.cancelarResposta();
    if (parcial) painel.registrarLog("iris", parcial + " [interrompida]");
    encerrarLive("Conversa encerrada. Diga “Iris” para chamar de novo.");
    return;
  }
  ouvinte?.encerrarConversa();
  if (estado === "PENSANDO" || estado === "FALANDO") interromper();
  else voltarAoIdle();
  painel.registrarLog("sistema", "Conversa encerrada. Diga “Iris” para chamar de novo.");
}

reprodutor.aoTerminar = voltarAoIdle;

// ---------- WebSocket ----------
function conectar() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.binaryType = "arraybuffer";
  ws.onopen = () => painel.mostrarConexao(true);
  ws.onclose = () => {
    painel.mostrarConexao(false);
    setTimeout(conectar, 1500); // tenta de novo sozinho
  };
  ws.onmessage = (ev) => {
    if (ev.data instanceof ArrayBuffer) reprodutor.adicionar(ev.data); // áudio de uma frase
    else tratarMensagem(JSON.parse(ev.data));
  };
}

function enviar(tipo, dados = {}) {
  if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ tipo, ...dados }));
}

function tratarMensagem(msg) {
  switch (msg.tipo) {
    case "estado":
      definirEstado(msg.estado);
      break;
    case "resposta_inicio":
      reprodutor.iniciar();
      painel.iniciarResposta();
      break;
    case "token":
      painel.adicionarResposta(msg.texto);
      break;
    case "resposta_fim":
      painel.finalizarResposta((texto) => painel.registrarLog("iris", texto));
      break;
    case "audio_fim":
      // volta ao IDLE quando a última frase acabar de tocar
      if (estado === "PENSANDO" || estado === "FALANDO") reprodutor.finalizar();
      break;
    case "status":
      painel.mostrarStatus(msg);
      break;
    case "config":
      config = msg;
      painel.mostrarSaudacao(msg.nome);
      if (!ouvinte) iniciarOuvido(msg.ouvir);
      if (!msg.nome && !jaPerguntouNome) {
        jaPerguntouNome = true;
        abrirConfig();
      }
      break;
    case "rascunho":
      painel.mostrarRascunho(msg.rascunho);
      break;
    case "memoria":
      painel.mostrarMemoria(msg, (tipo, id) =>
        enviar(tipo === "fato" ? "esquecer_fato" : "fechar_assunto", { id }),
      );
      break;

    case "habilidades":
      painel.mostrarHabilidades(msg, (acao, nome) => {
        if (acao === "ver" || acao === "ver_proposta") enviar("ver_habilidade", { nome, proposta: acao === "ver_proposta" });
        else enviar(acao === "aprovar" ? "aprovar_habilidade" : "recusar_habilidade", { nome });
      });
      break;

    case "personalidade_aprendida":
      painel.mostrarPersonalidade(msg, (acao, id) => enviar(acao, { id }));
      break;

    // ----- Vigília -----
    case "pensamento":
      painel.adicionarPensamento(msg);
      break;
    case "pendencias":
      painel.mostrarPendencias(msg.itens, (id) => enviar("descartar_pendencia", { id }));
      break;
    case "alerta_proativo":
      alertasPendentes.push(msg.pendencia);
      tentarAlertar();
      break;
    case "erro":
    case "sistema": // avisos e ações das ferramentas ("Feito: abrir o programa Spotify.")
      painel.registrarLog("sistema", msg.texto);
      break;

    // ----- Live -----
    case "live_status":
      if (msg.ativo) break;
      liveFalhouAte = Date.now() + (config.live?.falha_minutos ?? 5) * 60 * 1000;
      painel.registrarLog("sistema", `Gemini Live indisponível (${msg.erro}). Usando o modo clássico por ${config.live?.falha_minutos ?? 5} min.`);
      if (liveAtiva) {
        // a conversa continua, agora pelo modo clássico
        const estavaConversando = estado !== "IDLE";
        encerrarLiveLocal();
        reprodutor.parar();
        painel.cancelarResposta();
        if (estavaConversando) ouvinte?.ativarManual();
        else voltarAoIdle();
      }
      break;
    case "voce_parcial":
      renovarConversa();
      falaPendente = true;
      if (estado !== "FALANDO") painel.mostrarTranscricao("", msg.texto);
      break;
    case "voce_final":
      painel.mostrarTranscricao(msg.texto);
      painel.registrarLog("voce", msg.texto);
      if (DESPEDIDA.test(normalizar(msg.texto))) encerrarDepois = true; // ela responde e encerra
      break;
    case "interrompido": {
      // você falou por cima: para de tocar na hora e volta a ouvir
      falaPendente = false;
      reprodutor.parar();
      const parcial = painel.cancelarResposta() || msg.texto;
      if (parcial) painel.registrarLog("iris", parcial + " [interrompida]");
      if (liveAtiva) definirEstado("OUVINDO");
      break;
    }
    case "turno_fim":
      falaPendente = false;
      renovarConversa();
      reprodutor.finalizar(); // quando a última parte tocar, volta a ouvir
      break;
  }
}

// ---------- Conversa Live ----------
function podeUsarLive() {
  return config.live?.ativo && Date.now() > liveFalhouAte && ws?.readyState === WebSocket.OPEN;
}

function iniciarLive(porVoz) {
  liveAtiva = true;
  falaPendente = false;
  encerrarDepois = false;
  audio.destravar();
  ouvinte?.pausar(); // o reconhecimento do navegador descansa: quem ouve agora é a Live
  definirEstado("OUVINDO");
  painel.mostrarTranscricao("", "");
  enviar("live_iniciar");
  renovarConversa();
  // se você chamou logo que a janela abriu, o gravador pode ainda estar ligando: espera por ele
  gravadorPronto.then((pronto) => {
    if (!liveAtiva) return;
    if (!pronto) {
      enviar("live_encerrar");
      encerrarLiveLocal();
      liveFalhouAte = Date.now() + (config.live?.falha_minutos ?? 5) * 60 * 1000;
      painel.registrarLog("sistema", "Não consegui gravar o microfone para a Live. Usando o modo clássico.");
      ouvinte?.ativarManual();
      return;
    }
    // o "Iris" é detectado com atraso: manda junto o começo da fala, para o pedido não se perder
    const comeco = gravador.pcmRecente(porVoz ? 2.5 : 0.3);
    if (comeco) ws.send(comeco);
    gravador.aoBloco = enviarAudioLive;
  });
}

function enviarAudioLive(pcm) {
  if (!liveAtiva || ws?.readyState !== WebSocket.OPEN) return;
  if (dialogo.open) return; // amostra de voz na engrenagem não deve ir para a Live
  // sem "interromper falando", o microfone fica mudo enquanto ela fala (evita ela ouvir a si mesma)
  if (!config.live?.interromper_falando && estado === "FALANDO") return;
  ws.send(pcm);
}

/** Fecha só do lado da interface (a Live já caiu ou vai ser fechada). */
function encerrarLiveLocal() {
  liveAtiva = false;
  falaPendente = false;
  gravador.aoBloco = null;
  clearTimeout(timerConversa);
}

function encerrarLive(mensagem) {
  enviar("live_encerrar");
  encerrarLiveLocal();
  encerrarDepois = false;
  ouvinte?.encerrarConversa();
  definirEstado("IDLE");
  painel.mostrarTranscricao("", "");
  ouvinte?.retomar();
  if (mensagem) painel.registrarLog("sistema", mensagem);
}

/** Cada sinal de vida (você falou, ela respondeu) adia o fim da conversa por silêncio. */
function renovarConversa() {
  clearTimeout(timerConversa);
  const segundos = config.ouvir?.conversa_segundos ?? 60;
  timerConversa = setTimeout(() => {
    if (!liveAtiva) return;
    if (estado === "OUVINDO") encerrarLive("Conversa encerrada por silêncio. Diga “Iris” para chamar de novo.");
    else renovarConversa();
  }, segundos * 1000);
}

// ---------- Ouvido ----------
async function iniciarOuvido(cfgOuvir) {
  ouvinte = new Ouvinte(cfgOuvir, {
    aoOuvirFundo: (texto) => painel.mostrarTranscricao("", texto),
    aoAtivar: (porVoz) => {
      audio.bip();
      if (podeUsarLive()) {
        iniciarLive(porVoz);
        return;
      }
      // modo clássico. Pela voz, o "Iris" foi detectado com atraso: guarda uns segundos de antes
      ativadoPorVoz = porVoz;
      adiantado = null;
      gravador.marcar(porVoz ? 2.5 : 0.3);
      definirEstado("OUVINDO");
      painel.mostrarTranscricao("", "");
    },
    aoTranscrever: (final, parcial) => painel.mostrarTranscricao(final, parcial),
    aoFimDeFrase: adiantarWhisper,
    aoComando: async (textoNavegador) => {
      painel.mostrarTranscricao(textoNavegador);
      definirEstado("PENSANDO");
      const texto = await corrigirComWhisper(textoNavegador);
      if (estado !== "PENSANDO") return; // foi interrompida enquanto transcrevia
      if (DESPEDIDA.test(normalizar(texto))) encerrarDepois = true; // responde e encerra
      painel.mostrarTranscricao(texto);
      painel.registrarLog("voce", texto);
      conversaClassica = true;
      enviar("mensagem", { texto });
    },
    aoDesistir: () => {
      painel.mostrarTranscricao("", "");
      voltarAoIdle();
    },
    aoErro: (texto) => painel.registrarLog("sistema", texto),
  });
  ouvinte.iniciar();
  gravadorPronto = prepararMicrofone(cfgOuvir);
}

/** Liga o microfone (volume do núcleo) e o gravador (Whisper e Live). Devolve se o gravador ficou pronto. */
async function prepararMicrofone(cfgOuvir) {
  try {
    await microfone.iniciar();
  } catch {
    painel.registrarLog("sistema", "Não consegui acessar o microfone (o núcleo não vai reagir à voz).");
    return false;
  }
  if (!cfgOuvir.whisper && !config.live?.ativo) return false;
  try {
    await gravador.iniciar(microfone);
    usarWhisper = Boolean(cfgOuvir.whisper);
    return true;
  } catch (erro) {
    painel.registrarLog("sistema", `Não consegui gravar o microfone (${erro.message}): Live e Whisper desligados.`);
    return false;
  }
}

// Whisper adiantado: começa a transcrever quando a frase fecha, durante a pausa,
// para o texto já estar pronto quando a pausa terminar.
let adiantado = null; // { texto: texto do navegador naquele momento, promessa }

/** Manda o áudio gravado até agora para o Whisper. Devolve o texto ou "" se falhar. */
async function transcreverAudio() {
  const wav = gravador.recortar();
  if (!wav) return "";
  try {
    const resposta = await fetch("/ouvir/transcrever", {
      method: "POST",
      body: wav,
      signal: AbortSignal.timeout(5000),
    });
    const { texto } = await resposta.json();
    return resposta.ok ? texto : "";
  } catch {
    return "";
  }
}

function adiantarWhisper(textoNavegador) {
  if (usarWhisper) adiantado = { texto: textoNavegador, promessa: transcreverAudio() };
}

/** Texto final do pedido: o do Whisper (adiantado, se você não falou mais nada depois) ou o do navegador. */
async function corrigirComWhisper(textoNavegador) {
  if (!usarWhisper) return textoNavegador;
  const promessa = adiantado?.texto === textoNavegador ? adiantado.promessa : transcreverAudio();
  adiantado = null;
  const texto = await promessa;
  if (!texto) return textoNavegador;
  return (ativadoPorVoz ? ouvinte.removerAtivacao(texto) : texto) || textoNavegador;
}

function interromper() {
  enviar("interromper");
  reprodutor.parar();
  const parcial = painel.cancelarResposta();
  if (parcial) painel.registrarLog("iris", parcial + " [interrompida]");
  voltarAoIdle();
}

// ---------- Núcleo reage ao som ----------
nucleo.definirEspectro(() => reprodutor.espectro());
setInterval(() => {
  const nivelMic = microfone.nivel();
  if (estado === "OUVINDO") nucleo.definirNivel(nivelMic);
  else if (estado === "FALANDO") nucleo.definirNivel(reprodutor.nivel());
  else nucleo.definirNivel(0);

  // Live: a Live não avisa quando você terminou de falar; se você falou e ficou
  // em silêncio, mostramos PENSANDO até a resposta chegar
  if (!liveAtiva) return;
  const agora = performance.now();
  if (nivelMic > 0.08) silencioDesde = agora;
  if (estado === "OUVINDO" && falaPendente && agora - silencioDesde > 400) definirEstado("PENSANDO");
  else if (estado === "PENSANDO" && nivelMic > 0.2) definirEstado("OUVINDO");
}, 33);

// ---------- Teclado ----------
window.addEventListener("keydown", (ev) => {
  audio.destravar();
  if (document.getElementById("config").open) return;
  // digitando numa caixa de texto: os atalhos não valem (só Esc fecha a caixa de digitar)
  if (ev.target.closest?.("input, textarea, select")) {
    if (ev.code === "Escape" && !campo("digitar").hidden) fecharDigitar();
    return;
  }
  if (ev.key === "/") {
    ev.preventDefault();
    abrirDigitar();
    return;
  }
  if (ev.code === "Tab") {
    ev.preventDefault();
    painel.alternarGaveta();
    return;
  }
  if (ev.code === "Escape" && painel.gavetaAberta()) {
    painel.alternarGaveta(false); // Esc fecha a gaveta antes de qualquer outra coisa
    return;
  }
  if (ev.code === "Escape" && (ouvinte?.emConversa || estado !== "IDLE")) {
    encerrarConversa();
    return;
  }
  if (ev.code !== "Space") return;
  ev.preventDefault();
  if (ev.repeat) return;
  if (estado === "IDLE") ouvinte?.ativarManual();
  else if (liveAtiva) {
    // Live: Espaço só corta a fala dela (a Live já sabe sozinha quando você terminou)
    if (estado === "PENSANDO" || estado === "FALANDO") {
      reprodutor.parar();
      const parcial = painel.cancelarResposta();
      if (parcial) painel.registrarLog("iris", parcial + " [interrompida]");
      definirEstado("OUVINDO");
    }
  } else if (estado === "OUVINDO") ouvinte?.concluirAgora();
  else interromper();
});
window.addEventListener("pointerdown", audio.destravar);

// ---------- Configurações ----------
const dialogo = document.getElementById("config");
const campo = (id) => document.getElementById(id);
const comSinal = (n) => (n >= 0 ? `+${n}` : `${n}`);
const velocidadeTexto = () => `${comSinal(Number(campo("cfg-velocidade").value))}%`;
const tomTexto = () => `${comSinal(Number(campo("cfg-tom").value))}Hz`;
let amostra = null;

function abrirConfig() {
  // enquanto a engrenagem está aberta a Iris não escuta (senão a amostra "Iris" a ativaria)
  if (!liveAtiva) ouvinte?.pausar();
  campo("cfg-voz").innerHTML = "";
  const grupos = {};
  for (const v of config.vozes || []) {
    if (!grupos[v.grupo]) {
      grupos[v.grupo] = document.createElement("optgroup");
      grupos[v.grupo].label = v.grupo;
      campo("cfg-voz").appendChild(grupos[v.grupo]);
    }
    grupos[v.grupo].appendChild(new Option(v.nome, v.id));
  }
  campo("cfg-nome").value = config.nome || "";
  campo("cfg-voz").value = config.voz;
  campo("cfg-velocidade").value = parseInt(config.velocidade) || 0;
  campo("cfg-tom").value = parseInt(config.tom) || 0;
  montarTracos();
  atualizarRotulos();
  dialogo.showModal();
}

/** Um controle deslizante (0–100%) para cada ajuste de personalidade. */
function montarTracos() {
  const caixa = campo("cfg-tracos");
  caixa.innerHTML = "";
  for (const t of config.personalidade || []) {
    const rotulo = document.createElement("label");
    rotulo.innerHTML = `<span class="rotulo-traco"><span></span><output></output></span>
      <input type="range" min="0" max="100" step="5">`;
    rotulo.querySelector("span span").textContent = t.rotulo;
    const deslizante = rotulo.querySelector("input");
    const valor = rotulo.querySelector("output");
    deslizante.dataset.traco = t.id;
    deslizante.value = t.nivel;
    valor.textContent = `${t.nivel}%`;
    deslizante.addEventListener("input", () => (valor.textContent = `${deslizante.value}%`));
    caixa.appendChild(rotulo);
  }
}

function atualizarRotulos() {
  campo("cfg-velocidade-valor").textContent = velocidadeTexto();
  campo("cfg-tom-valor").textContent = tomTexto();
  // velocidade e tom só valem para vozes do edge-tts
  const gemini = campo("cfg-voz").value.startsWith("gemini:");
  campo("cfg-ajustes-edge").hidden = gemini;
}

campo("cfg-velocidade").addEventListener("input", atualizarRotulos);
campo("cfg-tom").addEventListener("input", atualizarRotulos);
campo("cfg-voz").addEventListener("change", atualizarRotulos);

campo("cfg-ouvir").addEventListener("click", async () => {
  amostra?.pause();
  const botao = campo("cfg-ouvir");
  botao.textContent = "…";
  const params = new URLSearchParams({ voz: campo("cfg-voz").value, velocidade: velocidadeTexto(), tom: tomTexto() });
  try {
    const resposta = await fetch(`/voz/amostra?${params}`);
    if (!resposta.ok) throw new Error(await resposta.text());
    amostra = new Audio(URL.createObjectURL(await resposta.blob()));
    await amostra.play();
  } catch (erro) {
    painel.registrarLog("sistema", `Não consegui tocar a amostra: ${erro.message}`);
  } finally {
    botao.textContent = "▶ Ouvir";
  }
});

// ---------- Digitar em vez de falar ----------
function abrirDigitar() {
  campo("digitar").hidden = false;
  campo("digitar-texto").focus();
}

function fecharDigitar() {
  campo("digitar").hidden = true;
  campo("digitar-texto").value = "";
  campo("digitar-texto").blur();
}

/** O texto digitado vai para a Iris como se você tivesse falado. */
function enviarDigitado(texto) {
  painel.registrarLog("voce", texto);
  if (DESPEDIDA.test(normalizar(texto))) encerrarDepois = true;
  if (!liveAtiva && podeUsarLive()) iniciarLive(false); // abre a conversa, se ainda não estiver aberta
  if (liveAtiva) {
    enviar("live_texto", { texto });
    falaPendente = false;
    definirEstado("PENSANDO");
    renovarConversa();
  } else {
    // modo reserva (clássico)
    ouvinte?.pausar();
    definirEstado("PENSANDO");
    conversaClassica = true;
    enviar("mensagem", { texto });
  }
}

campo("digitar").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const texto = campo("digitar-texto").value.trim();
  fecharDigitar();
  if (texto) enviarDigitado(texto);
});
campo("abrir-digitar").addEventListener("click", (ev) => {
  ev.stopPropagation();
  abrirDigitar();
});

campo("abrir-config").addEventListener("click", abrirConfig);
campo("abrir-gaveta").addEventListener("click", (ev) => {
  ev.stopPropagation();
  painel.alternarGaveta();
});
campo("fechar-gaveta").addEventListener("click", () => painel.alternarGaveta(false));
// clicar fora da gaveta fecha; clicar fora do cartão de rascunho esconde o cartão
// (esconder não cancela nada: um e-mail pendente continua esperando o seu "pode enviar")
window.addEventListener("click", (ev) => {
  if (!campo("rascunho").hidden && !campo("rascunho").contains(ev.target) && !campo("gaveta").contains(ev.target)) {
    painel.mostrarRascunho(null);
  }
  if (painel.gavetaAberta() && !campo("gaveta").contains(ev.target)) painel.alternarGaveta(false);
});
// clicar fora da janela de configurações (no fundo escuro) fecha sem salvar
dialogo.addEventListener("click", (ev) => {
  const r = dialogo.getBoundingClientRect();
  const fora = ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom;
  if (ev.target === dialogo && fora) dialogo.close("cancelar");
});
dialogo.addEventListener("close", () => {
  amostra?.pause();
  if (estado === "IDLE" || estado === "OUVINDO") voltarAoIdle(); // volta a ouvir (ou segue a conversa)
  if (dialogo.returnValue !== "salvar") return;
  enviar("salvar_config", {
    nome: campo("cfg-nome").value,
    voz: campo("cfg-voz").value,
    velocidade: velocidadeTexto(),
    tom: tomTexto(),
    personalidade: Object.fromEntries(
      [...campo("cfg-tracos").querySelectorAll("input")].map((d) => [d.dataset.traco, Number(d.value)]),
    ),
  });
  painel.registrarLog("sistema", "Configurações salvas. Valem a partir da próxima conversa.");
});

// ---------- Início ----------
painel.iniciarRelogio();
definirEstado("IDLE");
painel.registrarLog("sistema", "Núcleo iniciado. Interface online.", false);
conectar();

// para depuração no console do navegador (F12): window.iris.nucleo.definirEstado("FALANDO")
window.iris = { nucleo, painel, reprodutor };
