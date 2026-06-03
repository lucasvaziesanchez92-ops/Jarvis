'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'

export type BrainState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error' | 'sleep'

interface OrganicBrainMeshProps {
  state: BrainState
}

// ── State Configuration ───────────────────────────────────────
const STATE_CONF: Record<BrainState, {
  baseColor: [number, number, number]
  emissive: [number, number, number]
  rimColor: [number, number, number]
  grooveColor: [number, number, number]
  coreColor: [number, number, number]
  transmissionColor: [number, number, number]
  rimIntensity: number
  grooveIntensity: number
  transmissionIntensity: number
  pulseSpeed: number
}> = {
  idle: {
    baseColor: [0.85, 0.92, 1.0],
    emissive: [0.03, 0.05, 0.12],
    rimColor: [0.0, 0.78, 1.0],
    grooveColor: [0.6, 0.1, 0.4],
    coreColor: [0.2, 0.6, 1.0],
    transmissionColor: [0.0, 0.5, 0.8],
    rimIntensity: 1.6,
    grooveIntensity: 0.65,
    transmissionIntensity: 0.5,
    pulseSpeed: 0.8,
  },
  listening: {
    baseColor: [0.82, 0.96, 1.0],
    emissive: [0.04, 0.08, 0.18],
    rimColor: [0.0, 1.0, 1.0],
    grooveColor: [0.7, 0.2, 0.55],
    coreColor: [0.1, 0.7, 1.0],
    transmissionColor: [0.0, 0.8, 0.9],
    rimIntensity: 2.0,
    grooveIntensity: 0.85,
    transmissionIntensity: 0.7,
    pulseSpeed: 1.2,
  },
  thinking: {
    baseColor: [0.95, 0.88, 0.92],
    emissive: [0.08, 0.04, 0.06],
    rimColor: [1.0, 0.0, 0.4],
    grooveColor: [0.85, 0.1, 0.4],
    coreColor: [0.8, 0.2, 0.6],
    transmissionColor: [0.6, 0.1, 0.5],
    rimIntensity: 2.2,
    grooveIntensity: 1.0,
    transmissionIntensity: 0.6,
    pulseSpeed: 2.5,
  },
  speaking: {
    baseColor: [0.88, 0.96, 0.94],
    emissive: [0.04, 0.1, 0.1],
    rimColor: [0.2, 1.0, 0.8],
    grooveColor: [0.15, 0.65, 0.5],
    coreColor: [0.1, 0.8, 0.6],
    transmissionColor: [0.0, 0.7, 0.6],
    rimIntensity: 1.8,
    grooveIntensity: 0.55,
    transmissionIntensity: 0.45,
    pulseSpeed: 1.0,
  },
  error: {
    baseColor: [0.95, 0.8, 0.8],
    emissive: [0.1, 0.02, 0.02],
    rimColor: [1.0, 0.1, 0.2],
    grooveColor: [0.9, 0.08, 0.15],
    coreColor: [0.8, 0.1, 0.1],
    transmissionColor: [0.6, 0.0, 0.1],
    rimIntensity: 2.5,
    grooveIntensity: 1.2,
    transmissionIntensity: 0.8,
    pulseSpeed: 3.0,
  },
  sleep: {
    baseColor: [0.6, 0.65, 0.75],
    emissive: [0.02, 0.03, 0.06],
    rimColor: [0.35, 0.45, 0.7],
    grooveColor: [0.35, 0.3, 0.55],
    coreColor: [0.2, 0.3, 0.5],
    transmissionColor: [0.2, 0.3, 0.4],
    rimIntensity: 0.9,
    grooveIntensity: 0.35,
    transmissionIntensity: 0.25,
    pulseSpeed: 0.3,
  },
}

