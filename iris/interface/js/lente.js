// A presença da Iris: a íris de uma lente de câmera (WebGL com Three.js), desenhada no shader.
// No centro, um diafragma de lâminas que abre e fecha; em volta, anéis de instrumento:
// um medidor radial que reage à voz, escalas, anéis tracejados e miras.
// Mesmo jeito de usar do núcleo 2D: definirEstado / definirNivel / definirEspectro.
//
// Estados:
//   IDLE      o diafragma respira, o medidor quase parado, as escalas giram devagar
//   OUVINDO   o diafragma abre e o medidor acompanha a sua voz
//   PENSANDO  as lâminas giram, o medidor corre em volta, tom violeta, um arco varre
//   FALANDO   o medidor pulsa com a voz dela e o centro acende

import * as THREE from "three";

const ESTADOS = {
  //          abertura giro   brilho varredura  traço (magenta)        apoio (violeta)        quente (âmbar)
  IDLE:     { abertura: 0.24, giro: 0.04, brilho: 0.85, varredura: 0.0,
              traco: [1.0, 0.36, 0.6], apoio: [0.55, 0.38, 1.0], quente: [1.0, 0.66, 0.32] },
  OUVINDO:  { abertura: 0.33, giro: 0.05, brilho: 1.1, varredura: 0.0,
              traco: [1.0, 0.45, 0.7], apoio: [0.62, 0.45, 1.0], quente: [1.0, 0.75, 0.42] },
  PENSANDO: { abertura: 0.15, giro: 0.6, brilho: 0.95, varredura: 1.0,
              traco: [0.7, 0.42, 1.0], apoio: [0.45, 0.38, 1.0], quente: [0.85, 0.6, 1.0] },
  FALANDO:  { abertura: 0.22, giro: 0.06, brilho: 1.05, varredura: 0.0,
              traco: [1.0, 0.32, 0.56], apoio: [0.55, 0.36, 1.0], quente: [1.0, 0.66, 0.3] },
};

const VERTICE = /* glsl */ `void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }`;

