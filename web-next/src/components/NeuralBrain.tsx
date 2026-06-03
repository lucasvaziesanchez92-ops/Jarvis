import { useRef, useMemo, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useGLTF, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

/* ────────────────────────────────────────────────────────────
   NEURAL BRAIN — Professional Holographic Brain
   
   Technique: MeshPhysicalMaterial + onBeforeCompile shader
   injection. We extend the native PBR material (which gives us
   real lighting, specular, reflections) by injecting custom
   GLSL for rim lighting and curvature-based groove coloring.
   
   This solves the black-background problem because the brain
   is rendered as a solid glossy/emissive surface (like the
   reference image), not as transparent glass.
   
   Key learnings from research:
   - MeshPhysicalMaterial.transmission FAILS on black bg
   - The reference is solid glossy ceramic, not glass
   - onBeforeCompile is the standard Three.js way to extend
     native materials with custom effects
   ──────────────────────────────────────────────────────────── */

export type BrainState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error' | 'sleep'

interface NeuralBrainProps {
  state?: BrainState
}

const STATE_CONF: Record<BrainState, {
  base: [number, number, number]      // surface color tint
  emissive: [number, number, number]  // base self-illumination
  edge: [number, number, number]      // rim/fresnel glow
  groove: [number, number, number]    // sulci interior
  grooveIntensity: number
  rimIntensity: number
}> = {
  idle:      { base: [0.90,0.95,1.00], emissive: [0.03,0.06,0.10], edge: [0.25,0.85,1.00], groove: [0.60,0.10,0.40], grooveIntensity: 0.55, rimIntensity: 1.4 },
  listening: { base: [0.88,0.96,1.00], emissive: [0.04,0.08,0.12], edge: [0.15,0.95,1.00], groove: [0.70,0.20,0.55], grooveIntensity: 0.70, rimIntensity: 1.8 },
  thinking:  { base: [0.95,0.90,0.94], emissive: [0.08,0.05,0.07], edge: [0.95,0.30,0.60], groove: [0.85,0.10,0.40], grooveIntensity: 0.85, rimIntensity: 2.0 },
  speaking:  { base: [0.90,0.96,0.94], emissive: [0.04,0.10,0.08], edge: [0.20,1.00,0.80], groove: [0.15,0.65,0.50], grooveIntensity: 0.50, rimIntensity: 1.5 },
  error:     { base: [0.95,0.80,0.80], emissive: [0.10,0.03,0.03], edge: [1.00,0.15,0.20], groove: [0.90,0.08,0.15], grooveIntensity: 1.00, rimIntensity: 2.2 },
  sleep:     { base: [0.60,0.65,0.75], emissive: [0.02,0.03,0.06], edge: [0.35,0.45,0.70], groove: [0.35,0.30,0.55], grooveIntensity: 0.30, rimIntensity: 0.8 },
}

/* ── Brain Mesh Component ────────────────────────────────── */
function Brain({ state }: { state: BrainState }) {
  const groupRef = useRef<THREE.Group>(null)
  const meshRef = useRef<THREE.Mesh>(null)
  const materialRef = useRef<THREE.MeshPhysicalMaterial>(null)
  const shaderRef = useRef<THREE.WebGLProgramParametersWithUniforms | null>(null)
  const { scene } = useGLTF('/models/brain_optimized.glb')

  const geo = useMemo(() => {
    let g: THREE.BufferGeometry | null = null
    scene.traverse(c => { if ((c as THREE.Mesh).isMesh && !g) g = (c as THREE.Mesh).geometry.clone() })
    return g
  }, [scene])

  const cfg = STATE_CONF[state]

  /* Shader injection: we hook into Three.js native
     MeshPhysicalMaterial and add rim light + groove color */
  const onBeforeCompile = useMemo(() => (shader: THREE.WebGLProgramParametersWithUniforms) => {
    shaderRef.current = shader

    // Uniforms for injected effects
    shader.uniforms.uRimColor = { value: new THREE.Color().fromArray(cfg.edge) }
    shader.uniforms.uGrooveColor = { value: new THREE.Color().fromArray(cfg.groove) }
    shader.uniforms.uRimIntensity = { value: cfg.rimIntensity }
    shader.uniforms.uGrooveIntensity = { value: cfg.grooveIntensity }
    shader.uniforms.uTime = { value: 0 }

    // ── Vertex Shader: add varyings ──────────────────────
    shader.vertexShader = shader.vertexShader.replace(
      '#include <common>',
      /* glsl */ `
      #include <common>
      varying vec3 vWorldPos;
      varying vec3 vNormalWorld;
      varying float vCurvature;
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
      `
    )

    // ── Fragment Shader: add varyings & uniforms ───────────
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <common>',
      /* glsl */ `
      #include <common>
      varying vec3 vWorldPos;
      varying vec3 vNormalWorld;
      varying float vCurvature;
      uniform vec3 uRimColor;
      uniform vec3 uGrooveColor;
      uniform float uRimIntensity;
      uniform float uGrooveIntensity;
      uniform float uTime;
      `
    )

    // Inject after emissivemap: add rim light + groove glow
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <emissivemap_fragment>',
      /* glsl */ `
      #include <emissivemap_fragment>

      // Fresnel rim light (silhouette glow)
      vec3 viewDir = normalize(cameraPosition - vWorldPos);
      float ndotv = max(dot(normalize(vNormalWorld), viewDir), 0.0);
      float fresnel = pow(1.0 - ndotv, 3.0);
      totalEmissiveRadiance += uRimColor * fresnel * uRimIntensity;

      // Curvature-based groove coloring (magenta in sulci)
      float concave = smoothstep(0.15, -0.50, vCurvature);
      totalEmissiveRadiance += uGrooveColor * concave * uGrooveIntensity;

      // Subtle tech scanline
      float scan = pow(abs(sin(vWorldPos.y * 30.0 + uTime * 2.0)), 16.0) * 0.04;
      totalEmissiveRadiance += uRimColor * scan;
      `
    )
  }, []) // empty deps: we re-configure in useFrame

  // customProgramCacheKey prevents Three.js from reusing a cached
  // program without our injections
  const programCacheKey = useMemo(() => () => 'brain-holographic-v1', [])

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const c = STATE_CONF[state]
    const shader = shaderRef.current

    if (shader) {
      // Smoothly lerp colors to target state
      shader.uniforms.uRimColor.value.lerp(new THREE.Color().fromArray(c.edge), 0.05)
      shader.uniforms.uGrooveColor.value.lerp(new THREE.Color().fromArray(c.groove), 0.05)

      // Lerp intensities
      const ri = shader.uniforms.uRimIntensity.value
      shader.uniforms.uRimIntensity.value = ri + (c.rimIntensity - ri) * 0.04

      const gi = shader.uniforms.uGrooveIntensity.value
      shader.uniforms.uGrooveIntensity.value = gi + (c.grooveIntensity - gi) * 0.04

      shader.uniforms.uTime.value = t
    }

    // Gentle idle rotation
    if (groupRef.current) groupRef.current.rotation.y += 0.0005
  })

  if (!geo) return null

  return (
    <group ref={groupRef} scale={0.75}>
      <mesh ref={meshRef} geometry={geo} castShadow>
        <meshPhysicalMaterial
          ref={materialRef}
          color={new THREE.Color().fromArray(cfg.base)}
          emissive={new THREE.Color().fromArray(cfg.emissive)}
          emissiveIntensity={2.0}
          metalness={0.05}
          roughness={0.25}
          clearcoat={1.0}
          clearcoatRoughness={0.1}
          ior={1.5}
          envMapIntensity={1.0}
          side={THREE.DoubleSide}
          onBeforeCompile={onBeforeCompile}
          customProgramCacheKey={programCacheKey}
        />
      </mesh>
    </group>
  )
}

