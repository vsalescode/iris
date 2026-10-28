// Núcleo animado no centro do HUD. Desenhado num <canvas> a cada quadro.
// Estados: IDLE (pulsa devagar), OUVINDO (reage ao volume do mic),
// PENSANDO (gira e processa), FALANDO (ondas sincronizadas com o áudio).

const CORES = {
  IDLE: [62, 232, 255],
  OUVINDO: [154, 244, 255],
  PENSANDO: [90, 140, 255],
  FALANDO: [62, 232, 255],
};

export class Nucleo {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.estado = "IDLE";
    this.nivelAlvo = 0;      // volume informado de fora (0 a 1)
    this.nivel = 0;          // volume suavizado
    this.espectro = null;    // função que devolve Uint8Array de frequências (opcional)
    this.cor = [...CORES.IDLE];
    this.t = 0;
    this.giro = 0;
    this.velocidadeGiro = 0.15;
    this.particulas = Array.from({ length: 70 }, () => ({
      angulo: Math.random() * Math.PI * 2,
      raio: 1.15 + Math.random() * 0.75,
      vel: (Math.random() * 0.5 + 0.15) * (Math.random() < 0.5 ? -1 : 1),
      tamanho: Math.random() * 1.6 + 0.4,
      fase: Math.random() * Math.PI * 2,
    }));

