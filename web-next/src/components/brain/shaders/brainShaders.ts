/* ───────────────────────────────────────────────────────────────
   ORGANIC BRAIN — GLSL Shaders
   
   Estos shaders crean un cerebro translúcido, orgánico y luminoso
   que simula biología digital con técnicas de:
   - Fresnel rim lighting con gradiente cian→magenta
   - Fake subsurface scattering (curvature-based)
   - Volumetric glow
   - Organic scanlines

   Compatible con MeshPhysicalMaterial de Three.js + onBeforeCompile
   ─────────────────────────────────────────────────────────────── */

// ── Vertex Shader ──────────────────────────────────────────────
export const BRAIN_VERTEX_SHADER = /* glsl */ `
#define ORGANIC_BRAIN

#include <common>

// Varyings (pasamos datos del vertex al fragment shader)
varying vec3 vWorldPos;
varying vec3 vNormalWorld;
varying float vCurvature;
varying float vGradientY;
varying vec3 vViewDir;
varying float vDepth;

void main() {
  #include <beginnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
  #include <project_vertex>

  // Posición en world space (para calcular distancias y gradientes)
  vec4 worldPosition = modelMatrix * vec4(transformed, 1.0);
  vWorldPos = worldPosition.xyz;

  // Normal en world space
  vNormalWorld = normalize((modelMatrix * vec4(normal, 0.0)).xyz);

  // Vector hacia la cámara
  vViewDir = normalize(cameraPosition - vWorldPos);

  // Curvatura: calculamos cuán cónica/esférica es la superficie
  // positivo = convexo (bordes externos del cerebro)
  // negativo = cóncavo (surcos internos)
  vec3 toCenter = normalize(-vWorldPos);
  vCurvature = dot(vNormalWorld, toCenter);

  // Gradient Y: usamos la posición Y para el gradiente de color
  // Mapeamos a 0-1 basado en la bounding box aproximada del cerebro
  vGradientY = smoothstep(-1.2, 1.2, vWorldPos.y);

  // Profundidad relativa (para depth-based effects)
  vDepth = gl_Position.z;
}
`;

