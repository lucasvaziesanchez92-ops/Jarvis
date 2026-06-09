'use client'

import { useRef, useMemo, useState, useEffect, Suspense } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import * as THREE from 'three'
import { useJarvisStore } from '@/store/jarvisStore'

/* ──────────────────────────────────────────────────────────────
   JARVIS BRAIN v2 — Ice Material + Particles + States
   Based on brain-3d.html we recreated earlier.
   Now integrated into React Three Fiber with Zustand store.
─────────────────────────────────────────────────────────────── */

/* ── Color Palettes per state & personality ─────────────────── */
const STATE_META = {
  idle:      { grooveIntensity: 0.55, rimIntensity: 1.4 },
  listening: { grooveIntensity: 0.70, rimIntensity: 1.8 },
  thinking:  { grooveIntensity: 0.85, rimIntensity: 2.0 },
  speaking:  { grooveIntensity: 0.50, rimIntensity: 1.5 },
  error:     { grooveIntensity: 1.00, rimIntensity: 2.2 },
  sleep:     { grooveIntensity: 0.30, rimIntensity: 0.8 },
}

const PERSONALITY_THEMES = {
  profesional: {
    idle:      { base: 0xd0e8e8, emissive: 0x2a1030, edge: 0x40e0d0 },
    listening: { base: 0xc8e0e8, emissive: 0x2a3040, edge: 0x00ff88 },
    thinking:  { base: 0xe8d0e0, emissive: 0x801030, edge: 0xff69b4 },
    speaking:  { base: 0xd0e8e0, emissive: 0x1a4030, edge: 0x00d4ff },
    error:     { base: 0xffa0a0, emissive: 0x401010, edge: 0xff4444 },
    sleep:     { base: 0x8890a0, emissive: 0x101020, edge: 0x5566aa },
  },
  amigable: {
    idle:      { base: 0xffe4e1, emissive: 0x3a1015, edge: 0xff6b6b },
    listening: { base: 0xffdab9, emissive: 0x401810, edge: 0xffaa00 },
    thinking:  { base: 0xffe4e1, emissive: 0x501020, edge: 0xff3b75 },
    speaking:  { base: 0xfff0f5, emissive: 0x3a0820, edge: 0xff8e53 },
    error:     { base: 0xffa0a0, emissive: 0x401010, edge: 0xff4444 },
    sleep:     { base: 0xb0a0a0, emissive: 0x1a0a0a, edge: 0xcc8888 },
  },
  tecnica: {
    idle:      { base: 0xd8f3dc, emissive: 0x082b18, edge: 0x00ff66 },
    listening: { base: 0xe8f5e9, emissive: 0x0a3310, edge: 0x39ff14 },
    thinking:  { base: 0xf1f8e9, emissive: 0x2e5a1c, edge: 0xc6ff00 },
    speaking:  { base: 0xe8f8f5, emissive: 0x064e3b, edge: 0x10b981 },
    error:     { base: 0xffa0a0, emissive: 0x401010, edge: 0xff4444 },
    sleep:     { base: 0x90a095, emissive: 0x051a08, edge: 0x4d7c0f },
  },
  ejecutiva: {
    idle:      { base: 0xfff3e0, emissive: 0x382a08, edge: 0xffb74d },
    listening: { base: 0xffecb3, emissive: 0x4a3205, edge: 0xffd700 },
    thinking:  { base: 0xfff8e1, emissive: 0x5d4037, edge: 0xff8a65 },
    speaking:  { base: 0xffebd7, emissive: 0x3e2723, edge: 0xffaa00 },
    error:     { base: 0xffa0a0, emissive: 0x401010, edge: 0xff4444 },
    sleep:     { base: 0xa09585, emissive: 0x1a1205, edge: 0xb5a642 },
  },
  creativa: {
    idle:      { base: 0xf3e5f5, emissive: 0x311b92, edge: 0x8a2be2 },
    listening: { base: 0xe1bee7, emissive: 0x4a148c, edge: 0xda70d6 },
    thinking:  { base: 0xfce4ec, emissive: 0x880e4f, edge: 0xff1493 },
    speaking:  { base: 0xf3ebd7, emissive: 0x3a0f7c, edge: 0x9333ea },
    error:     { base: 0xffa0a0, emissive: 0x401010, edge: 0xff4444 },
    sleep:     { base: 0x988da0, emissive: 0x120326, edge: 0x7c3aed },
  },
  soporte: {
    idle:      { base: 0xe3f2fd, emissive: 0x0d47a1, edge: 0x3b82f6 },
    listening: { base: 0xe0f7fa, emissive: 0x006064, edge: 0x00e5ff },
    thinking:  { base: 0xe1f5fe, emissive: 0x01579b, edge: 0x0288d1 },
    speaking:  { base: 0xe0f2f1, emissive: 0x004d40, edge: 0x14b8a6 },
    error:     { base: 0xffa0a0, emissive: 0x401010, edge: 0xff4444 },
    sleep:     { base: 0x8ea2b0, emissive: 0x051d3b, edge: 0x5a8fb2 },
  },
}