    new ResizeObserver(() => this._redimensionar()).observe(canvas);
    this._redimensionar();
    this._ultimo = performance.now();
    requestAnimationFrame((t) => this._quadro(t));
  }

  definirEstado(estado) { this.estado = estado; }
  definirNivel(v) { this.nivelAlvo = Math.max(0, Math.min(1, v)); }
  definirEspectro(fn) { this.espectro = fn; }

  _redimensionar() {
    const dpr = window.devicePixelRatio || 1;
    const { width, height } = this.canvas.getBoundingClientRect();
    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.w = width;
    this.h = height;
  }

  _quadro(agora) {
    const dt = Math.min(0.05, (agora - this._ultimo) / 1000);
    this._ultimo = agora;
    this.dt = dt;
    this.t += dt;

    // suaviza volume, cor e velocidade de giro para as transições ficarem macias
    this.nivel += (this.nivelAlvo - this.nivel) * Math.min(1, dt * 12);
    const alvoCor = CORES[this.estado] || CORES.IDLE;
    this.cor = this.cor.map((c, i) => c + (alvoCor[i] - c) * Math.min(1, dt * 4));
    const alvoGiro = { IDLE: 0.15, OUVINDO: 0.35, PENSANDO: 2.4, FALANDO: 0.5 }[this.estado] ?? 0.15;
    this.velocidadeGiro += (alvoGiro - this.velocidadeGiro) * Math.min(1, dt * 3);
    this.giro += this.velocidadeGiro * dt;

    this._desenhar();
    requestAnimationFrame((t) => this._quadro(t));
  }

  _rgba(a) {
    const [r, g, b] = this.cor;
    return `rgba(${r | 0}, ${g | 0}, ${b | 0}, ${a})`;
  }

  _desenhar() {
    const { ctx, w, h, t } = this;
    ctx.clearRect(0, 0, w, h);
    const cx = w / 2;
    const cy = h / 2 - h * 0.03;
    const R = Math.min(w, h) * 0.2;

    // quanto o núcleo "respira" em cada estado
    let pulso = 0;
    if (this.estado === "IDLE") pulso = Math.sin(t * 1.3) * 0.035;
    else if (this.estado === "OUVINDO") pulso = this.nivel * 0.28 + Math.sin(t * 3) * 0.01;
    else if (this.estado === "PENSANDO") pulso = Math.sin(t * 5) * 0.02;
    else if (this.estado === "FALANDO") pulso = this.nivel * 0.18;

    ctx.save();
    ctx.translate(cx, cy);

    this._halo(R, pulso);
    this._marcas(R * 1.62);
    this._arcos(R * 1.32);
    this._particulas(R);
    this._anelPrincipal(R * (1 + pulso));
    this._miolo(R * 0.58 * (1 + pulso * 1.4));

    ctx.restore();
  }

  _halo(R, pulso) {
    const { ctx } = this;
    const g = ctx.createRadialGradient(0, 0, R * 0.2, 0, 0, R * 2.4);
    g.addColorStop(0, this._rgba(0.16 + pulso * 0.4));
    g.addColorStop(0.45, this._rgba(0.05));
    g.addColorStop(1, this._rgba(0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(0, 0, R * 2.4, 0, Math.PI * 2);
    ctx.fill();
  }

  // anel externo de "réguas" finas
  _marcas(raio) {
    const { ctx } = this;
    const total = 120;
    ctx.save();
    ctx.rotate(-this.giro * 0.25);
    for (let i = 0; i < total; i++) {
      const a = (i / total) * Math.PI * 2;
      const longa = i % 10 === 0;
      const tam = longa ? 10 : 4;
      ctx.strokeStyle = this._rgba(longa ? 0.55 : 0.22);
      ctx.lineWidth = longa ? 1.4 : 1;
      ctx.beginPath();
      ctx.moveTo(Math.cos(a) * raio, Math.sin(a) * raio);
      ctx.lineTo(Math.cos(a) * (raio + tam), Math.sin(a) * (raio + tam));
      ctx.stroke();
    }
    ctx.restore();
  }

  // arcos segmentados que giram (rápido no PENSANDO)
  _arcos(raio) {
    const { ctx } = this;
    const pensando = this.estado === "PENSANDO";
    const camadas = [
      { r: raio, larg: 2, sent: 1, segs: [[0, 0.9], [1.3, 2.2], [3.1, 4.6]] },
      { r: raio * 0.9, larg: 1, sent: -1.6, segs: [[0.4, 1.2], [2.5, 3.0], [4.0, 5.6]] },
    ];
    for (const c of camadas) {
      ctx.save();
      ctx.rotate(this.giro * c.sent);
      ctx.strokeStyle = this._rgba(pensando ? 0.85 : 0.45);
      ctx.lineWidth = c.larg;
      ctx.shadowColor = this._rgba(0.9);
      ctx.shadowBlur = pensando ? 14 : 6;
      for (const [a, b] of c.segs) {
        ctx.beginPath();
        ctx.arc(0, 0, c.r, a, b);
        ctx.stroke();
      }
      ctx.restore();
    }
  }

  _particulas(R) {
    const { ctx, t } = this;
    const acelera = { PENSANDO: 3, FALANDO: 1.5, OUVINDO: 1.2 }[this.estado] ?? 0.6;
    for (const p of this.particulas) {
      p.angulo += p.vel * 0.25 * acelera * this.dt;
      const r = R * p.raio * (1 + this.nivel * 0.15);
      const brilho = 0.25 + 0.35 * (0.5 + 0.5 * Math.sin(t * 2 + p.fase));
      ctx.fillStyle = this._rgba(brilho);
      ctx.beginPath();
      ctx.arc(Math.cos(p.angulo) * r, Math.sin(p.angulo) * r, p.tamanho, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // anel principal: no FALANDO vira uma onda que segue o áudio
  _anelPrincipal(raio) {
    const { ctx, t } = this;
    const pontos = 180;
    const dados = this.estado === "FALANDO" && this.espectro ? this.espectro() : null;

    ctx.save();
    ctx.shadowColor = this._rgba(1);
    ctx.shadowBlur = 22;
    ctx.strokeStyle = this._rgba(0.95);
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    for (let i = 0; i <= pontos; i++) {
      const a = (i / pontos) * Math.PI * 2;
      let desloc = 0;
      if (this.estado === "FALANDO") {
        if (dados) {
          // espelha o espectro para a onda fechar sem "degrau"
          const idx = Math.floor((i <= pontos / 2 ? i : pontos - i) / (pontos / 2) * (dados.length * 0.6));
          desloc = (dados[idx] / 255) * 0.22;
        } else {
          desloc = this.nivel * 0.12 * (Math.sin(a * 6 + t * 7) + Math.sin(a * 11 - t * 9) * 0.6);
        }
      } else if (this.estado === "OUVINDO") {
        desloc = this.nivel * 0.05 * Math.sin(a * 8 + t * 6);
      }
      const r = raio * (1 + desloc);
      const x = Math.cos(a) * r;
      const y = Math.sin(a) * r;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.stroke();

    // segundo anel fino, levemente defasado
    ctx.shadowBlur = 0;
    ctx.strokeStyle = this._rgba(0.3);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(0, 0, raio * 0.86, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  _miolo(raio) {
    const { ctx } = this;
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, raio);
    g.addColorStop(0, this._rgba(0.55 + this.nivel * 0.4));
    g.addColorStop(0.35, this._rgba(0.22));
    g.addColorStop(1, this._rgba(0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(0, 0, raio, 0, Math.PI * 2);
    ctx.fill();

    // hexágono girando no meio
    ctx.save();
    ctx.rotate(-this.giro * 0.6);
    ctx.strokeStyle = this._rgba(0.6);
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (let i = 0; i <= 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      const x = Math.cos(a) * raio * 0.42;
      const y = Math.sin(a) * raio * 0.42;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();
  }
}
