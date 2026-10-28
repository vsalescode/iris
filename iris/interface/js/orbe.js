// A "presença" da Iris: um orbe 3D de partículas de luz (WebGL com Three.js).
// Mesmo jeito de usar do núcleo antigo: definirEstado / definirNivel / definirEspectro.
//
// Estados:
//   IDLE      respira devagar, partículas flutuando
//   OUVINDO   se acende e cresce um pouco, a superfície reage à sua voz
//   PENSANDO  gira em espiral, mais agitado, tom azulado
//   FALANDO   a superfície ondula com a voz dela

import * as THREE from "three";

// Ruído simplex 3D (Ashima Arts / Stefan Gustavson, licença MIT) – deixa o movimento orgânico
const RUIDO = /* glsl */ `
vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1.0/6.0,1.0/3.0); const vec4 D=vec4(0.0,0.5,1.0,2.0);
  vec3 i=floor(v+dot(v,C.yyy)); vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz); vec3 l=1.0-g; vec3 i1=min(g.xyz,l.zxy); vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx; vec3 x2=x0-i2+C.yyy; vec3 x3=x0-D.yyy;
  i=mod289(i);
  vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
  float n_=0.142857142857; vec3 ns=n_*D.wyz-D.xzx;
  vec4 j=p-49.0*floor(p*ns.z*ns.z); vec4 x_=floor(j*ns.z); vec4 y_=floor(j-7.0*x_);
  vec4 x=x_*ns.x+ns.yyyy; vec4 y=y_*ns.x+ns.yyyy; vec4 h=1.0-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy); vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.0+1.0; vec4 s1=floor(b1)*2.0+1.0; vec4 sh=-step(h,vec4(0.0));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy; vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x); vec3 p1=vec3(a0.zw,h.y); vec3 p2=vec3(a1.xy,h.z); vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x; p1*=norm.y; p2*=norm.z; p3*=norm.w;
  vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0); m=m*m;
  return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}`;

const VERTICE_PARTICULAS = /* glsl */ `
uniform float uTempo, uNivel, uAgitacao, uEspiral, uTamanho, uPixelRatio;
attribute float aAleatorio;
varying float vBrilho;
${RUIDO}
void main(){
  vec3 p = position;
  // espiral: gira cada "andar" do orbe numa velocidade diferente (PENSANDO)
  float ang = uEspiral * (p.y * 1.6 + uTempo * 1.4);
  float c = cos(ang), s = sin(ang);
  p.xz = mat2(c, -s, s, c) * p.xz;
  // superfície viva: ruído lento + ondas rápidas que seguem o som
  float lento = snoise(p * 1.4 + vec3(uTempo * 0.25));
  float rapido = snoise(p * 3.2 + vec3(uTempo * 1.8));
  float desloc = lento * (0.06 + uAgitacao * 0.22) + rapido * uNivel * 0.32;
  p *= 1.0 + desloc;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = uTamanho * (0.6 + aAleatorio * 0.9) * uPixelRatio * (1.0 + uNivel * 0.6) / -mv.z;
  // partículas na borda (de lado para a câmera) brilham mais: dá volume de esfera
  vec3 normal = normalize(normalMatrix * normalize(p));
  float borda = 1.0 - abs(normal.z);
  vBrilho = (0.35 + borda * 0.9 + max(desloc, 0.0) * 2.5) * (0.55 + aAleatorio * 0.45);
}`;

const FRAGMENTO_PARTICULAS = /* glsl */ `
uniform vec3 uCor, uCorBorda;
uniform float uIntensidade;
varying float vBrilho;
void main(){
  float d = length(gl_PointCoord - 0.5);
  float a = smoothstep(0.5, 0.0, d);
  vec3 cor = mix(uCor, uCorBorda, clamp(vBrilho - 0.6, 0.0, 1.0));
  gl_FragColor = vec4(cor, a * vBrilho * uIntensidade);
}`;