function IceBrain() {
  const groupRef = useRef<THREE.Group>(null)
  const mainMeshRef = useRef<THREE.Mesh>(null)
  const innerMeshRef = useRef<THREE.Mesh>(null)
  const glowMeshRef = useRef<THREE.Mesh>(null)

  const { activityState, persona, brainMode } = useJarvisStore()
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null)

  /* Load STL — relative proxy path or public fallback */
  useEffect(() => {
    const loader = new STLLoader()
    const urls = [
      '/brain.stl',
      '/models/brain.stl',
    ]
    let idx = 0
    const tryNext = () => {
      if (idx >= urls.length) return
      const url = urls[idx]
      loader.load(url, (geo) => {
        geo.computeVertexNormals()
        geo.center()
        setGeometry(geo)
      }, undefined, () => {
        idx++
        tryNext()
      })
    }
    tryNext()
  }, [])

  /* Materials definitions */
  const innerMatRef = useRef<THREE.MeshPhysicalMaterial | null>(null)
  const glowMatRef = useRef<THREE.MeshBasicMaterial | null>(null)

  const materials = useMemo(() => {
    // 1. Hologram (our custom Ice material)
    const hologram = new THREE.MeshPhysicalMaterial({
      color: 0xd0e8e8, emissive: 0x2a1030, emissiveIntensity: 0.3, metalness: 0, roughness: 0.25,
      transmission: 0.6, thickness: 1.2, ior: 1.45, clearcoat: 0.8, clearcoatRoughness: 0.1,
      sheen: 0.5, sheenColor: new THREE.Color(0xff69b4), sheenRoughness: 0.5,
      specularIntensity: 1.0, specularColor: new THREE.Color(0xffffff),
      side: THREE.DoubleSide, flatShading: true, envMapIntensity: 0.5,
    })

    // 2. Wireframe
    const wireframe = new THREE.MeshBasicMaterial({
      color: 0x44ccdd, wireframe: true, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending
    })

    // 3. Solid
    const solid = new THREE.MeshStandardMaterial({
      color: 0x88aabb, roughness: 0.8, metalness: 0.1, flatShading: true
    })

    // 4. PBR
    const pbr = new THREE.MeshPhysicalMaterial({
      color: 0xffffff, roughness: 0.1, metalness: 0.9, clearcoat: 1.0, clearcoatRoughness: 0.05
    })

    // 5. Unlit
    const unlit = new THREE.MeshBasicMaterial({
      color: 0x4488aa
    })

    // 6. Normal
    const normal = new THREE.MeshNormalMaterial({
      flatShading: true
    })

    // 7. Toon
    const toon = new THREE.MeshToonMaterial({
      color: 0x44ccdd
    })

    // 8. Sketch
    const sketch = new THREE.MeshBasicMaterial({
      color: 0x888888, wireframe: true, transparent: true, opacity: 0.15
    })

    return { hologram, wireframe, solid, pbr, unlit, normal, toon, sketch }
  }, [])

  const innerMaterial = useMemo(() => {
    const m = new THREE.MeshPhysicalMaterial({
      color: 0x40e0d0, emissive: 0xff1493, emissiveIntensity: 0.4,
      transparent: true, opacity: 0.15, side: THREE.BackSide, flatShading: true,
    })
    innerMatRef.current = m
    return m
  }, [])

  const glowMaterial = useMemo(() => {
    const m = new THREE.MeshBasicMaterial({
      color: 0xff69b4, transparent: true, opacity: 0, side: THREE.FrontSide,
      blending: THREE.AdditiveBlending, depthWrite: false,
    })
    glowMatRef.current = m
    return m
  }, [])

  /* Animation loop */
  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    
    // Resolve dynamic personality and state colors
    const pName = persona?.name || 'profesional'
    const theme = PERSONALITY_THEMES[pName as keyof typeof PERSONALITY_THEMES] || PERSONALITY_THEMES.profesional
    const stateColor = theme[activityState as keyof typeof theme] || theme.idle
    
    // Idle rotation
    groupRef.current.rotation.x = (-Math.PI / 2) + Math.sin(t * 0.15) * 0.05
    groupRef.current.rotation.z = (Math.PI / 3.5) + Math.cos(t * 0.1) * 0.03

    // Lerp colors dynamically
    const activeColor = new THREE.Color(stateColor.base)
    const edgeColor = new THREE.Color(stateColor.edge)
    const emissiveColor = new THREE.Color(stateColor.emissive)

    // Hologram
    materials.hologram.color.lerp(activeColor, 0.05)
    materials.hologram.emissive.lerp(emissiveColor, 0.05)
    materials.hologram.sheenColor.lerp(edgeColor, 0.05)

    if (activityState === 'thinking') {
      const blink = (Math.sin(t * 3) + 1) / 2
      materials.hologram.opacity = 0.5 + blink * 0.5
      materials.hologram.transmission = 0.3 + blink * 0.5
      materials.hologram.emissiveIntensity = 0.3 + blink * 0.5
    } else if (activityState === 'speaking') {
      materials.hologram.opacity = 1
      materials.hologram.transmission = 0
      materials.hologram.emissiveIntensity = 1.0
    } else {
      materials.hologram.opacity = 1
      materials.hologram.transmission = 0.6
      materials.hologram.emissiveIntensity = 0.3
    }

    // Wireframe
    materials.wireframe.color.lerp(edgeColor, 0.05)
    materials.wireframe.opacity = 0.2 + (activityState === 'speaking' ? 0.3 : activityState === 'thinking' ? 0.15 * Math.sin(t * 4) + 0.25 : 0.1)

    // Solid
    materials.solid.color.lerp(activeColor, 0.05)

    // PBR
    materials.pbr.color.lerp(activeColor, 0.05)

    // Unlit
    materials.unlit.color.lerp(activeColor, 0.05)

    // Toon
    materials.toon.color.lerp(edgeColor, 0.05)

    // Sketch
    materials.sketch.color.lerp(edgeColor, 0.05)

    // Glows
    if (innerMatRef.current) {
      innerMatRef.current.color.lerp(edgeColor, 0.05)
      innerMatRef.current.emissive.lerp(edgeColor, 0.05)
      innerMatRef.current.opacity = (brainMode === 'hologram' || brainMode === 'pbr') ? 0.15 : 0
    }

    if (glowMatRef.current) {
      glowMatRef.current.color.lerp(edgeColor, 0.05)
      glowMatRef.current.opacity = (brainMode === 'hologram' || brainMode === 'pbr') ? (0.15 + Math.sin(t * 0.8) * 0.05) : 0
    }
  })

  if (!geometry) {
    return (
      <mesh>
        <icosahedronGeometry args={[0.8, 2]} />
        <meshBasicMaterial color="#4488aa" wireframe />
      </mesh>
    )
  }

  const box = new THREE.Box3().setFromObject(new THREE.Mesh(geometry))
  const size = box.getSize(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  const scale = 1.6 / maxDim

  const activeMaterial = materials[brainMode as keyof typeof materials] || materials.hologram

  return (
    <group ref={groupRef} scale={scale}>
      {/* Main brain */}
      <mesh ref={mainMeshRef} geometry={geometry} castShadow receiveShadow>
        <primitive object={activeMaterial} attach="material" />
      </mesh>
      {/* Inner glow */}
      <mesh ref={innerMeshRef} geometry={geometry} scale={[0.97, 0.97, 0.97]}>
        <primitive object={innerMaterial} attach="material" />
      </mesh>
      {/* Outer glow */}
      <mesh ref={glowMeshRef} geometry={geometry} scale={[1.02, 1.02, 1.02]}>
        <primitive object={glowMaterial} attach="material" />
      </mesh>
    </group>
  )
}

