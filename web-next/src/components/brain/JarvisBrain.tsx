'use client'

import { useRef, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useGLTF, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

/* ────────────────────────────────────────────────────────────
   JARVIS BRAIN — Visible guaranteed
   
   Carga brain.glb (1.6MB, NO Draco = no falla).
   MeshStandardMaterial + emissive alto = SIEMPRE visible.
   Bloom sutil en bordes. Rotación automática.
   ──────────────────────────────────────────────────────────── */

export type BrainState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error' | 'sleep'

const STATE_COLORS: Record<BrainState, {
  emissive: THREE.Color
  emissiveIntensity: number
  base: THREE.Color
}> = {
  idle:      { emissive: new THREE.Color('#1a3355'), emissiveIntensity: 2.5, base: new THREE.Color('#d0e0f0') },
  listening: { emissive: new THREE.Color('#115544'), emissiveIntensity: 3.0, base: new THREE.Color('#c8f0e0') },
  thinking:  { emissive: new THREE.Color('#442244'), emissiveIntensity: 3.5, base: new THREE.Color('#f0d0e0') },
  speaking:  { emissive: new THREE.Color('#224444'), emissiveIntensity: 2.8, base: new THREE.Color('#d8f0e8') },
  error:     { emissive: new THREE.Color('#552222'), emissiveIntensity: 3.5, base: new THREE.Color('#f0c8c8') },
  sleep:     { emissive: new THREE.Color('#0f1520'), emissiveIntensity: 1.2, base: new THREE.Color('#8899aa') },
}

function BrainMesh({ state }: { state: BrainState }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const matRef = useRef<THREE.MeshStandardMaterial>(null)
  const groupRef = useRef<THREE.Group>(null)

  // Load brain — NO Draco, guaranteed to work
  const { scene } = useGLTF('/models/brain.glb', false)

  // Extract geometry
  const geo = (() => {
    let g: THREE.BufferGeometry | null = null
    scene.traverse((c) => {
      if ((c as THREE.Mesh).isMesh && !g) g = (c as THREE.Mesh).geometry
    })
    return g
  })()

  useFrame(() => {
    if (matRef.current) {
      const c = STATE_COLORS[state]
      matRef.current.emissive.lerp(c.emissive, 0.05)
      matRef.current.emissiveIntensity += (c.emissiveIntensity - matRef.current.emissiveIntensity) * 0.05
      matRef.current.color.lerp(c.base, 0.05)
    }
    if (groupRef.current) groupRef.current.rotation.y += 0.002
  })

  if (!geo) return null

  return (
    <group ref={groupRef}>
      <mesh ref={meshRef} geometry={geo} scale={0.65}>
        <meshStandardMaterial
          ref={matRef}
          color={STATE_COLORS.idle.base}
          emissive={STATE_COLORS.idle.emissive}
          emissiveIntensity={STATE_COLORS.idle.emissiveIntensity}
          metalness={0.1}
          roughness={0.35}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  )
}

function Scene({ state }: { state: BrainState }) {
  return (
    <>
      <BrainMesh state={state} />
      {/* Esfera de glow interior */}
      <mesh>
        <sphereGeometry args={[0.65, 32, 32]} />
        <meshBasicMaterial
          color={new THREE.Color('#224488')}
          transparent opacity={0.05}
          side={THREE.BackSide}
          depthWrite={false}
        />
      </mesh>
    </>
  )
}

function Fallback() {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.15
  })
  return (
    <mesh ref={ref}>
      <icosahedronGeometry args={[0.7, 4]} />
      <meshBasicMaterial color="#4488ee" wireframe transparent opacity={0.3} />
    </mesh>
  )
}

export default function JarvisBrain({ state = 'idle' }: { state?: BrainState }) {
  const isMobile =
    typeof navigator !== 'undefined' &&
    /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)

  return (
    <div className="w-full h-full" style={{ background: '#000000' }}>
      <Canvas
        camera={{ position: [0, 0, 4.5], fov: 40, near: 0.1, far: 50 }}
        dpr={isMobile ? Math.min(window.devicePixelRatio, 1.5) : Math.min(window.devicePixelRatio, 2)}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.2,
        }}
        onCreated={({ gl }) => gl.setClearColor(new THREE.Color('#000000'))}
      >
        <color attach="background" args={['#000000']} />

        {/* Environment para reflejos en StandardMaterial */}
        <Environment preset="night" environmentIntensity={0.3} />

        {/* Luces para resaltar geometría */}
        <ambientLight intensity={0.15} />
        <directionalLight position={[3, 5, 3]} intensity={0.6} color="#ddeeff" />
        <directionalLight position={[-2, 1, -2]} intensity={0.3} color="#ffddff" />
        <pointLight position={[2, 3, 3]} intensity={0.5} color="#00d4ff" distance={8} />

        <Suspense fallback={<Fallback />}>
          <Scene state={state} />
        </Suspense>

        <EffectComposer>
          <Bloom luminanceThreshold={0.7} luminanceSmoothing={0.4} intensity={0.5} mipmapBlur />
        </EffectComposer>
      </Canvas>
    </div>
  )
}

useGLTF.preload('/models/brain.glb', false)