const FRAGMENTO = /* glsl */ `
precision highp float;
uniform vec2 uCentro;
uniform float uRaio, uTempo, uAbertura, uGiro, uBrilho, uNivel, uVarredura, uPensando;
uniform vec3 uTraco, uApoio, uQuente;

const float PI = 3.14159265;
const float LAMINAS = 8.0;

float acaso(float n) { return fract(sin(n * 12.9898) * 43758.5453); }
float linha(float d, float largura) { return smoothstep(largura, 0.0, abs(d)); }
float anel(float r, float raio, float largura) { return linha(r - raio, largura); }

void main() {
  vec2 p = (gl_FragCoord.xy - uCentro) / uRaio;
  float r = length(p);
  float ang = atan(p.y, p.x);                    // -PI..PI
  float volta = (ang + PI) / (2.0 * PI);         // 0..1
  float px = 1.5 / uRaio;                        // ~1 pixel, para linhas nítidas
  vec3 cor = vec3(0.0);

  // ---------- diafragma: abertura poligonal de 8 lâminas ----------
  float setor = 2.0 * PI / LAMINAS;
  float angGiro = ang + uGiro;
  float borda = uAbertura * cos(PI / LAMINAS) / cos(mod(angGiro, setor) - PI / LAMINAS);
  float aberto = smoothstep(borda + px, borda - px, r);
  float zona = smoothstep(0.44 + px, 0.44 - px, r) * (1.0 - aberto);
  // emendas das lâminas: linhas em espiral saindo dos vértices
  float emenda = abs(fract((angGiro - (r - uAbertura) * 1.4) / setor) - 0.5) * setor * r;
  float metal = 0.07 + 0.06 * fract((angGiro - (r - uAbertura) * 1.4) / setor);
  cor += uApoio * metal * zona;
  cor += uTraco * linha(emenda, px * 1.2) * zona * 0.55;
  cor += uTraco * linha(r - borda, px * 1.5) * 0.9;              // contorno da abertura
  // núcleo de luz no fundo da abertura
  cor += mix(uQuente, uTraco, 0.4) * exp(-r * r / (uAbertura * uAbertura * 0.18)) * (0.55 + uNivel * 0.9) * aberto;

  // ---------- medidor radial (barras) ----------
  float barras = 120.0;
  float i = floor(volta * barras);
  float dentroBarra = abs(fract(volta * barras) - 0.5) < 0.32 ? 1.0 : 0.0;
  float altura = 0.12 + 0.1 * sin(uTempo * 0.8 + i * 0.5);
  altura += uNivel * (0.25 + 0.75 * acaso(i + floor(uTempo * 18.0)));
  // pensando: uma onda corre em volta
  altura += uPensando * 1.0 * pow(0.5 + 0.5 * sin(volta * 2.0 * PI * 3.0 - uTempo * 6.0), 4.0);
  float h = (r - 0.5) / 0.17;
  float acesa = step(0.0, h) * step(h, min(altura, 1.0)) * dentroBarra;
  cor += mix(uQuente, uTraco, clamp(h * 1.3, 0.0, 1.0)) * acesa * 0.95;
  cor += uApoio * step(0.0, h) * step(h, 1.0) * dentroBarra * 0.05;   // trilho apagado

  // ---------- anéis de instrumento ----------
  cor += uApoio * anel(r, 0.47, px) * 0.6;
  // anel tracejado que gira
  float traco1 = step(0.45, fract(volta * 48.0 + uTempo * 0.05 * (1.0 + uVarredura * 6.0)));
  cor += uTraco * anel(r, 0.72, px * 1.2) * traco1 * 0.8;
  // escala: marcas finas a cada 2°, longas a cada 10°, girando ao contrário
  float escala = fract(volta * 180.0 - uTempo * 0.01 * (1.0 + uVarredura * 8.0));
  float longa = step(0.8, fract(floor(volta * 180.0 - uTempo * 0.01 * (1.0 + uVarredura * 8.0)) / 5.0));
  float marca = linha((escala - 0.5) * 2.0 * PI * r / 180.0, px * 0.8);
  float altMarca = mix(0.035, 0.07, longa);
  cor += uApoio * marca * step(0.8, r) * step(r, 0.8 + altMarca) * (0.5 + longa * 0.4);
  cor += uApoio * anel(r, 0.8, px) * 0.45;
  // anel externo e miras nos quatro pontos
  cor += uTraco * anel(r, 0.98, px * 1.4) * 0.75;
  float cruz = min(abs(p.x), abs(p.y));
  cor += uTraco * linha(cruz, px) * step(1.04, r) * step(r, 1.16) * 0.8;
  cor += uTraco * anel(r, 1.16, px) * step(0.97, fract(volta * 4.0 + 0.485)) * 0.9; // colchetes
  // pontos em órbita
  for (int k = 0; k < 3; k++) {
    float a = uTempo * (0.25 + float(k) * 0.12) * (k == 1 ? -1.0 : 1.0) + float(k) * 2.1;
    vec2 ponto = vec2(cos(a), sin(a)) * (1.08 + float(k) * 0.05);
    cor += mix(uQuente, uTraco, float(k) * 0.5) * smoothstep(px * 4.0, 0.0, length(p - ponto));
  }
  // pensando: arco de varredura
  float arco = fract((ang - uTempo * 2.4) / (2.0 * PI));
  cor += uApoio * anel(r, 0.9, px * 2.0) * pow(arco, 4.0) * uVarredura * 1.5;
  // brilho fraco em volta, como vidro de lente
  cor += uApoio * exp(-abs(r - 0.98) * 9.0) * 0.08;

  cor = clamp(cor * uBrilho, 0.0, 1.0);
  gl_FragColor = vec4(cor, max(max(cor.r, cor.g), cor.b)); // cor já multiplicada pela transparência
}`;

