// Roda numa thread de áudio separada: junta as amostras do microfone em blocos
// e manda para a página, junto com o horário (em segundos do AudioContext) de cada bloco.

const TAMANHO_BLOCO = 4096;

class Gravador extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bloco = new Float32Array(TAMANHO_BLOCO);
    this.pos = 0;
    this.inicioBloco = 0;
  }

  process(entradas) {
    const canal = entradas[0]?.[0];
    if (!canal) return true;
    for (let i = 0; i < canal.length; i++) {
      if (this.pos === 0) this.inicioBloco = currentTime + i / sampleRate;
      this.bloco[this.pos++] = canal[i];
      if (this.pos === TAMANHO_BLOCO) {
        this.port.postMessage({ t: this.inicioBloco, dados: this.bloco });
        this.bloco = new Float32Array(TAMANHO_BLOCO);
        this.pos = 0;
      }
    }
    return true;
  }
}

registerProcessor("gravador", Gravador);
