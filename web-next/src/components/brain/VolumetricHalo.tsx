'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export type BrainState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error' | 'sleep'

interface VolumetricHaloProps {
  state: BrainState
}

// Colores de halo por estado
const HALO_COLORS: Record<BrainState, THREE.ColorRepresentation> = {
  idle: '#4466ff',
  listening: '#00ccff',
  thinking: '#ff2288',
  speaking: '#00ddaa',
  error: '#ff2244',
  sleep: '#445599',
}

export default function VolumetricHalo({ state }: VolumetricHaloProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const materialRef = useRef<THREE.ShaderMaterial>(null)

  const uniforms = useMemo(
    () => ({
      uHaloColor: { value: new THREE.Color(HALO_COLORS.idle) },
      uHaloIntensity: { value: 0.35 },
      uTime: { value: 0 },
    }),
    []
  )

  const vertexShader = /* glsl */ `
    varying vec3 vNormal;
    varying vec3 vView;
    varying float vDepth;

    void main() {
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      vNormal = normalize(normalMatrix * normal);
      vView = normalize(-mvPosition.xyz);
      vDepth = -mvPosition.z;
      gl_Position = projectionMatrix * mvPosition;
    }
  `

  const fragmentShader = /* glsl */ `
    uniform vec3 uHaloColor;
    uniform float uHaloIntensity;
    uniform float uTime;

    varying vec3 vNormal;
    varying vec3 vView;
    varying float vDepth;

    void main() {
      float fresnel = pow(1.0 - clamp(dot(vNormal, vView), 0.0, 1.0), 2.0);
      float pulse = sin(uTime * 0.4) * 0.3 + 0.7;

      // Atenuación por distancia (más débil cerca y lejos)
      float depthAtt = smoothstep(0.0, 3.0, vDepth) * (1.0 - smoothstep(6.0, 10.0, vDepth));

      float alpha = fresnel * uHaloIntensity * pulse * depthAtt * 0.5;

      gl_FragColor = vec4(uHaloColor, alpha);
    }
  `

  useFrame(({ clock }) => {
    if (!materialRef.current) return

    const t = clock.getElapsedTime()
    materialRef.current.uniforms.uTime.value = t
    materialRef.current.uniforms.uHaloColor.value.lerp(
      new THREE.Color(HALO_COLORS[state]),
      0.03
    )

    // Intensidad por estado
    const targetIntensity =
      state === 'thinking'
        ? 0.5
        : state === 'error'
          ? 0.55
          : state === 'listening'
            ? 0.45
            : 0.35

    materialRef.current.uniforms.uHaloIntensity.value = THREE.MathUtils.lerp(
      materialRef.current.uniforms.uHaloIntensity.value,
      targetIntensity,
      0.03
    )
  })

  return (
    <mesh ref={meshRef} scale={1.8}>
      <sphereGeometry args={[1, 32, 32]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        side={THREE.BackSide}
      />
    </mesh>
  )
}