/* ── Personality Palettes for particles and bubbles ─────────── */
const PERSONALITY_PALETTES = {
  profesional: [0x40e0d0, 0xff69b4, 0xffffff, 0x00d4ff, 0x7c3aed],
  amigable:    [0xff6b6b, 0xffaa00, 0xffffff, 0xff8e53, 0xffc0cb],
  tecnica:     [0x00ff66, 0x39ff14, 0xffffff, 0xc6ff00, 0x10b981],
  ejecutiva:   [0xffb74d, 0xffd700, 0xffffff, 0xffaa00, 0xfef08a],
  creativa:    [0x8a2be2, 0xda70d6, 0xffffff, 0xff1493, 0x9333ea],
  soporte:     [0x3b82f6, 0x00e5ff, 0xffffff, 0x0288d1, 0x14b8a6],
}

/* ── Particle Orbitals ─────────────────────────────────────── */
function ParticleField() {
  const pointsRef = useRef<THREE.Points>(null)
  const velocities = useRef<Array<{ angle: number; speed: number; yOffset: number; rad: number }>>([])
  const colorIndicesRef = useRef<number[]>([])

  const { persona } = useJarvisStore()
  const PARTICLE_COUNT = 32
  const defaultPalette = PERSONALITY_PALETTES.profesional

  const geo = useMemo(() => {
    const positions = new Float32Array(PARTICLE_COUNT * 3)
    const colors = new Float32Array(PARTICLE_COUNT * 3)
    velocities.current = []
    colorIndicesRef.current = []

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const radius = 1.5 + Math.random() * 2

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = radius * Math.cos(phi)

      const colIdx = Math.floor(Math.random() * defaultPalette.length)
      colorIndicesRef.current.push(colIdx)

      const c = new THREE.Color(defaultPalette[colIdx])
      colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b

      velocities.current.push({ angle: theta, speed: 0.2 + Math.random() * 0.8, yOffset: Math.random() * Math.PI * 2, rad: radius })
    }

    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return g
  }, [])

  useFrame(({ clock }) => {
    if (!pointsRef.current) return
    const pos = (pointsRef.current.geometry as THREE.BufferGeometry).attributes.position.array as Float32Array
    const colors = (pointsRef.current.geometry as THREE.BufferGeometry).attributes.color.array as Float32Array
    const t = clock.getElapsedTime()
    const dt = clock.getDelta()

    // Dynamic color updates based on active persona
    const pName = persona?.name || 'profesional'
    const pPalette = PERSONALITY_PALETTES[pName as keyof typeof PERSONALITY_PALETTES] || PERSONALITY_PALETTES.profesional
    const targetColors = pPalette.map(hex => new THREE.Color(hex))

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const v = velocities.current[i]
      v.angle += v.speed * dt * 0.5
      const r = v.rad + Math.sin(t + v.yOffset) * 0.3
      pos[i * 3] = r * Math.cos(v.angle)
      pos[i * 3 + 1] = r * Math.sin(t * 0.3 + v.yOffset) * 0.5
      pos[i * 3 + 2] = r * Math.sin(v.angle)

      // Lerp particle color attribute
      const colIdx = colorIndicesRef.current[i]
      const target = targetColors[colIdx % targetColors.length]
      colors[i * 3]     += (target.r - colors[i * 3]) * 0.05
      colors[i * 3 + 1] += (target.g - colors[i * 3 + 1]) * 0.05
      colors[i * 3 + 2] += (target.b - colors[i * 3 + 2]) * 0.05
    }

    ;(pointsRef.current.geometry as THREE.BufferGeometry).attributes.position.needsUpdate = true
    ;(pointsRef.current.geometry as THREE.BufferGeometry).attributes.color.needsUpdate = true
  })

  return (
    <points ref={pointsRef} geometry={geo}>
      <pointsMaterial
        size={0.05}
        vertexColors
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        transparent
        opacity={0.8}
        sizeAttenuation
      />
    </points>
  )
}