/* ── Fallback while GLB loads ───────────────────────────── */
function Fallback() {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.1
  })
  return (
    <mesh ref={ref}>
      <icosahedronGeometry args={[0.7, 3]} />
      <meshBasicMaterial color="#4488aa" wireframe />
    </mesh>
  )
}

/* ── Main Export ──────────────────────────────────────────── */
export default function NeuralBrain({ state = 'idle' }: NeuralBrainProps) {
  const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)

  return (
    <div className="relative w-full h-full" style={{ background: '#000000' }}>
      <Canvas
        camera={{ position: [0, 0.0, 5.5], fov: 35, near: 0.01, far: 50 }}
        dpr={isMobile ? Math.min(window.devicePixelRatio, 1.5) : Math.min(window.devicePixelRatio, 2)}
        gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
        onCreated={({ gl }) => {
          gl.setClearColor(new THREE.Color('#000000'))
          gl.toneMapping = THREE.ACESFilmicToneMapping
          gl.toneMappingExposure = 1.2
        }}
      >
        {/* Pure black scene background (no visible env) */}
        <color attach="background" args={['#000000']} />

        {/* Environment map for glossy reflections only */}
        <Environment preset="studio" environmentIntensity={0.5} />

        {/* Subtle fill lights for extra specular definition */}
        <ambientLight intensity={0.15} />
        <directionalLight position={[3, 5, 4]} intensity={0.6} color="#e0f0ff" />
        <directionalLight position={[-2, 1, -3]} intensity={0.3} color="#ffccff" />

        <Suspense fallback={<Fallback />}>
          <Brain state={state} />
        </Suspense>

        {/* Very subtle bloom — only brightest edges glow */}
        <EffectComposer>
          <Bloom
            luminanceThreshold={0.85}
            luminanceSmoothing={0.3}
            intensity={0.3}
            mipmapBlur
          />
        </EffectComposer>
      </Canvas>
    </div>
  )
}

useGLTF.preload('/models/brain_optimized.glb')
