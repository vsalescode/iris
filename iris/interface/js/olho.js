// A presença da Iris: a íris de um olho, feita de fibras de luz (WebGL com Three.js).
// Tudo é desenhado no shader, sem imagens. Mesmo jeito de usar do núcleo 2D:
// definirEstado / definirNivel / definirEspectro.
//
// Estados:
//   IDLE      a pupila respira devagar, as fibras quase paradas
//   OUVINDO   a pupila dilata com a sua voz e a íris se acende
//   PENSANDO  as camadas de fibras giram em sentidos opostos, tom violeta, um arco varre em volta
//   FALANDO   ondas de luz saem da pupila no ritmo da voz dela

import * as THREE from "three";

const ESTADOS = {
  //          pupila giro   brilho  varredura  centro (âmbar)        meio (magenta)          borda (violeta)
  IDLE:     { pupila: 0.33, giro: 0.02, brilho: 0.85, varredura: 0.0,
              centro: [1.0, 0.62, 0.28], meio: [1.0, 0.3, 0.58], borda: [0.52, 0.32, 1.0] },
  OUVINDO:  { pupila: 0.42, giro: 0.03, brilho: 1.15, varredura: 0.0,
              centro: [1.0, 0.72, 0.4], meio: [1.0, 0.38, 0.66], borda: [0.6, 0.4, 1.0] },
  PENSANDO: { pupila: 0.26, giro: 0.35, brilho: 0.95, varredura: 1.0,
              centro: [0.85, 0.55, 1.0], meio: [0.62, 0.36, 1.0], borda: [0.35, 0.3, 1.0] },
  FALANDO:  { pupila: 0.31, giro: 0.05, brilho: 1.05, varredura: 0.0,
              centro: [1.0, 0.65, 0.3], meio: [1.0, 0.28, 0.55], borda: [0.55, 0.32, 1.0] },
};

const VERTICE = /* glsl */ `void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }`;

const FRAGMENTO = /* glsl */ `
precision highp float;
uniform vec2 uCentro;          // centro da íris na tela (pixels)
uniform float uRaio;           // raio da íris (pixels)
uniform float uTempo, uPupila, uGiro1, uGiro2, uBrilho, uNivel, uFala, uVarredura;
uniform vec3 uCorCentro, uCorMeio, uCorBorda;

const float PI = 3.14159265;

float acaso(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float ruido(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(acaso(i), acaso(i + vec2(1, 0)), u.x), mix(acaso(i + vec2(0, 1)), acaso(i + vec2(1, 1)), u.x), u.y);
}
// ruído que dá a volta certinho no ângulo (sem emenda)
float fibras(float angulo, float r, float giro, float densidade, float semente) {
  float a = (angulo + giro) / (2.0 * PI) * densidade;
  float n1 = ruido(vec2(a, r * 2.5 + semente));
  float n2 = ruido(vec2(a - densidade, r * 2.5 + semente));
  float t = fract((angulo + giro) / (2.0 * PI));
  return mix(n1, n2, smoothstep(0.9, 1.0, t));
}

void main() {
  vec2 p = (gl_FragCoord.xy - uCentro) / uRaio;
  float r = length(p);
  float ang = atan(p.y, p.x);
  vec3 cor = vec3(0.0);

  // íris: fibras radiais em duas camadas que podem girar em sentidos opostos
  float dentro = smoothstep(1.0, 0.97, r) * smoothstep(uPupila - 0.01, uPupila + 0.02, r);
  float f1 = fibras(ang, r, uGiro1, 90.0, 0.0);
  float f2 = fibras(ang, r, uGiro2, 160.0, 7.0);
  float f = pow(f1 * 0.6 + f2 * 0.55, 1.3);
  float fio = pow(fibras(ang, r * 0.3, uGiro1 * 0.5, 240.0, 3.0), 6.0) * 1.4; // fios finos e brilhantes
  float m = smoothstep(uPupila, 0.95, r);
  vec3 tom = mix(uCorCentro, uCorMeio, smoothstep(0.0, 0.55, m));
  tom = mix(tom, uCorBorda, smoothstep(0.5, 1.0, m));
  float colarinho = smoothstep(0.06, 0.0, abs(r - (uPupila + 0.16 + 0.03 * ruido(vec2(ang * 6.0, uTempo * 0.2)))));
  float anelEscuro = smoothstep(0.82, 1.0, r);     // borda escura da íris (anel limbal)
  float base = 0.28 + 0.22 * ruido(vec2(ang * 3.0, r * 4.0));             // cor de fundo da íris
  float iris = (base + f * 1.1 + fio + colarinho * 0.7) * (1.0 - anelEscuro * 0.75);
  // ondas de luz saindo da pupila quando ela fala
  float onda = pow(0.5 + 0.5 * sin((r - uTempo * 0.9) * 26.0), 6.0) * uFala * smoothstep(1.0, uPupila, r);
  cor += tom * (iris + onda * 1.2) * dentro * uBrilho;

  // pupila: escura, com uma luz pequena no fundo
  float pupila = smoothstep(uPupila + 0.015, uPupila - 0.01, r);
  cor = mix(cor, vec3(0.0), pupila);
  cor += uCorMeio * exp(-r * r / 0.004) * (0.35 + uNivel * 0.8 + uFala * 0.6) * pupila;

  // borda nítida da íris, brilho em volta e anéis finos de interface
  cor += uCorBorda * smoothstep(0.02, 0.0, abs(r - 0.995)) * 0.5 * uBrilho;
  cor += uCorBorda * exp(-max(r - 1.0, 0.0) * 6.0) * 0.22 * step(1.0, r) * uBrilho;
  for (int i = 0; i < 3; i++) {
    float raio = 1.22 + float(i) * 0.14;
    float giroAnel = uTempo * (0.05 + float(i) * 0.03) * (i == 1 ? -1.0 : 1.0) * (1.0 + uVarredura * 4.0);
    float traco = step(0.35, fract((ang + giroAnel) / (2.0 * PI) * (24.0 + float(i) * 16.0)));
    cor += uCorMeio * smoothstep(0.004, 0.0, abs(r - raio)) * traco * (0.18 + uVarredura * 0.25);
  }
  // pensando: um arco que varre em volta
  float arco = fract((ang - uTempo * 2.2) / (2.0 * PI));
  cor += uCorBorda * smoothstep(0.012, 0.0, abs(r - 1.12)) * pow(arco, 3.0) * uVarredura * 1.6;

  // reflexos de luz no olho (dão volume)
  cor += vec3(1.0) * smoothstep(0.09, 0.0, length(p - vec2(-0.32, 0.36))) * 0.55;
  cor += vec3(1.0) * smoothstep(0.035, 0.0, length(p - vec2(0.24, -0.22))) * 0.35;

  cor = clamp(cor, 0.0, 1.0);
  gl_FragColor = vec4(cor, max(max(cor.r, cor.g), cor.b)); // cor já multiplicada pela transparência
}`;