export class Lente {
  constructor(canvas) {
    this.canvas = canvas;
    this.estado = "IDLE";
    this.nivelAlvo = 0;
    this.nivel = 0;
    this.atual = structuredClone(ESTADOS.IDLE);
    this.giro = 0;

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true, premultipliedAlpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.cena = new THREE.Scene();
    this.camera = new THREE.Camera();
    const cor = () => ({ value: new THREE.Color() });
    this.u = {
      uCentro: { value: new THREE.Vector2() }, uRaio: { value: 100 },
      uTempo: { value: 0 }, uAbertura: { value: 0.24 }, uGiro: { value: 0 }, uBrilho: { value: 1 },
      uNivel: { value: 0 }, uVarredura: { value: 0 }, uPensando: { value: 0 },
      uTraco: cor(), uApoio: cor(), uQuente: cor(),
    };
    this.cena.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
      uniforms: this.u, vertexShader: VERTICE, fragmentShader: FRAGMENTO, transparent: false, depthTest: false,
    })));

    new ResizeObserver(() => this._redimensionar()).observe(canvas);
    this._redimensionar();
    this.relogio = new THREE.Clock();
    this.renderer.setAnimationLoop(() => this._quadro());
  }

  definirEstado(estado) { this.estado = ESTADOS[estado] ? estado : "IDLE"; }
  definirNivel(v) { this.nivelAlvo = Math.max(0, Math.min(1, v)); }
  definirEspectro() {} // a lente usa só o volume

  _redimensionar() {
    const { width, height } = this.canvas.getBoundingClientRect();
    if (!width || !height) return;
    this.renderer.setSize(width, height, false);
    const escala = this.renderer.getPixelRatio();
    // um pouco acima do centro: a fala aparece embaixo, à esquerda
    this.u.uCentro.value.set(width * escala * 0.5, height * escala * 0.58);
    this.u.uRaio.value = Math.min(width, height) * escala * 0.22;
  }

  _quadro() {
    const dt = Math.min(this.relogio.getDelta(), 0.05);
    const t = this.relogio.elapsedTime;
    const alvo = ESTADOS[this.estado];
    const suave = (atual, destino, vel) => atual + (destino - atual) * Math.min(1, dt * vel);
    const a = this.atual;
    const u = this.u;

    this.nivel = suave(this.nivel, this.nivelAlvo, 14);
    for (const chave of ["abertura", "giro", "brilho", "varredura"]) a[chave] = suave(a[chave], alvo[chave], 3);
    for (const chave of ["traco", "apoio", "quente"]) a[chave] = a[chave].map((c, i) => suave(c, alvo[chave][i], 3));

    const ouvindo = this.estado === "OUVINDO" ? this.nivel : 0;
    const falando = this.estado === "FALANDO" ? this.nivel : 0;
    const respirar = this.estado === "IDLE" ? Math.sin(t * 0.9) * 0.012 : 0;
    // o diafragma abre quando você fala e "pulsa" de leve com a voz dela
    u.uAbertura.value = suave(u.uAbertura.value, a.abertura + respirar + ouvindo * 0.06 + falando * 0.03, 10);
    this.giro += dt * a.giro;
    u.uGiro.value = this.giro;
    u.uTempo.value = t;
    u.uBrilho.value = a.brilho + ouvindo * 0.25 + falando * 0.2;
    u.uNivel.value = suave(u.uNivel.value, Math.max(ouvindo, falando), 16);
    u.uVarredura.value = a.varredura;
    u.uPensando.value = suave(u.uPensando.value, this.estado === "PENSANDO" ? 1 : 0, 3);
    u.uTraco.value.setRGB(...a.traco);
    u.uApoio.value.setRGB(...a.apoio);
    u.uQuente.value.setRGB(...a.quente);

    this.renderer.render(this.cena, this.camera);
  }
}
