// Áudio da interface: toca a voz da Iris em fila, mede o volume do microfone
// e do que ela fala (para o núcleo reagir), e toca o bip de ativação.

const ctx = new AudioContext();

/** O navegador só libera som depois de uma interação; chamamos em cada tecla/clique. */
export function destravar() {
  if (ctx.state === "suspended") ctx.resume();
}

function rms(analisador, buffer) {
  analisador.getByteTimeDomainData(buffer);
  let soma = 0;
  for (const v of buffer) soma += ((v - 128) / 128) ** 2;
  return Math.sqrt(soma / buffer.length);
}

/** Converte PCM 16 bits (little-endian, mono, 24 kHz) em AudioBuffer tocável. */
function pcmParaBuffer(dados, taxa = 24000) {
  const amostras = new Int16Array(dados, 0, Math.floor(dados.byteLength / 2));
  const buffer = ctx.createBuffer(1, amostras.length, taxa);
  const canal = buffer.getChannelData(0);
  for (let i = 0; i < amostras.length; i++) canal[i] = amostras[i] / 32768;
  return buffer;
}

// ---------- Voz da Iris ----------
export class Reprodutor {
  constructor() {
    this.analisador = ctx.createAnalyser();
    this.analisador.fftSize = 256;
    this.analisador.smoothingTimeConstant = 0.75;
    this.analisador.connect(ctx.destination);
    this.freq = new Uint8Array(this.analisador.frequencyBinCount);
    this.onda = new Uint8Array(this.analisador.fftSize);
    this.aoTerminar = null;
    this._zerar();
    this.ignorando = false;
  }

  _zerar() {
    this.geracao = (this.geracao || 0) + 1; // invalida áudios de respostas antigas
    this.fontes = new Set();
    this.pendentes = 0;
    this.fimRecebido = false;
    this.proximoInicio = 0;
    this.inicioResposta = null; // quando a 1ª parte desta resposta começou a tocar
    this.tocouTudo = false;
    this.cadeia = Promise.resolve();
  }

  /** Quanto da resposta atual já tocou e quanto já chegou (em segundos), para a legenda acompanhar a voz. */
  progresso() {
    if (this.inicioResposta == null) return { tocado: 0, agendado: 0, terminou: this.tocouTudo };
    const agendado = this.proximoInicio - this.inicioResposta;
    const tocado = Math.max(0, Math.min(agendado, ctx.currentTime - this.inicioResposta));
    return { tocado, agendado, terminou: this.tocouTudo };
  }

  /** Nova resposta começando. */
  iniciar() {
    this.parar();
    this.ignorando = false;
    this.tocouTudo = false;
  }

  /** Recebe um pedaço de áudio do servidor e agenda para tocar logo após o anterior.
   *  1º byte: 1 = MP3 completo (edge-tts), 2 = pedaço PCM 16 bits 24 kHz (Gemini). */
  adicionar(pacote) {
    if (this.ignorando) return;
    const formato = new Uint8Array(pacote, 0, 1)[0];
    const dados = pacote.slice(1);
    const geracao = this.geracao;
    this.pendentes++;
    // a cadeia garante que os pedaços são decodificados e tocados na ordem
    this.cadeia = this.cadeia.then(async () => {
      try {
        const som = formato === 2 ? pcmParaBuffer(dados) : await ctx.decodeAudioData(dados);
        if (geracao !== this.geracao) return;
        const fonte = ctx.createBufferSource();
        fonte.buffer = som;
        fonte.connect(this.analisador);
        // se nada está tocando, dá uma folguinha para os próximos pedaços chegarem
        const folga = this.proximoInicio > ctx.currentTime ? 0 : formato === 2 ? 0.08 : 0.02;
        const inicio = Math.max(ctx.currentTime + folga, this.proximoInicio);
        fonte.start(inicio);
        if (this.inicioResposta == null) this.inicioResposta = inicio;
        this.proximoInicio = inicio + som.duration;
        this.fontes.add(fonte);
        fonte.onended = () => {
          this.fontes.delete(fonte);
          this._talvezTerminou();
        };
      } catch (erro) {
        console.warn("Falha ao tocar áudio", erro);
      } finally {
        if (geracao === this.geracao) {
          this.pendentes--;
          this._talvezTerminou();
        }
      }
    });
  }

  /** O servidor avisou que não vem mais áudio. */
  finalizar() {
    this.fimRecebido = true;
    this._talvezTerminou();
  }

  /** Para tudo imediatamente (interrupção). */
  parar() {
    for (const f of this.fontes) {
      f.onended = null;
      try { f.stop(); } catch {}
    }
    this.ignorando = true;
    this._zerar();
  }

  _talvezTerminou() {
    if (this.fimRecebido && this.pendentes === 0 && this.fontes.size === 0) {
      this.fimRecebido = false;
      this.tocouTudo = true;
      this.aoTerminar?.();
    }
  }

  nivel() { return Math.min(1, rms(this.analisador, this.onda) * 3.5); }
  espectro() { this.analisador.getByteFrequencyData(this.freq); return this.freq; }
}

