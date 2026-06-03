'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { PARTICLE_VERTEX_SHADER, PARTICLE_FRAGMENT_SHADER } from './shaders/brainShaders'

export type BrainState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error' | 'sleep'

interface EnhancedParticlesProps {
  state: BrainState
  count?: number
}

// Colores de partículas por estado
const PARTICLE_COLORS: Record<BrainState, { A: THREE.ColorRepresentation; B: THREE.ColorRepresentation }> = {
  idle:      { A: '#88ddff', B: '#ffffff' },
  listening: { A: '#00ffff', B: '#ccffff' },
  thinking:  { A: '#ff66aa', B: '#ffffff' },
  speaking:  { A: '#44ffcc', B: '#eeffff' },
  error:     { A: '#ff4444', B: '#ffcccc' },
  sleep:     { A: '#6688cc', B: '#aa88cc' },
}

// ── Generar geometría de partículas ───────────────────────────
function makeOrganicParticles(n: number) {
  const positions = new Float32Array(n * 3)
  const sizes = new Float32Array(n)
  const phases = new Float32Array(n)
  const speeds = new Float32Array(n)
  const colors = new Float32Array(n * 3)

  // Radios: partículas más concentradas cerca del cerebro, algunas lejos
  const minR = 1.2
  const maxR = 4.5

  for (let i = 0; i < n; i++) {
    // Distribución no uniforme: más partículas cerca del centro
    const r = minR + Math.pow(Math.random(), 0.7) * (maxR - minR)
    
    // Esfera con concentración en el ecuador
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = r * Math.cos(phi) * 0.8 // Aplanado en Y
    positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta)

    // Tamaño variable
    sizes[i] = 1.2 + Math.random() * 5.5

    // Fase aleatoria
    phases[i] = Math.random() * Math.PI * 2

    // Speed individual
    speeds[i] = 0.3 + Math.random() * 1.2

    // Color aleatorio entre blanco y cian/rosa
    const mix = Math.random()
    colors[i * 3] = 0.5 + mix * 0.5 // R
    colors[i * 3 + 1] = 0.8 + mix * 0.2 // G
    colors[i * 3 + 2] = 0.9 + mix * 0.1 // B
  }

  return { positions, sizes, phases, speeds, colors }
}

export default function EnhancedParticles({ state, count = 1500 }: EnhancedParticlesProps) {
  const materialRef = useRef<THREE.ShaderMaterial>(null)

  const { positions, sizes, phases, speeds } = useMemo(
    () => makeOrganicParticles(count),
    [count]
  )

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uDPR: {
        value:
          typeof window !== 'undefined'
            ? Math.min(window.devicePixelRatio, 2)
            : 1,
      },
      uColorA: { value: new THREE.Color(PARTICLE_COLORS.idle.A) },
      uColorB: { value: new THREE.Color(PARTICLE_COLORS.idle.B) },
      uParticleIntensity: { value: 1.0 },
    }),
    []
  )

  useFrame(({ clock }) => {
    if (!materialRef.current) return

    const t = clock.getElapsedTime()
    const target = PARTICLE_COLORS[state]

    materialRef.current.uniforms.uTime.value = t
    materialRef.current.uniforms.uColorA.value.lerp(
      new THREE.Color(target.A),
      0.04
    )
    materialRef.current.uniforms.uColorB.value.lerp(
      new THREE.Color(target.B),
      0.04
    )

    // Intensidad varía por estado
    const targetIntensity =
      state === 'thinking'
        ? 1.3
        : state === 'error'
          ? 1.4
          : state === 'listening'
            ? 1.1
            : 0.9

    materialRef.current.uniforms.uParticleIntensity.value = THREE.MathUtils.lerp(
      materialRef.current.uniforms.uParticleIntensity.value,
      targetIntensity,
      0.05
    )
  })

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={count}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-aSize"
          array={sizes}
          count={count}
          itemSize={1}
        />
        <bufferAttribute
          attach="attributes-aPhase"
          array={phases}
          count={count}
          itemSize={1}
        />
        <bufferAttribute
          attach="attributes-aSpeed"
          array={speeds}
          count={count}
          itemSize={1}
        />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        vertexShader={PARTICLE_VERTEX_SHADER}
        fragmentShader={PARTICLE_FRAGMENT_SHADER}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}