// ── Fragment Shader ─────────────────────────────────────────────
export const BRAIN_FRAGMENT_SHADER = /* glsl */ `
#define ORGANIC_BRAIN

#include <common>

// Varyings del vertex shader
varying vec3 vWorldPos;
varying vec3 vNormalWorld;
varying float vCurvature;
varying float vGradientY;
varying vec3 vViewDir;
varying float vDepth;

// Uniforms inyectados desde JavaScript
uniform vec3 uRimColor;
uniform vec3 uGrooveColor;
uniform vec3 uCoreColor;
uniform vec3 uTransmissionColor;
uniform float uRimIntensity;
uniform float uGrooveIntensity;
uniform float uTransmissionIntensity;
uniform float uTime;
uniform float uOrganicPulse;

// Función de ruido simple para textura orgánica
float hash(vec3 p) {
  p = fract(p * vec3(443.897, 441.423, 437.195));
  p += dot(p, p.yzx + 19.19);
  return fract((p.x + p.y) * p.z);
}

float noise3D(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);

  float n = mix(
    mix(
      mix(hash(i), hash(i + vec3(1.0, 0.0, 0.0)), f.x),
      mix(hash(i + vec3(0.0, 1.0, 0.0)), hash(i + vec3(1.0, 1.0, 0.0)), f.x),
      f.y
    ),
    mix(
      mix(hash(i + vec3(0.0, 0.0, 1.0)), hash(i + vec3(1.0, 0.0, 1.0)), f.x),
      mix(hash(i + vec3(0.0, 1.0, 1.0)), hash(i + vec3(1.0, 1.0, 1.0)), f.x),
      f.y
    ),
    f.z
  );
  return n;
}

// Fresnel: brillo en los bordes
float fresnel(float power) {
  float ndotv = clamp(dot(vNormalWorld, vViewDir), 0.0, 1.0);
  return pow(1.0 - ndotv, power);
}

// Fake subsurface scattering: luz que atraviesa desde atrás
float fakeSSS() {
  // Cuando la luz viene por detrás de la superficie (back-scattering)
  float backScatter = clamp(-dot(vNormalWorld, vViewDir), 0.0, 1.0);
  // Suavizamos
  return smoothstep(0.0, 0.6, backScatter);
}

void main() {
  // ── Cálculo del gradiente orgánico ─────────────────────────
  // Cian (abajo) → Azul/Blanco (medio) → Magenta/Rosa (arriba)
  vec3 bottomColor = vec3(0.0, 0.78, 1.0);    // #00c7ff - cian brillante
  vec3 midColor    = vec3(0.53, 0.27, 1.0);    // #8844ff - violeta
  vec3 topColor    = vec3(1.0, 0.0, 0.4);      // #ff0066 - magenta profundo
  
  // Gradient base con suavizado
  vec3 gradientColor;
  if (vGradientY < 0.5) {
    gradientColor = mix(bottomColor, midColor, smoothstep(0.0, 0.5, vGradientY));
  } else {
    gradientColor = mix(midColor, topColor, smoothstep(0.5, 1.0, vGradientY));
  }

  // ── Textura orgánica (ruido sutil) ────────────────────────
  float organicNoise = noise3D(vWorldPos * 4.0 + uTime * 0.1) * 0.12;
  float organicNoise2 = noise3D(vWorldPos * 12.0 + uTime * 0.05) * 0.06;
  float combinedNoise = organicNoise + organicNoise2;

  // ── Fresnel rim light ─────────────────────────────────────
  float rim = fresnel(2.5);
  // Acentuamos el rim en los bordes superiores
  float rimTop = rim * (0.5 + vGradientY * 0.5);

  // ── Fake Subsurface Scattering (SSS) ────────────────────────
  float sss = fakeSSS();
  // Los surcos (cóncavos) acumulan más luz SSS
  float grooveDepth = smoothstep(0.15, -0.50, vCurvature);
  float sssGroove = sss * grooveDepth * 1.5;

  // ── Volumetric glow desde el núcleo ───────────────────────
  // Simula luz que viene desde adentro del cerebro hacia afuera
  float coreGlow = exp(-length(vWorldPos) * 1.8) * uOrganicPulse;

  // ── Organic pulse (latido neuronal) ────────────────────────
  float pulse = sin(uTime * 1.2) * 0.5 + 0.5;
  float pulseFast = sin(uTime * 3.0 + vWorldPos.y * 2.0) * 0.5 + 0.5;

  // ── Scanlines orgánicas (muy sutiles) ──────────────────────
  float scan = pow(abs(sin(vWorldPos.y * 25.0 + uTime * 0.8)), 24.0) * 0.03 * pulse;
  float scan2 = pow(abs(cos(vWorldPos.x * 20.0 + uTime * 0.5)), 32.0) * 0.02;

  // ── Combinación de emissive ───────────────────────────────
  vec3 emissive = vec3(0.0);
  
  // Rim light con color de gradiente
  emissive += gradientColor * rimTop * uRimIntensity * 0.6;
  
  // Groove color (magenta en surcos)
  emissive += uGrooveColor * grooveDepth * uGrooveIntensity;
  
  // SSS fake (luz que atraviesa por los bordes)
  emissive += uTransmissionColor * sssGroove * uTransmissionIntensity * 0.4;
  
  // Core glow (brillo interno)
  emissive += uCoreColor * coreGlow * 2.0;
  
  // Ruido orgánico aditivo
  emissive += gradientColor * combinedNoise * rim * 0.3;
  
  // Scanlines
  emissive += gradientColor * (scan + scan2);
  
  // Pulse ambiental
  emissive += uRimColor * pulseFast * 0.05 * grooveDepth;

  // ── Color base con variación orgánica ──────────────────────
  vec3 baseColor = gradientColor * (0.85 + combinedNoise);
  
  // Mezcla suave del color base con el emissive
  vec3 finalColor = baseColor + emissive;

  // ── Atenuación por profundidad (depth-based glow) ─────────
  float depthGlow = smoothstep(0.0, 0.3, vDepth) * 0.15;
  finalColor += uTransmissionColor * depthGlow;

  // ── Output ────────────────────────────────────────────────
  // El MeshPhysicalMaterial maneja difuso, specular, etc.
  // Nosotros solo modificamos la componente emissive
  totalEmissiveRadiance += finalColor;
  
  // Opcional: modificar difuso para que el color base también tenga gradiente
  diffuseColor.rgb = mix(diffuseColor.rgb, gradientColor, 0.15);
}
`;