// Brilho (núcleo e aura): um quadrado sempre virado para a câmera com degradê radial
const VERTICE_BRILHO = /* glsl */ `
varying vec2 vUv;
void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const FRAGMENTO_BRILHO = /* glsl */ `
uniform vec3 uCor; uniform float uForca, uDureza;
varying vec2 vUv;
void main(){
  float d = length(vUv - 0.5) * 2.0;
  float a = pow(max(1.0 - d, 0.0), uDureza);
  gl_FragColor = vec4(uCor, a * uForca);
}`;

const ESTADOS = {
  //           agitação  espiral  intensidade  escala  cor (núcleo)       cor (borda)
  IDLE:     { agitacao: 0.15, espiral: 0.0, intensidade: 0.75, escala: 1.0, cor: [0.25, 0.85, 1.0], borda: [0.75, 0.97, 1.0] },
  OUVINDO:  { agitacao: 0.35, espiral: 0.0, intensidade: 1.05, escala: 1.07, cor: [0.4, 0.92, 1.0], borda: [0.9, 1.0, 1.0] },
  PENSANDO: { agitacao: 0.55, espiral: 0.9, intensidade: 0.95, escala: 0.97, cor: [0.35, 0.5, 1.0], borda: [0.75, 0.7, 1.0] },
  FALANDO:  { agitacao: 0.3, espiral: 0.0, intensidade: 1.1, escala: 1.03, cor: [0.25, 0.85, 1.0], borda: [0.85, 1.0, 1.0] },
};

export class Orbe {
  constructor(canvas) {
    this.canvas = canvas;
    this.estado = "IDLE";
    this.nivelAlvo = 0;
    this.nivel = 0;
    this.atual = structuredClone(ESTADOS.IDLE);

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.cena = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    // câmera um pouco abaixo do centro: o orbe aparece mais alto e deixa espaço para a fala embaixo
    this.camera.position.set(0, -0.55, 7.2);
    this.grupo = new THREE.Group();
    this.cena.add(this.grupo);

    this._criarParticulas();
    this._criarBrilhos();
    this._criarAneis();
    this._criarPoeira();

    new ResizeObserver(() => this._redimensionar()).observe(canvas);
    this._redimensionar();
    this.relogio = new THREE.Clock();
    this.renderer.setAnimationLoop(() => this._quadro());
  }

  definirEstado(estado) { this.estado = ESTADOS[estado] ? estado : "IDLE"; }
  definirNivel(v) { this.nivelAlvo = Math.max(0, Math.min(1, v)); }
  definirEspectro() {} // o orbe usa só o volume

  _criarParticulas() {
    // pontos distribuídos por igual na esfera (espiral de Fibonacci)
    const total = 9000;
    const pos = new Float32Array(total * 3);
    const aleatorio = new Float32Array(total);
    const ouro = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < total; i++) {
      const y = 1 - (i / (total - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const t = ouro * i;
      const raio = 1.12 * (0.97 + Math.random() * 0.06);
      pos.set([Math.cos(t) * r * raio, y * raio, Math.sin(t) * r * raio], i * 3);
      aleatorio[i] = Math.random();
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("aAleatorio", new THREE.BufferAttribute(aleatorio, 1));
    this.uParticulas = {
      uTempo: { value: 0 }, uNivel: { value: 0 }, uAgitacao: { value: 0.15 }, uEspiral: { value: 0 },
      uTamanho: { value: 26 }, uPixelRatio: { value: this.renderer.getPixelRatio() },
      uCor: { value: new THREE.Color() }, uCorBorda: { value: new THREE.Color() }, uIntensidade: { value: 0.8 },
    };
    this.particulas = new THREE.Points(geo, new THREE.ShaderMaterial({
      uniforms: this.uParticulas, vertexShader: VERTICE_PARTICULAS, fragmentShader: FRAGMENTO_PARTICULAS,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    this.grupo.add(this.particulas);
  }

  _brilho(tamanho, dureza) {
    const material = new THREE.ShaderMaterial({
      uniforms: { uCor: { value: new THREE.Color() }, uForca: { value: 0.3 }, uDureza: { value: dureza } },
      vertexShader: VERTICE_BRILHO, fragmentShader: FRAGMENTO_BRILHO,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    const malha = new THREE.Mesh(new THREE.PlaneGeometry(tamanho, tamanho), material);
    this.cena.add(malha); // fora do grupo: não gira, fica sempre de frente
    return malha;
  }

  _criarBrilhos() {
    this.miolo = this._brilho(2.2, 2.2);   // luz no centro
    this.aura = this._brilho(7.5, 3.0);    // halo grande e fraco em volta
  }

  _criarAneis() {
    // anéis finos em órbita, inclinados: aparecem mais quando ela pensa
    this.aneis = [];
    for (const [raio, inclinacao, vel] of [[1.55, 1.15, 0.12], [1.72, -0.75, -0.08], [1.92, 0.35, 0.05]]) {
      const pontos = [];
      for (let i = 0; i <= 256; i++) {
        const a = (i / 256) * Math.PI * 2;
        // anel tracejado: alguns trechos somem
        if (Math.sin(a * 7) > -0.3) pontos.push(new THREE.Vector3(Math.cos(a) * raio, 0, Math.sin(a) * raio));
      }
      const linha = new THREE.Points(
        new THREE.BufferGeometry().setFromPoints(pontos),
        new THREE.PointsMaterial({ size: 0.018, color: 0x6fe8ff, transparent: true, opacity: 0.25,
          blending: THREE.AdditiveBlending, depthWrite: false }),
      );
      linha.rotation.x = inclinacao;
      linha.userData.vel = vel;
      this.grupo.add(linha);
      this.aneis.push(linha);
    }
  }

  _criarPoeira() {
    // poeira de luz flutuando ao redor, bem fraca
    const total = 500;
    const pos = new Float32Array(total * 3);
    for (let i = 0; i < total; i++) {
      const r = 2.2 + Math.random() * 3.5;
      const t = Math.random() * Math.PI * 2;
      const f = Math.acos(2 * Math.random() - 1);
      pos.set([r * Math.sin(f) * Math.cos(t), r * Math.cos(f) * 0.7, r * Math.sin(f) * Math.sin(t)], i * 3);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    this.poeira = new THREE.Points(geo, new THREE.PointsMaterial({
      size: 0.02, color: 0x8feaff, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    this.cena.add(this.poeira);
  }

  _redimensionar() {
    const { width, height } = this.canvas.getBoundingClientRect();
    if (!width || !height) return;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    // em telas estreitas, afasta a câmera para o orbe caber
    this.camera.position.z = width / height < 1 ? 7.2 / (width / height) * 0.8 : 7.2;
    this.camera.updateProjectionMatrix();
  }

  _quadro() {
    const dt = Math.min(this.relogio.getDelta(), 0.05);
    const t = this.relogio.elapsedTime;
    const alvo = ESTADOS[this.estado];
    const suave = (atual, destino, vel) => atual + (destino - atual) * Math.min(1, dt * vel);

    this.nivel = suave(this.nivel, this.nivelAlvo, 14);
    const a = this.atual;
    a.agitacao = suave(a.agitacao, alvo.agitacao, 3);
    a.espiral = suave(a.espiral, alvo.espiral, 2);
    a.intensidade = suave(a.intensidade, alvo.intensidade, 3);
    a.escala = suave(a.escala, alvo.escala, 4);
    a.cor = a.cor.map((c, i) => suave(c, alvo.cor[i], 3));
    a.borda = a.borda.map((c, i) => suave(c, alvo.borda[i], 3));

    const respirar = this.estado === "IDLE" ? Math.sin(t * 1.1) * 0.025 : 0;
    const escala = a.escala + respirar + this.nivel * 0.06;

    const u = this.uParticulas;
    u.uTempo.value = t;
    u.uNivel.value = this.nivel;
    u.uAgitacao.value = a.agitacao;
    u.uEspiral.value = a.espiral;
    u.uIntensidade.value = a.intensidade;
    u.uCor.value.setRGB(...a.cor);
    u.uCorBorda.value.setRGB(...a.borda);

    this.grupo.scale.setScalar(escala);
    this.grupo.rotation.y += dt * (0.06 + a.espiral * 0.5);
    this.grupo.rotation.x = Math.sin(t * 0.13) * 0.12;

    this.miolo.material.uniforms.uCor.value.setRGB(...a.cor);
    this.miolo.material.uniforms.uForca.value = (0.35 + this.nivel * 0.6 + respirar * 4) * a.intensidade;
    this.miolo.scale.setScalar(escala * (1 + this.nivel * 0.25));
    this.aura.material.uniforms.uCor.value.setRGB(...a.cor);
    this.aura.material.uniforms.uForca.value = (0.1 + this.nivel * 0.12) * a.intensidade;

    for (const anel of this.aneis) {
      anel.rotation.y += dt * anel.userData.vel * (1 + a.espiral * 6);
      anel.material.opacity = 0.12 + a.espiral * 0.35 + this.nivel * 0.1;
    }
    this.poeira.rotation.y += dt * 0.01;

    this.renderer.render(this.cena, this.camera);
  }
}