// ---------- Microfone (só para medir volume; quem transcreve é o ouvir.js) ----------
export class Microfone {
  async iniciar() {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
    });
    this.analisador = ctx.createAnalyser();
    this.analisador.fftSize = 512;
    this.onda = new Uint8Array(this.analisador.fftSize);
    this.fonte = ctx.createMediaStreamSource(stream);
    this.fonte.connect(this.analisador);
  }

  nivel() {
    return this.analisador ? Math.min(1, rms(this.analisador, this.onda) * 6) : 0;
  }
}

// ---------- Gravador (áudio da sua fala para o Whisper) ----------
// Grava sem parar e guarda só os últimos segundos; quando você termina de falar,
// recorta o trecho do pedido e devolve como WAV de 16 kHz (o que o Whisper usa).
const GUARDAR_SEGUNDOS = 40;
const TAXA_WHISPER = 16000;

export class Gravador {
  async iniciar(microfone) {
    await ctx.audioWorklet.addModule("js/gravador-worklet.js");
    const no = new AudioWorkletNode(ctx, "gravador");
    this.blocos = [];
    this.aoBloco = null; // se definido, recebe cada bloco já em PCM 16 bits / 16 kHz (para a Live)
    no.port.onmessage = ({ data }) => {
      this.blocos.push(data);
      const limite = data.t - GUARDAR_SEGUNDOS;
      while (this.blocos.length && this.blocos[0].t < limite) this.blocos.shift();
      if (this.aoBloco) this.aoBloco(paraPcm16(reamostrar(data.dados, ctx.sampleRate, TAXA_WHISPER)));
    };
    microfone.fonte.connect(no);
    // ligado a um volume zero só para o navegador manter o nó processando
    const mudo = ctx.createGain();
    mudo.gain.value = 0;
    no.connect(mudo).connect(ctx.destination);
    this.ativo = true;
  }

  /** Marca onde começa o pedido. `antes` = segundos a incluir antes de agora. */
  marcar(antes = 0) {
    this.inicio = ctx.currentTime - antes;
  }

  /** Recorta do início marcado até agora e devolve um Blob WAV (ou null se não houver áudio). */
  recortar() {
    const amostras = this._desde(this.inicio);
    return amostras ? codificarWav(amostras, TAXA_WHISPER) : null;
  }

  /** Os últimos `segundos` gravados, em PCM 16 bits / 16 kHz (o começo da fala, para a Live). */
  pcmRecente(segundos) {
    const amostras = this._desde(ctx.currentTime - segundos);
    return amostras ? paraPcm16(amostras) : null;
  }

  _desde(inicio) {
    if (!this.ativo || inicio == null) return null;
    const trechos = this.blocos.filter((b) => b.t + b.dados.length / ctx.sampleRate > inicio);
    if (!trechos.length) return null;
    const total = trechos.reduce((n, b) => n + b.dados.length, 0);
    const juntos = new Float32Array(total);
    let pos = 0;
    for (const b of trechos) {
      juntos.set(b.dados, pos);
      pos += b.dados.length;
    }
    return reamostrar(juntos, ctx.sampleRate, TAXA_WHISPER);
  }
}

function paraPcm16(amostras) {
  const pcm = new Int16Array(amostras.length);
  for (let i = 0; i < amostras.length; i++) {
    const s = Math.max(-1, Math.min(1, amostras[i]));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return pcm.buffer;
}

function reamostrar(amostras, de, para) {
  if (de === para) return amostras;
  const razao = de / para;
  const saida = new Float32Array(Math.floor(amostras.length / razao));
  for (let i = 0; i < saida.length; i++) {
    // média das amostras que caem neste ponto (evita chiado)
    const ini = Math.floor(i * razao);
    const fim = Math.min(amostras.length, Math.floor((i + 1) * razao));
    let soma = 0;
    for (let j = ini; j < fim; j++) soma += amostras[j];
    saida[i] = soma / Math.max(1, fim - ini);
  }
  return saida;
}

function codificarWav(amostras, taxa) {
  const buffer = new ArrayBuffer(44 + amostras.length * 2);
  const v = new DataView(buffer);
  const texto = (pos, s) => [...s].forEach((c, i) => v.setUint8(pos + i, c.charCodeAt(0)));
  texto(0, "RIFF");
  v.setUint32(4, 36 + amostras.length * 2, true);
  texto(8, "WAVE");
  texto(12, "fmt ");
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true);          // PCM
  v.setUint16(22, 1, true);          // mono
  v.setUint32(24, taxa, true);
  v.setUint32(28, taxa * 2, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  texto(36, "data");
  v.setUint32(40, amostras.length * 2, true);
  for (let i = 0; i < amostras.length; i++) {
    const s = Math.max(-1, Math.min(1, amostras[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}

// ---------- Bip de ativação ----------
export function bip() {
  const agora = ctx.currentTime;
  const osc = ctx.createOscillator();
  const ganho = ctx.createGain();
  osc.type = "sine";
  osc.frequency.setValueAtTime(880, agora);
  osc.frequency.exponentialRampToValueAtTime(1500, agora + 0.12);
  ganho.gain.setValueAtTime(0.0001, agora);
  ganho.gain.exponentialRampToValueAtTime(0.08, agora + 0.02);
  ganho.gain.exponentialRampToValueAtTime(0.0001, agora + 0.18);
  osc.connect(ganho).connect(ctx.destination);
  osc.start(agora);
  osc.stop(agora + 0.2);
}
