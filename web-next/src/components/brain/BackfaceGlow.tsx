'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'

export type BrainState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error' | 'sleep'

interface BackfaceGlowProps {
  state: BrainState
}

// Colores por estado para el glow interior
const GLOW_COLORS: Record<BrainState, THREE.ColorRepresentation> = {
  idle: '#3366ff',
  listening: '#00ccff',
  thinking: '#ff2288',
  speaking: '#00ddaa',
  error: '#ff2222',
  sleep: '#445599',
}

export default function BackfaceGlow({ state }: BackfaceGlowProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const materialRef = useRef<THREE.MeshBasicMaterial>(null)

  // Usamos la misma geometría del cerebro
  const { scene } = useGLTF('/models/brain_draco.glb', true)

  const geometry = useMemo(() => {
    let g: THREE.BufferGeometry | null = null
    scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh && !g) {
        g = (child as THREE.Mesh).geometry.clone()
      }
    })
    return g
  }, [scene])

  // Escalado sutil para que el glow asome por los bordes
  const scale = 1.04

  useFrame(({ clock }) => {
    if (!materialRef.current) return

    const t = clock.getElapsedTime()
    const targetColor = new THREE.Color(GLOW_COLORS[state])

    // Suave transición de color
    materialRef.current.color.lerp(targetColor, 0.04)

    // Opacidad pulsante orgánica
    const pulse = Math.sin(t * 1.0) * 0.15 + 0.2
    materialRef.current.opacity = THREE.MathUtils.lerp(
      materialRef.current.opacity,
      pulse,
      0.05
    )
  })

  if (!geometry) return null

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      scale={[scale, scale, scale]}
    >
      <meshBasicMaterial
        ref={materialRef}
        color={GLOW_COLORS[state]}
        transparent
        opacity={0.2}
        side={THREE.BackSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  )
}

useGLTF.preload('/models/brain_draco.glb', true)