/* ── Thought Bubbles floating ──────────────────────────────── */
function ThoughtBubbles() {
  const bubbles = useRef<THREE.Mesh[]>([])
  const { persona } = useJarvisStore()
  const defaultPalette = PERSONALITY_PALETTES.profesional

  const group = useMemo(() => {
    const g = new THREE.Group()
    bubbles.current = []
    for (let i = 0; i < 8; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: defaultPalette[i % defaultPalette.length],
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending
      })
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.03, 8, 8), mat)
      mesh.position.set((Math.random() - 0.5) * 3, -2 - Math.random() * 3, (Math.random() - 0.5) * 3)
      mesh.userData = { speed: 0.3 + Math.random() * 0.7, phase: Math.random() * Math.PI * 2, wobble: Math.random() * 0.5 }
      g.add(mesh)
      bubbles.current.push(mesh)
    }
    return g
  }, [])

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const dt = clock.getDelta()

    const pName = persona?.name || 'profesional'
    const pPalette = PERSONALITY_PALETTES[pName as keyof typeof PERSONALITY_PALETTES] || PERSONALITY_PALETTES.profesional
    const targetColors = pPalette.map(hex => new THREE.Color(hex))

    bubbles.current.forEach((th, i) => {
      th.position.y += th.userData.speed * dt * 0.5
      th.position.x += Math.sin(th.userData.wobble * t + th.userData.phase) * dt * 0.2
      
      const mat = th.material as THREE.MeshBasicMaterial
      const target = targetColors[i % targetColors.length]
      mat.color.lerp(target, 0.05)

      mat.opacity = 0.2 + Math.sin(t * 2 + th.userData.phase) * 0.15
      if (th.position.y > 3.5) {
        th.position.y = -2.5
        th.position.x = (Math.random() - 0.5) * 3
        th.position.z = (Math.random() - 0.5) * 3
      }
    })
  })

  return <primitive object={group} />
}

