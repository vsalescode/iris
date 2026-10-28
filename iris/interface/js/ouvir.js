// Ouvido da Iris: usa o reconhecimento de voz do navegador (Web Speech API).
//
// Modos:
//   fundo   -> ouve sem parar procurando a palavra de ativação ("Iris")
//   comando -> ativada: junta o que você fala e envia após a pausa
//   pausado -> desligado enquanto ela fala (para não ouvir a própria voz)
//
// Modo conversa: depois de chamada uma vez, tudo que você fala é com ela
// (sem repetir "Iris") até um tempo de silêncio ou até a conversa ser encerrada.

const ESPERA_SEM_FALA_MS = 8000; // ativou e não falou nada -> volta a dormir

const palavras = (texto) => texto.trim().split(/\s+/).filter(Boolean);
const normalizar = (p) =>
  p.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");

export class Ouvinte {
  /**
   * @param config  { idioma, pausa_segundos, palavras_ativacao }
   * @param eventos { aoOuvirFundo(texto), aoAtivar(), aoTranscrever(final, parcial),
   *                  aoComando(texto), aoDesistir(), aoErro(mensagem) }
   *   aoAtivar recebe true se a ativação foi pela voz ("Iris") e false se pelo teclado.
   *   aoFimDeFrase(texto) (opcional): o reconhecedor fechou a frase; o envio vem logo depois.
   */
  constructor(config, eventos) {
    this.eventos = eventos;
    const Reconhecimento = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Reconhecimento) {
      this.indisponivel = true;
      eventos.aoErro("Este navegador não tem reconhecimento de voz. Use o Edge.");
      return;
    }
    this.pausaMs = (config.pausa_segundos ?? 1.5) * 1000;
    // quando o reconhecedor já "fechou" a frase, dá para responder mais cedo
    this.pausaFinalMs = (config.pausa_final_segundos ?? 0.8) * 1000;
    this.conversaMs = (config.conversa_segundos ?? 60) * 1000;
    this.emConversa = false;
    // usamos a última palavra de cada expressão: "ei iris" -> "iris"
    this.ativacao = new Set(config.palavras_ativacao.map((p) => normalizar(palavras(p).pop())));

    this.modo = "fundo";
    this.ligado = false;
    this.falhasSeguidas = 0;
    this._reiniciarSessao();