// ── Particle Vertex Shader ─────────────────────────────────────
export const PARTICLE_VERTEX_SHADER = /* glsl */ `
attribute float aSize;
attribute float aPhase;
attribute float aSpeed;

uniform float uTime;
uniform float uDPR;
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform float uParticleIntensity;

varying float vAlpha;
varying vec3 vColor;
varying float vGlow;

// Simplex noise helper (simplificado para partículas)
float hash11(float p) {
  return fract(sin(p * 127.1) * 43758.5453);
}

float hash21(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
  vec3 p = position;
  
  // Movimiento browniano simulado con ruido
  float t = uTime * aSpeed;
  
  // Órbita suave + desplazamiento aleatorio
  float angleXZ = atan(p.z, p.x) + t * 0.05 * (hash11(aPhase) - 0.5);
  float radius = length(p.xz) + sin(t * 0.3 + aPhase) * 0.1;
  
  p.x = cos(angleXZ) * radius;
  p.z = sin(angleXZ) * radius;
  p.y += sin(t * 0.7 + aPhase * 2.0) * 0.08 + cos(t * 0.4 + aPhase) * 0.05;
  
  // Movimiento errático adicional (Browniano)
  p.x += sin(t * 1.1 + aPhase * 3.7) * 0.03;
  p.y += cos(t * 0.9 + aPhase * 5.3) * 0.02;
  p.z += sin(t * 1.3 + aPhase * 2.1) * 0.03;
  
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  
  // Size con atenuación por distancia y DPR
  float dist = -mv.z;
  gl_PointSize = aSize * uDPR * (180.0 / max(dist, 0.1)) * uParticleIntensity;
  
  // Alpha con variación
  vAlpha = (0.4 + sin(uTime * 1.5 + aPhase * 3.0) * 0.3) * 
           (0.6 + sin(uTime * 0.4 + aPhase) * 0.4);
  
  // Color mix basado en phase
  float colorMix = hash11(aPhase);
  vColor = mix(uColorA, uColorB, colorMix);
  
  // Glow factor
  vGlow = smoothstep(3.0, 0.5, dist) * 0.8 + 0.2;
}
`;

// ── Particle Fragment Shader ───────────────────────────────────
export const PARTICLE_FRAGMENT_SHADER = /* glsl */ `
varying float vAlpha;
varying vec3 vColor;
varying float vGlow;

uniform float uTime;

void main() {
  // Círculo suave con gradiente radial
  vec2 center = gl_PointCoord - 0.5;
  float dist = length(center);
  
  if (dist > 0.5) discard;
  
  // Forma orgánica: no perfectamente circular
  float organicShape = smoothstep(0.5, 0.0, dist);
  organicShape = pow(organicShape, 1.5);
  
  // Soft glow halo
  float halo = exp(-dist * dist * 8.0) * 0.3;
  
  float alpha = (organicShape + halo) * vAlpha * vGlow;
  
  // Color más brillante en el centro
  vec3 finalColor = vColor * (1.0 + organicShape * 0.5) * 2.0;
  
  gl_FragColor = vec4(finalColor, alpha);
}
`;

// ── Volumetric Halo Shader (para el glow exterior) ────────────
export const HALO_VERTEX_SHADER = /* glsl */ `
varying vec3 vNormal;
varying vec3 vView;
varying float vDepth;

void main() {
  vec4 worldPos = modelMatrix * vec4(position, 1.0);
  vNormal = normalize((modelViewMatrix * vec4(normal, 0.0)).xyz);
  vView = normalize(-(modelViewMatrix * vec4(position, 1.0)).xyz);
  vDepth = gl_Position.z;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const HALO_FRAGMENT_SHADER = /* glsl */ `
uniform vec3 uHaloColor;
uniform float uHaloIntensity;
uniform float uTime;

varying vec3 vNormal;
varying vec3 vView;
varying float vDepth;

void main() {
  float fresnel = pow(1.0 - clamp(dot(vNormal, vView), 0.0, 1.0), 3.0);
  float pulse = sin(uTime * 0.5) * 0.3 + 0.7;
  
  float alpha = fresnel * uHaloIntensity * pulse;
  alpha *= smoothstep(0.0, 0.2, vDepth);
  
  gl_FragColor = vec4(uHaloColor, alpha);
}
`;
