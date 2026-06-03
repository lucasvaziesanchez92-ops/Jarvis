'use client'

import { useRef, useMemo, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useGLTF, Float } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

export type BrainState = 'idle' | 'thinking' | 'speaking' | 'listening' | 'error'

/* ── Palette per state ──────────────────────────────────────────────── */
const PALETTE: Record<BrainState, THREE.ColorRepresentation> = {
  idle:      '#4488ff',
  thinking:  '#aa44ff',
  speaking:  '#00d4ff',
  listening: '#00ff88',
  error:     '#ff4444',
}
const PALETTE_B: Record<BrainState, THREE.ColorRepresentation> = {
  idle:      '#8833cc',
  thinking:  '#ff44aa',
  speaking:  '#44ffcc',
  listening: '#00cc66',
  error:     '#cc2222',
}

/* ── Holographic Fresnel + displacement vertex shader ───────────────── */
const HOLO_VS = /* glsl */`
  uniform float uTime;
  uniform float uWave;
  varying vec3  vNorm;
  varying vec3  vView;
  varying float vDisp;

  void main() {
    vec3 p = position;
    float d = sin(p.x * 5.0 + uTime * 1.3)
            * cos(p.y * 4.5 + uTime * 1.0)
            * sin(p.z * 5.2 + uTime * 1.1);
    p += normal * d * uWave;
    vDisp = d;

    vec4 world = modelMatrix * vec4(p, 1.0);
    vNorm = normalize(normalMatrix * normal);
    vView = normalize(cameraPosition - world.xyz);
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`

const HOLO_FS = /* glsl */`
  uniform float uTime;
  uniform vec3  uColA;
  uniform vec3  uColB;
  uniform float uOpacity;
  varying vec3  vNorm;
  varying vec3  vView;
  varying float vDisp;

  void main() {
    float fr = pow(1.0 - clamp(dot(vNorm, vView), 0.0, 1.0), 3.0);
    vec3 wp = (modelMatrix * vec4(position, 1.0)).xyz;
    float scan = pow(abs(sin(wp.y * 30.0 + uTime * 1.8)), 8.0) * 0.35;
    float vein = smoothstep(0.7, 1.0, abs(vDisp)) * 0.5;
    vec3 col = mix(uColA, uColB, abs(vNorm.y));
    float a   = fr * uOpacity + scan + vein;
    gl_FragColor = vec4(col + vein * uColA, clamp(a, 0.0, 1.0));
  }
`

/* ── Particle orbit shader ──────────────────────────────────────────── */
const PART_VS = /* glsl */`
  attribute float aSz;
  attribute float aPh;
  uniform float uTime;
  uniform float uDPR;
  uniform vec3  uColA;
  varying float vA;
  varying vec3  vC;

  void main() {
    vec3 p = position;
    float ang = atan(p.z, p.x) + uTime * 0.07 * sign(aPh - 3.14);
    float r   = length(p.xz);
    p.x = cos(ang) * r;
    p.z = sin(ang) * r;
    p.y += sin(uTime * 0.6 + aPh) * 0.07;

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_PointSize = aSz * uDPR * (160.0 / -mv.z);
    gl_Position  = projectionMatrix * mv;

    vA = (0.3 + sin(uTime * 1.6 + aPh * 2.5) * 0.4) * 0.9;
    vC = uColA;
  }
`

const PART_FS = /* glsl */`
  varying float vA;
  varying vec3  vC;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5) discard;
    float a = pow(1.0 - d * 2.0, 2.5) * vA;
    gl_FragColor = vec4(vC * 1.8, a);
  }
`

/* ── Orbital particles geometry ─────────────────────────────────────── */
function makeParticles(n = 500) {
  const pos = new Float32Array(n * 3)
  const sz  = new Float32Array(n)
  const ph  = new Float32Array(n)
  for (let i = 0; i < n; i++) {
    const t = Math.random() * Math.PI * 2
    const f = Math.acos(2 * Math.random() - 1)
    const r = 1.4 + Math.random() * 0.7
    pos[i*3]   = r * Math.sin(f) * Math.cos(t)
    pos[i*3+1] = r * Math.cos(f)
    pos[i*3+2] = r * Math.sin(f) * Math.sin(t)
    sz[i]  = 1.5 + Math.random() * 4.5
    ph[i]  = Math.random() * Math.PI * 2
  }
  return { pos, sz, ph }
}