// ── Organic Brain Mesh ────────────────────────────────────────
export default function OrganicBrainMesh({ state }: OrganicBrainMeshProps) {
  const groupRef = useRef<THREE.Group>(null)
  const meshRef = useRef<THREE.Mesh>(null)
  const shaderRef = useRef<THREE.WebGLProgramParametersWithUniforms | null>(null)

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

  const cfg = STATE_CONF[state]

  // Shader injection con gradiente + SSS + glow orgánico
  const onBeforeCompile = useMemo(() => {
    return (shader: THREE.WebGLProgramParametersWithUniforms) => {
      shaderRef.current = shader

      // Uniforms
      shader.uniforms.uRimColor = { value: new THREE.Color().fromArray(cfg.rimColor) }
      shader.uniforms.uGrooveColor = { value: new THREE.Color().fromArray(cfg.grooveColor) }
      shader.uniforms.uCoreColor = { value: new THREE.Color().fromArray(cfg.coreColor) }
      shader.uniforms.uTransmissionColor = { value: new THREE.Color().fromArray(cfg.transmissionColor) }
      shader.uniforms.uRimIntensity = { value: cfg.rimIntensity }
      shader.uniforms.uGrooveIntensity = { value: cfg.grooveIntensity }
      shader.uniforms.uTransmissionIntensity = { value: cfg.transmissionIntensity }
      shader.uniforms.uTime = { value: 0 }
      shader.uniforms.uOrganicPulse = { value: 1.0 }

      // Vertex: agregar world pos, curvature, gradient Y
      shader.vertexShader = shader.vertexShader.replace(
        '#include <common>',
        /* glsl */ `
        #include <common>
        varying vec3 vWorldPos;
        varying vec3 vNormalWorld;
        varying float vCurvature;
        varying float vGradientY;
        `
      )

      shader.vertexShader = shader.vertexShader.replace(
        '#include <begin_vertex>',
        /* glsl */ `
        #include <begin_vertex>
        vec4 wp = modelMatrix * vec4(transformed, 1.0);
        vWorldPos = wp.xyz;
        vNormalWorld = normalize((modelMatrix * vec4(normal, 0.0)).xyz);
        vec3 toCenter = normalize(-vWorldPos);
        vCurvature = dot(vNormalWorld, toCenter);
        vGradientY = smoothstep(-1.2, 1.2, vWorldPos.y);
        `
      )

      // Fragment: declara varyings y uniforms
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <common>',
        /* glsl */ `
        #include <common>
        varying vec3 vWorldPos;
        varying vec3 vNormalWorld;
        varying float vCurvature;
        varying float vGradientY;
        uniform vec3 uRimColor;
        uniform vec3 uGrooveColor;
        uniform vec3 uCoreColor;
        uniform vec3 uTransmissionColor;
        uniform float uRimIntensity;
        uniform float uGrooveIntensity;
        uniform float uTransmissionIntensity;
        uniform float uTime;
        uniform float uOrganicPulse;
        `
      )

      // Fragment: inyectar efectos orgánicos después de emissive
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <emissivemap_fragment>',
        /* glsl */ `
        #include <emissivemap_fragment>

        // Fresnel rim con gradiente por altura
        vec3 viewDir = normalize(cameraPosition - vWorldPos);
        float ndotv = clamp(dot(normalize(vNormalWorld), viewDir), 0.0, 1.0);
        float fresnel = pow(1.0 - ndotv, 2.5);
        float rimTop = fresnel * (0.5 + vGradientY * 0.5);

        // Fake SSS (back-scattering en bordes)
        float backScatter = clamp(-dot(normalize(vNormalWorld), viewDir), 0.0, 1.0);
        float grooveDepth = smoothstep(0.15, -0.50, vCurvature);
        float sssGroove = backScatter * grooveDepth * 1.5;

        // Core glow (luz desde adentro)
        float coreGlow = exp(-length(vWorldPos) * 1.8) * uOrganicPulse;

        // Organic noise sutil
        float oNoise = fract(sin(dot(vWorldPos * 4.0 + vec3(uTime * 0.1), vec3(443.897, 441.423, 437.195))) * 43758.5453) * 0.12;

        // Pulse
        float pulseFast = sin(uTime * 3.0 + vWorldPos.y * 2.0) * 0.5 + 0.5;

        // Scanlines orgánicas
        float scan = pow(abs(sin(vWorldPos.y * 25.0 + uTime * 0.8)), 24.0) * 0.03 * (sin(uTime * 1.2) * 0.5 + 0.5);

        // Gradient cian-magenta basado en altura Y
        vec3 cian = vec3(0.0, 0.78, 1.0);
        vec3 midCol = vec3(0.53, 0.27, 1.0);
        vec3 magenta = vec3(1.0, 0.0, 0.4);
        vec3 gradientCol;
        if (vGradientY < 0.5) {
          gradientCol = mix(cian, midCol, smoothstep(0.0, 0.5, vGradientY));
        } else {
          gradientCol = mix(midCol, magenta, smoothstep(0.5, 1.0, vGradientY));
        }

        // Combinar emissive
        totalEmissiveRadiance += gradientCol * rimTop * uRimIntensity * 0.6;
        totalEmissiveRadiance += uGrooveColor * grooveDepth * uGrooveIntensity;
        totalEmissiveRadiance += uTransmissionColor * sssGroove * uTransmissionIntensity * 0.4;
        totalEmissiveRadiance += uCoreColor * coreGlow * 2.0;
        totalEmissiveRadiance += gradientCol * oNoise * fresnel * 0.3;
        totalEmissiveRadiance += gradientCol * scan;
        totalEmissiveRadiance += uRimColor * pulseFast * 0.05 * grooveDepth;

        // Color base orgánico
        diffuseColor.rgb = mix(diffuseColor.rgb, gradientCol, 0.12);
        `
      )
    }
  }, []) // cache key separado

  const customProgramCacheKey = useMemo(() => () => 'organic-brain-v2', [])

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const c = STATE_CONF[state]
    const shader = shaderRef.current

    if (shader) {
      shader.uniforms.uRimColor.value.lerp(new THREE.Color().fromArray(c.rimColor), 0.04)
      shader.uniforms.uGrooveColor.value.lerp(new THREE.Color().fromArray(c.grooveColor), 0.04)
      shader.uniforms.uCoreColor.value.lerp(new THREE.Color().fromArray(c.coreColor), 0.04)
      shader.uniforms.uTransmissionColor.value.lerp(new THREE.Color().fromArray(c.transmissionColor), 0.04)

      const ri = shader.uniforms.uRimIntensity.value
      shader.uniforms.uRimIntensity.value = ri + (c.rimIntensity - ri) * 0.03

      const gi = shader.uniforms.uGrooveIntensity.value
      shader.uniforms.uGrooveIntensity.value = gi + (c.grooveIntensity - gi) * 0.03

      const ti = shader.uniforms.uTransmissionIntensity.value
      shader.uniforms.uTransmissionIntensity.value = ti + (c.transmissionIntensity - ti) * 0.03

      shader.uniforms.uTime.value = t
      shader.uniforms.uOrganicPulse.value = Math.sin(t * c.pulseSpeed) * 0.3 + 0.7
    }

    if (groupRef.current) {
      groupRef.current.rotation.y += 0.0004
    }
  })

  if (!geometry) return null

  return (
    <group ref={groupRef} scale={0.72}>
      <mesh ref={meshRef} geometry={geometry} castShadow>
        <meshPhysicalMaterial
          color={new THREE.Color().fromArray(cfg.baseColor)}
          emissive={new THREE.Color().fromArray(cfg.emissive)}
          emissiveIntensity={1.5}
          metalness={0.0}
          roughness={0.18}
          clearcoat={1.0}
          clearcoatRoughness={0.05}
          ior={1.45}
          transmission={0.35}
          thickness={2.0}
          attenuationColor={new THREE.Color(0.8, 0.2, 0.5)}
          attenuationDistance={1.8}
          envMapIntensity={0.8}
          side={THREE.DoubleSide}
          onBeforeCompile={onBeforeCompile}
          customProgramCacheKey={customProgramCacheKey}
        />
      </mesh>
    </group>
  )
}

useGLTF.preload('/models/brain_draco.glb', true)