/* ── Lights ────────────────────────────────────────────────── */
function StageLights() {
  const { scene } = useThree()

  useEffect(() => {
    scene.background = new THREE.Color(0x0a0a0f)
    const ambient = new THREE.AmbientLight(0x404040, 0.5)
    scene.add(ambient)
    const dir = new THREE.DirectionalLight(0xffffff, 1.2)
    dir.position.set(5, 5, 5)
    dir.castShadow = true
    scene.add(dir)
    const fill = new THREE.DirectionalLight(0xff69b4, 0.6)
    fill.position.set(-3, 2, -2)
    scene.add(fill)
    const rim = new THREE.DirectionalLight(0x40e0d0, 0.8)
    rim.position.set(0, -3, 4)
    scene.add(rim)
    const bottom = new THREE.PointLight(0xff1493, 0.5, 10)
    bottom.position.set(0, -2, 0)
    scene.add(bottom)
    const top = new THREE.PointLight(0xff69b4, 0.4, 8)
    top.position.set(0, 3, 0)
    scene.add(top)

    return () => {
      scene.remove(ambient, dir, fill, rim, bottom, top)
    }
  }, [scene])

  return null
}

/* ── Exported Scene ────────────────────────────────────────── */
export default function BrainBackground() {
  return (
    <div className="fixed inset-0 z-0">
      <Canvas
        camera={{ position: [3, 0, 4], fov: 45, near: 0.1, far: 100 }}
        gl={{ antialias: true, alpha: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.0 }}
        shadows
      >
        <color attach="background" args={['#0a0a0f']} />
        <fog attach="fog" args={['#0a0a0f', 6, 20]} />
        <OrbitControls
          enableDamping
          dampingFactor={0.05}
          minDistance={1.5}
          maxDistance={8}
          target={[0, 0, 0]}
        />
        <Suspense fallback={null}>
          <StageLights />
          <IceBrain />
          <ParticleField />
          <ThoughtBubbles />
        </Suspense>
        <EffectComposer>
          <Bloom intensity={0.6} luminanceThreshold={0.2} luminanceSmoothing={0.9} />
        </EffectComposer>
      </Canvas>
    </div>
  )
}