    this.rec = new Reconhecimento();
    this.rec.lang = config.idioma || "pt-BR";
    this.rec.continuous = true;
    this.rec.interimResults = true;
    this.rec.onresult = (e) => this._resultado(e);
    this.rec.onerror = (e) => this._erro(e);
    this.rec.onend = () => this._fimDaSessao();
  }

  iniciar() {
    this._ligar();
  }

  /** Ativação pelo teclado (Espaço). */
  ativarManual() {
    if (this.indisponivel) return;
    this.emConversa = true;
    this.modo = "comando";
    this.idxAtivacao = -1;
    this.base = this.totalResultados; // ignora o que já tinha sido ouvido
    this.prefixo = [];
    this.cmdFinal = [];
    this.cmdParcial = [];
    this.eventos.aoAtivar(false);
    this._agendar();
    this._ligar();
  }

  /** Envia agora o que já foi falado (ou desiste se não houver nada). */
  concluirAgora() {
    this._concluir();
  }

  /** Desliga enquanto a Iris fala. */
  pausar() {
    this.modo = "pausado";
    clearTimeout(this.timer);
    try { this.rec?.abort(); } catch {}
  }

  /** Volta a ouvir em segundo plano. */
  retomar() {
    if (this.indisponivel) return;
    this.modo = "fundo";
    clearTimeout(this.timer);
    this._ligar();
  }

  /** Em conversa: depois que ela responde, já ouve o próximo pedido, sem precisar do nome. */
  continuarConversa() {
    if (this.indisponivel) return;
    this.modo = "comando";
    this.idxAtivacao = -1;
    this.base = this.totalResultados;
    this.prefixo = [];
    this.cmdFinal = [];
    this.cmdParcial = [];
    this._agendar();
    this._ligar();
  }

  /** Sai do modo conversa (volta a exigir "Iris"). */
  encerrarConversa() {
    this.emConversa = false;
    if (this.modo === "comando") {
      clearTimeout(this.timer);
      this.modo = "fundo";
      this.base = this.totalResultados;
    }
  }

  // ---------- interno ----------

  _reiniciarSessao() {
    this.base = 0;            // primeiro resultado que ainda interessa nesta sessão
    this.totalResultados = 0;
    this.idxAtivacao = -1;    // posição da palavra "Iris" (em palavras, a partir de base)
    this.prefixo = [];        // palavras do comando vindas de uma sessão anterior
    this.cmdFinal = [];
    this.cmdParcial = [];
  }

  _ligar() {
    if (this.ligado || this.modo === "pausado" || this.bloqueado) return;
    try {
      this.rec.start();
      this.ligado = true;
    } catch {
      // já estava ligado; o onend religa se precisar
    }
  }

  _resultado(e) {
    this.falhasSeguidas = 0;
    this.totalResultados = e.results.length;
    const finais = [];
    const parciais = [];
    let ultimoFinal = this.base;
    for (let i = this.base; i < e.results.length; i++) {
      const trecho = e.results[i][0].transcript;
      if (e.results[i].isFinal) {
        finais.push(trecho);
        ultimoFinal = i + 1;
      } else {
        parciais.push(trecho);
      }
    }
    const pf = palavras(finais.join(" "));
    const pp = palavras(parciais.join(" "));

    if (this.modo === "fundo") {
      const todas = [...pf, ...pp];
      const idx = todas.findIndex((p) => this._ehAtivacao(p));
      if (idx === -1) {
        this.eventos.aoOuvirFundo(todas.join(" "));
        this.base = ultimoFinal; // descarta o que já foi finalizado sem "Iris"
        return;
      }
      this.modo = "comando";
      this.emConversa = true;
      this.idxAtivacao = idx;
      this.prefixo = [];
      this.eventos.aoAtivar(true);
    }

    if (this.modo === "comando") {
      // o reconhecedor corrige o texto enquanto você fala; se a palavra "Iris"
      // mudou de posição, recalcula onde o pedido começa
      if (this.idxAtivacao >= 0) {
        const idx = [...pf, ...pp].findIndex((p) => this._ehAtivacao(p));
        if (idx !== -1) this.idxAtivacao = idx;
      }
      const inicio = this.idxAtivacao + 1;
      this.cmdFinal = [...this.prefixo, ...pf.slice(inicio)];
      this.cmdParcial = pp.slice(Math.max(0, inicio - pf.length));
      this.eventos.aoTranscrever(this.cmdFinal.join(" "), this.cmdParcial.join(" "));
      // frase fechada e nada em andamento: provável fim da fala (o app já adianta o Whisper)
      if (this.cmdFinal.length && !this.cmdParcial.length) this.eventos.aoFimDeFrase?.(this.cmdFinal.join(" "));
      this._agendar();
    }
  }

  /** Tira a palavra de ativação (e o que veio antes dela) de um texto. */
  removerAtivacao(texto) {
    const lista = palavras(texto);
    const idx = lista.findIndex((p) => this._ehAtivacao(p));
    return idx === -1 ? texto : lista.slice(idx + 1).join(" ").replace(/^[\s,.!?;:]+/, "");
  }

  _ehAtivacao(palavra) {
    const p = normalizar(palavra);
    // "eiiris"/"eiris" acontecem quando o reconhecedor junta "ei iris"
    return this.ativacao.has(p) || [...this.ativacao].some((a) => p.length <= a.length + 2 && p.endsWith(a));
  }

  /** Reinicia o cronômetro de silêncio. */
  _agendar() {
    clearTimeout(this.timer);
    let espera;
    if (this.cmdParcial.length) espera = this.pausaMs;             // ainda falando
    else if (this.cmdFinal.length) espera = this.pausaFinalMs;      // frase fechada
    else espera = this.emConversa ? this.conversaMs : ESPERA_SEM_FALA_MS;
    this.timer = setTimeout(() => this._concluir(), espera);
  }

  _concluir() {
    clearTimeout(this.timer);
    if (this.modo !== "comando") return;
    const texto = [...this.cmdFinal, ...this.cmdParcial].join(" ").trim();
    if (!texto) {
      this.emConversa = false; // ficou em silêncio: encerra a conversa
      this.modo = "fundo";
      this.base = this.totalResultados;
      this.eventos.aoDesistir();
      return;
    }
    this.pausar();
    this.eventos.aoComando(texto);
  }

  _erro(e) {
    if (e.error === "no-speech" || e.error === "aborted") return;
    if (e.error === "not-allowed" || e.error === "service-not-allowed") {
      this.bloqueado = true;
      this.eventos.aoErro("Sem permissão para usar o microfone. Libere no ícone de cadeado/câmera da janela e recarregue (F5).");
    } else if (e.error === "audio-capture") {
      this.eventos.aoErro("Nenhum microfone encontrado.");
    } else if (e.error === "network") {
      this.falhasSeguidas++;
      if (this.falhasSeguidas === 1) this.eventos.aoErro("O reconhecimento de voz precisa de internet. Tentando de novo…");
    } else {
      this.eventos.aoErro(`Reconhecimento de voz: ${e.error}`);
    }
  }

  _fimDaSessao() {
    this.ligado = false;
    // o navegador encerra a sessão de tempos em tempos; guardamos o comando em andamento
    const prefixo = this.modo === "comando" ? this.cmdFinal : [];
    this._reiniciarSessao();
    this.prefixo = prefixo;
    this.cmdFinal = [...prefixo];
    if (this.modo === "pausado" || this.bloqueado) return;
    const espera = this.falhasSeguidas ? Math.min(10000, 1000 * this.falhasSeguidas) : 200;
    setTimeout(() => this._ligar(), espera);
  }
}
