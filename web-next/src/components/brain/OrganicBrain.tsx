'use client'

import { useRef, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

import OrganicBrainMesh, { type BrainState } from './OrganicBrainMesh'
import BackfaceGlow from './BackfaceGlow'
import EnhancedParticles from './EnhancedParticles'
import VolumetricHalo from './VolumetricHalo'

interface OrganicBrainProps {
  state?: BrainState
}

/* ── Fallback mientras carga ─────────────────────────────────── */
function FallbackBrain() {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.15
  })
  return (
    <mesh ref={ref}>
      <icosahedronGeometry args={[0.7, 4]} />
      <meshBasicMaterial color="#4488ee" wireframe transparent opacity={0.2} 
        blending={THREE.AdditiveBlending} depthWrite={false} />
    </mesh>
  )
}

/* ── Núcleo interno (glow sphere sutil) ──────────────────────── */
function CoreGlow({ state }: { state: BrainState }) {
  const ref = useRef<THREE.Mesh>(null)

  const colors: Record<BrainState, THREE.ColorRepresentation> = {
    idle: '#2244aa',
    listening: '#0088cc',
    thinking: '#cc1166',
    speaking: '#00aa88',
    error: '#cc1111',
    sleep: '#223366',
  }

  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime()
    ref.current.scale.setScalar(1 + Math.sin(t * 0.7) * 0.02)
    ;(ref.current.material as THREE.MeshBasicMaterial).color.lerp(
      new THREE.Color(colors[state]), 0.03
    )
  })

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.75, 24, 24]} />
      <meshBasicMaterial
        color={colors.idle}
        transparent
        opacity={0.06}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  )
}

/* ── Scene raíz ────────────────────────────────────────────── */
function Scene({ state }: { state: BrainState }) {
  const groupRef = useRef<THREE.Group>(null)

  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.0003
      // Rotación X muy sutil para ver el cerebro en 3/4
      groupRef.current.rotation.x = Math.sin(Date.now() * 0.0001) * 0.05
    }
  })

  return (
    <group ref={groupRef} scale={0.68}>
      <CoreGlow state={state} />

      <group>
        {/* Backface para fake SSS */}
        <Suspense fallback={null}>
          <BackfaceGlow state={state} />
        </Suspense>

        {/* Cerebro principal translúcido */}
        <Suspense fallback={<FallbackBrain />}>
          <OrganicBrainMesh state={state} />
        </Suspense>
      </group>

      {/* Partículas orgánicas */}
      <EnhancedParticles state={state} count={1500} />

      {/* Halo volumétrico */}
      <VolumetricHalo state={state} />

      {/* Esfera de ambiente exterior para environment */}
      <pointLight position={[2, 3, 2]} intensity={0.8} color="#e0f0ff" distance={10} />
      <pointLight position={[-2, -1, -2]} intensity={0.4} color="#ffccff" distance={10} />
    </group>
  )
}

/* ── Export principal ──────────────────────────────────────── */
export default function OrganicBrain({ state = 'idle' }: OrganicBrainProps) {
  const isMobile =
    typeof navigator !== 'undefined' &&
    /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)

  return (
    <div className="relative w-full h-full" style={{ background: '#000000' }}>
      <Canvas
        camera={{ position: [0, 0.3, 5.0], fov: 38, near: 0.01, far: 50 }}
        dpr={isMobile ? Math.min(window.devicePixelRatio, 1.5) : Math.min(window.devicePixelRatio, 2)}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.3,
        }}
        onCreated={({ gl }) => {
          gl.setClearColor(new THREE.Color('#000000'))
        }}
      >
        <color attach="background" args={['#000000']} />

        {/* Environment map para reflejos orgánicos */}
        <Environment preset="night" environmentIntensity={0.4} />

        {/* Iluminación para resaltar translucidez */}
        <ambientLight intensity={0.08} />
        <directionalLight position={[3, 4, 3]} intensity={0.5} color="#ddeeff" />
        <directionalLight position={[-2, 1, -3]} intensity={0.2} color="#ffddff" />

        <Scene state={state} />

        {/* Post-processing avanzado */}
        <EffectComposer>
          <Bloom
            luminanceThreshold={0.55}
            luminanceSmoothing={0.35}
            intensity={0.75}
            radius={0.45}
            mipmapBlur
          />
        </EffectComposer>
      </Canvas>
    </div>
  )
}
