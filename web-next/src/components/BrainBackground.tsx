'use client';

import { useRef, useMemo, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { OrbitControls, Environment } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import * as THREE from 'three';
import { useJarvisStore } from '@/store/jarvisStore';

// JARVIS Brain v6 - replicas the user-supplied brain-3d.html
// (Tripo replica) with exact same parameters:
// - Camera at (3, 0, 4)
// - Ice material with transmission 0.6, clearcoat 0.8, sheen 0.5
// - Inner glow with AdditiveBlending, opacity 0.15
// - 5 states with color palettes (idle, listening, thinking, speaking, error, sleep)
// - Thinking state: opacity 0.5-1.0, transmission 0.3-0.8, emissiveIntensity 0.3-0.8
// - 4-light setup: directional + fill + rim + bottom + top
// - Particles + thought bubbles
// Loads /models/brain.stl (302KB)   the user-supplied anatomical model.

const PALETTE = {
  idle:      { base: 0xe91e63, emissive: 0x4a0830, edge: 0xff4081 },
  listening: { base: 0xf06292, emissive: 0x4a1830, edge: 0xff80ab },
  thinking:  { base: 0xff1744, emissive: 0x801030, edge: 0xff4081 },
  speaking:  { base: 0xd81b60, emissive: 0x4a0830, edge: 0xff80ab },
  error:     { base: 0xff5252, emissive: 0x801010, edge: 0xff8a80 },
  sleep:     { base: 0xad1457, emissive: 0x3a1020, edge: 0xec407a },
};

function getPalette(state: string) {
  return PALETTE[state as keyof typeof PALETTE] || PALETTE.idle;
}

function BrainModel() {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const innerGlowRef = useRef<THREE.Mesh>(null);
  const scaleRef = useRef<number>(1);
  const { persona, activityState } = useJarvisStore();
  const stateRef = useRef({ persona, activityState });
  useEffect(() => { stateRef.current = { persona, activityState }; }, [persona, activityState]);

  // Load the user-supplied brain-simplified.stl (302KB anatomical model)
  const geometry = useLoader(STLLoader, '/models/brain.stl');

  // Compute bounding box, center the geometry, and derive a scale
  // that makes the brain fit a target size of ~1.6 units. This
  // works for any STL regardless of its native units.
  useEffect(() => {
    geometry.computeBoundingBox();
    const bb = geometry.boundingBox;
    if (!bb) return;
    const center = new THREE.Vector3();
    bb.getCenter(center);
    geometry.translate(-center.x, -center.y, -center.z);
    const size = new THREE.Vector3();
    bb.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z);
    const TARGET = 1.6;
    scaleRef.current = maxDim > 0 ? TARGET / maxDim : 1;
    // STL files exported from 3D tools (Blender, Tripo, etc.) often
    // come with Z as 'up' but the user's reference image has the
    // brain in classic anatomical 3/4 lateral view (frontal lobe
    // on the LEFT, cerebellum on the RIGHT). Tripo STL exports
    // with the longitudinal axis along Z, so we rotate by -90deg
    // around X to put it in the expected anatomical pose, then
    // apply a 25deg yaw for the 3/4 view.
    geometry.rotateX(-Math.PI / 2);
    geometry.computeBoundingBox();
    geometry.computeVertexNormals();
  }, [geometry]);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const t = clock.getElapsedTime();
    const { persona: p, activityState: st } = stateRef.current;
    const stName = typeof st === 'string' ? st : 'idle';
    const palette = getPalette(stName);

    // Fixed anatomical 3/4 view (frontal lobe left, cerebellum
    // right) with a slow breath-like sway. The user explicitly
    // said: 'así se debería ver' pointing at a static 3/4 lateral
    // pose. No more spin.
    groupRef.current.rotation.y = Math.PI * 0.18 + Math.sin(t * 0.3) * 0.04;
    groupRef.current.rotation.x = 0.0;
    groupRef.current.rotation.z = Math.sin(t * 0.4) * 0.02;
    groupRef.current.position.y = Math.sin(t * 0.5) * 0.04;

    if (meshRef.current) {
      const mat = meshRef.current.material as THREE.MeshPhysicalMaterial;
      if (mat) {
        mat.color.setHex(palette.base);
        mat.emissive.setHex(palette.emissive);

        // Thinking: blink transmission + emissiveIntensity
        if (stName === 'thinking') {
          const blink = (Math.sin(t * 4) + 1) / 2;
          mat.transmission = 0.3 + blink * 0.5;
          mat.emissiveIntensity = 0.3 + blink * 0.5;
          mat.opacity = 0.5 + blink * 0.5;
          mat.transparent = true;
        } else {
          mat.transmission = 0.6;
          mat.emissiveIntensity = 0.3;
          mat.opacity = 1.0;
          mat.transparent = false;
        }
      }
    }

    if (innerGlowRef.current) {
      const mat = innerGlowRef.current.material as THREE.MeshBasicMaterial;
      if (mat) {
        mat.opacity = stName === 'thinking'
          ? 0.1 + (Math.sin(t * 4) + 1) * 0.2
          : 0.15 + Math.sin(t * 0.8) * 0.05;
      }
    }
  });

  return (
    <group ref={groupRef} scale={scaleRef.current} position={[0, 0, 0]}>
      {/* Main brain mesh - ice material */}
      <mesh ref={meshRef} castShadow receiveShadow geometry={geometry}>
        <meshPhysicalMaterial
          color={0xe91e63}
          emissive={0x4a0830}
          emissiveIntensity={0.3}
          metalness={0}
          roughness={0.25}
          transmission={0.6}
          thickness={1.2}
          ior={1.45}
          clearcoat={0.8}
          clearcoatRoughness={0.1}
          sheen={0.5}
          sheenColor={0xff80ab}
          side={THREE.DoubleSide}
        />
      </mesh>
      {/* Inner glow - additive blending */}
      <mesh ref={innerGlowRef} scale={0.95} geometry={geometry}>
        <meshBasicMaterial
          color={0xff69b4}
          transparent
          opacity={0.15}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

function ParticleField() {
  const pointsRef = useRef<THREE.Points>(null);
  const count = 32;
  const palette = [0xff69b4, 0x40e0d0, 0xffffff, 0xec4899, 0x7c3aed];

  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 1.5 + Math.random() * 2;
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);
      const c = new THREE.Color(palette[Math.floor(Math.random() * palette.length)]);
      colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
    }
    return { positions, colors };
  }, []);

  useFrame(({ clock }) => {
    if (!pointsRef.current) return;
    pointsRef.current.rotation.y = clock.getElapsedTime() * 0.1;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
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
  );
}