/* ── Brain mesh component ───────────────────────────────────────────── */
function BrainModel({ state }: { state: BrainState }) {
  const matRef  = useRef<THREE.ShaderMaterial>(null)
  const wireRef = useRef<THREE.MeshBasicMaterial>(null)
  const { scene } = useGLTF('/models/brain.glb')

  const geo = useMemo(() => {
    let g: THREE.BufferGeometry | null = null
    scene.traverse((c) => { if ((c as THREE.Mesh).isMesh && !g) g = (c as THREE.Mesh).geometry.clone() })
    return g
  }, [scene])

  const uniforms = useMemo(() => ({
    uTime:    { value: 0 },
    uWave:    { value: 0.012 },
    uColA:    { value: new THREE.Color(PALETTE.idle) },
    uColB:    { value: new THREE.Color(PALETTE_B.idle) },
    uOpacity: { value: 0.55 },
  }), [])

  useFrame(({ clock }) => {
    if (!matRef.current || !wireRef.current) return
    const t = clock.getElapsedTime()
    matRef.current.uniforms.uTime.value = t
    const waveTarget = state === 'speaking' ? 0.022 : state === 'thinking' ? 0.018 : 0.012
    const waveCur = matRef.current.uniforms.uWave.value
    matRef.current.uniforms.uWave.value = waveCur + (waveTarget - waveCur) * 0.05

    const cA = matRef.current.uniforms.uColA.value
    const cB = matRef.current.uniforms.uColB.value
    cA.lerp(new THREE.Color(PALETTE[state]),  0.04)
    cB.lerp(new THREE.Color(PALETTE_B[state]), 0.04)
    wireRef.current.color.lerp(new THREE.Color(PALETTE[state]), 0.04)
  })

  if (!geo) return null

  return (
    <group>
      <mesh geometry={geo}>
        <shaderMaterial
          ref={matRef}
          vertexShader={HOLO_VS}
          fragmentShader={HOLO_FS}
          uniforms={uniforms}
          transparent
          side={THREE.DoubleSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      <mesh geometry={geo}>
        <meshBasicMaterial
          ref={wireRef}
          color={new THREE.Color(PALETTE.idle)}
          wireframe
          transparent
          opacity={0.045}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  )
}

/* ── Fallback icosahedron while GLB loads ───────────────────────────── */
function FallbackBrain() {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.4
  })
  return (
    <mesh ref={ref}>
      <icosahedronGeometry args={[0.85, 3]} />
      <meshBasicMaterial color="#4488ff" wireframe transparent opacity={0.25}
        blending={THREE.AdditiveBlending} depthWrite={false} />
    </mesh>
  )
}

/* ── Particles around brain ─────────────────────────────────────────── */
function Particles({ state }: { state: BrainState }) {
  const matRef = useRef<THREE.ShaderMaterial>(null)
  const { pos, sz, ph } = useMemo(() => makeParticles(500), [])
  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uDPR:  { value: typeof window !== 'undefined' ? Math.min(window.devicePixelRatio, 2) : 1 },
    uColA: { value: new THREE.Color(PALETTE.idle) },
  }), [])

  useFrame(({ clock }) => {
    if (!matRef.current) return
    matRef.current.uniforms.uTime.value = clock.getElapsedTime()
    matRef.current.uniforms.uColA.value.lerp(new THREE.Color(PALETTE[state]), 0.05)
  })

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" array={pos} count={500} itemSize={3}/>
        <bufferAttribute attach="attributes-aSz"      array={sz}  count={500} itemSize={1}/>
        <bufferAttribute attach="attributes-aPh"      array={ph}  count={500} itemSize={1}/>
      </bufferGeometry>
      <shaderMaterial ref={matRef}
        vertexShader={PART_VS} fragmentShader={PART_FS} uniforms={uniforms}
        transparent depthWrite={false} blending={THREE.AdditiveBlending}/>
    </points>
  )
}

/* ── Inner glow sphere ──────────────────────────────────────────────── */
function CoreGlow({ state }: { state: BrainState }) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.scale.setScalar(1 + Math.sin(clock.getElapsedTime() * 0.5) * 0.03)
    ;(ref.current.material as THREE.MeshBasicMaterial).color.lerp(
      new THREE.Color(PALETTE[state]), 0.03
    )
  })
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.78, 24, 24]}/>
      <meshBasicMaterial color={PALETTE.idle} transparent opacity={0.04}
        depthWrite={false} blending={THREE.AdditiveBlending}/>
    </mesh>
  )
}

/* ── Scene root ─────────────────────────────────────────────────────── */
function Scene({ state }: { state: BrainState }) {
  const groupRef = useRef<THREE.Group>(null)
  useFrame(() => { if (groupRef.current) groupRef.current.rotation.y += 0.0007 })

  return (
    <group ref={groupRef} scale={0.65}>
      <CoreGlow state={state}/>
      <Float speed={0.9} rotationIntensity={0.06} floatIntensity={0.04}>
        <Suspense fallback={<FallbackBrain/>}>
          <BrainModel state={state}/>
        </Suspense>
      </Float>
      <Particles state={state}/>
    </group>
  )
}

/* ── Export ──────────────────────────────────────────────────────────── */
export default function NeuralBrainScene({ state = 'idle' }: { state?: BrainState }) {
  const dpr = typeof window !== 'undefined' ? Math.min(window.devicePixelRatio, 2) : 1
  return (
    <Canvas
      camera={{ position: [0, 0.1, 3.0], fov: 38, near: 0.01, far: 50 }}
      dpr={dpr}
      gl={{ antialias: true, alpha: true, premultipliedAlpha: false }}
      onCreated={({ gl }) => {
        gl.setClearColor(new THREE.Color(0, 0, 0), 0)
        gl.toneMapping = THREE.ACESFilmicToneMapping
        gl.toneMappingExposure = 1.1
      }}
      style={{ background: 'transparent', width: '100%', height: '100%' }}
    >
      <Scene state={state}/>
      <EffectComposer>
        <Bloom intensity={1.8} luminanceThreshold={0.28} luminanceSmoothing={0.7} radius={0.4} mipmapBlur/>
      </EffectComposer>
    </Canvas>
  )
}

useGLTF.preload('/models/brain.glb')