export class Olho {
  constructor(canvas) {
    this.canvas = canvas;
    this.estado = "IDLE";
    this.nivelAlvo = 0;
    this.nivel = 0;
    this.atual = structuredClone(ESTADOS.IDLE);
    this.giro1 = 0;
    this.giro2 = 0;

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true, premultipliedAlpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.cena = new THREE.Scene();
    this.camera = new THREE.Camera();
    const cor = () => ({ value: new THREE.Color() });
    this.u = {
      uCentro: { value: new THREE.Vector2() }, uRaio: { value: 100 },
      uTempo: { value: 0 }, uPupila: { value: 0.33 }, uGiro1: { value: 0 }, uGiro2: { value: 0 },
      uBrilho: { value: 1 }, uNivel: { value: 0 }, uFala: { value: 0 }, uVarredura: { value: 0 },
      uCorCentro: cor(), uCorMeio: cor(), uCorBorda: cor(),
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
  definirEspectro() {} // a íris usa só o volume

  _redimensionar() {
    const { width, height } = this.canvas.getBoundingClientRect();
    if (!width || !height) return;
    this.renderer.setSize(width, height, false);
    const escala = this.renderer.getPixelRatio();
    // a íris fica um pouco acima do centro: a fala aparece embaixo, à esquerda
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
    for (const chave of ["pupila", "giro", "brilho", "varredura"]) a[chave] = suave(a[chave], alvo[chave], 3);
    for (const chave of ["centro", "meio", "borda"]) a[chave] = a[chave].map((c, i) => suave(c, alvo[chave][i], 3));

    const ouvindo = this.estado === "OUVINDO" ? this.nivel : 0;
    const falando = this.estado === "FALANDO" ? this.nivel : 0;
    const respirar = this.estado === "IDLE" ? Math.sin(t * 0.9) * 0.015 : 0;
    // a pupila dilata quando você fala e contrai um pouco nos picos da voz dela
    u.uPupila.value = suave(u.uPupila.value, a.pupila + respirar + ouvindo * 0.1 - falando * 0.04, 10);
    this.giro1 += dt * a.giro;
    this.giro2 -= dt * a.giro * 0.7;
    u.uGiro1.value = this.giro1;
    u.uGiro2.value = this.giro2;
    u.uTempo.value = t;
    u.uBrilho.value = a.brilho + ouvindo * 0.35 + falando * 0.2;
    u.uNivel.value = ouvindo;
    u.uFala.value = suave(u.uFala.value, falando, 12);
    u.uVarredura.value = a.varredura;
    u.uCorCentro.value.setRGB(...a.centro);
    u.uCorMeio.value.setRGB(...a.meio);
    u.uCorBorda.value.setRGB(...a.borda);

    this.renderer.render(this.cena, this.camera);
  }
}