function StageLights() {
  // 4-light setup matching brain-3d.html
  return (
    <>
      <ambientLight intensity={0.3} />
      <directionalLight position={[5, 5, 5]} intensity={0.6} castShadow />
      <directionalLight position={[-3, 2, -2]} intensity={0.4} color={0x40e0d0} />
      <pointLight position={[0, -3, 4]} intensity={0.5} color={0xff69b4} />
      <pointLight position={[0, 2, 0]} intensity={0.3} color={0x40e0d0} />
    </>
  );
}

export default function BrainBackground() {
  return (
    <div className="fixed inset-0 z-0">
      <Canvas
        camera={{ position: [3, 0, 4], fov: 50, near: 0.1, far: 100 }}
        gl={{
          antialias: true,
          alpha: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.0,
        }}
        shadows
        dpr={[1, 2]}
      >
        <color attach="background" args={["#0a0a0f"]} />
        <fog attach="fog" args={["#0a0a0f", 6, 20]} />
        <OrbitControls
          enableDamping
          dampingFactor={0.05}
          minDistance={1.5}
          maxDistance={8}
          target={[0, 0, 0]}
        />
        <Suspense fallback={null}>
          <StageLights />
          <BrainModel />
          <ParticleField />
        </Suspense>
        <EffectComposer>
          <Bloom intensity={0.6} luminanceThreshold={0.2} luminanceSmoothing={0.9} />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
