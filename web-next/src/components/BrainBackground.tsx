'use client';

import { useRef, useMemo, useState, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';
import { useJarvisStore } from '@/store/jarvisStore';

// JARVIS Brain v3 - uses the user-supplied brain.glb model
// Restored after the binary-corruption incident. UTF-8 clean.

const STATE_META = {
  idle:      { grooveIntensity: 0.55, rimIntensity: 1.4 },
  listening: { grooveIntensity: 0.70, rimIntensity: 1.8 },
  thinking:  { grooveIntensity: 0.85, rimIntensity: 2.0 },
  speaking:  { grooveIntensity: 0.50, rimIntensity: 1.5 },
  error:     { grooveIntensity: 1.00, rimIntensity: 2.2 },
  sleep:     { grooveIntensity: 0.30, rimIntensity: 0.8 },
};

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
    idle:      { base: 0xe8e8f0, emissive: 0x202028, edge: 0x4060c0 },
    listening: { base: 0xd0d8e8, emissive: 0x182030, edge: 0x4080ff },
    thinking:  { base: 0xc8d0e0, emissive: 0x102040, edge: 0x6060ff },
    speaking:  { base: 0xd8d8e8, emissive: 0x182838, edge: 0x4080d0 },
    error:     { base: 0xffa0a0, emissive: 0x401010, edge: 0xff4444 },
    sleep:     { base: 0x808890, emissive: 0x101820, edge: 0x4060a0 },
  },
  creativa: {
    idle:      { base: 0xfde2ff, emissive: 0x401040, edge: 0xff40ff },
    listening: { base: 0xffe2c8, emissive: 0x502010, edge: 0xff8040 },
    thinking:  { base: 0xe2d2ff, emissive: 0x301050, edge: 0xa040ff },
    speaking:  { base: 0xffd2e8, emissive: 0x501030, edge: 0xff60c0 },
    error:     { base: 0xffa0a0, emissive: 0x401010, edge: 0xff4444 },
    sleep:     { base: 0xa0a0b0, emissive: 0x201020, edge: 0x8060a0 },
  },
  soporte: {
    idle:      { base: 0xe0f0e8, emissive: 0x102818, edge: 0x40c080 },
    listening: { base: 0xd0e8e0, emissive: 0x102818, edge: 0x40a070 },
    thinking:  { base: 0xd8e8d8, emissive: 0x183020, edge: 0x60a080 },
    speaking:  { base: 0xe0f0e0, emissive: 0x102820, edge: 0x40a080 },
    error:     { base: 0xffa0a0, emissive: 0x401010, edge: 0xff4444 },
    sleep:     { base: 0x90a090, emissive: 0x102010, edge: 0x608068 },
  },
};

function getPersonalityTheme(persona: string, state: string) {
  const p = PERSONALITY_THEMES[persona as keyof typeof PERSONALITY_THEMES]
    || PERSONALITY_THEMES.profesional;
  return p[state as keyof typeof p] || p.idle;
}

function BrainModel() {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const { persona, activityState } = useJarvisStore();
  const stateRef = useRef({ persona, activityState });
  useEffect(() => { stateRef.current = { persona, activityState }; }, [persona, activityState]);

  // Load the user-supplied brain.glb
  const gltf = useGLTF('/models/brain.glb');
  const scene = useMemo(() => {
    const cloned = gltf.scene.clone(true);
    cloned.traverse((obj) => {
      if ((obj as THREE.Mesh).isMesh) {
        const mesh = obj as THREE.Mesh;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        // Apply a material that we can recolor per personality/state
        if (!mesh.material || (mesh.material as any).isShared) {
          mesh.material = new THREE.MeshPhysicalMaterial({
            color: 0xd0e8e8,
            emissive: 0x2a1030,
            emissiveIntensity: 0.5,
            roughness: 0.15,
            metalness: 0.2,
            transmission: 0.6,
            thickness: 0.5,
            ior: 1.5,
            clearcoat: 0.5,
            clearcoatRoughness: 0.2,
          });
        }
      }
    });
    return cloned;
  }, [gltf]);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const t = clock.getElapsedTime();
    const { persona: p, activityState: st } = stateRef.current;
    const pName = typeof p === 'string' ? p : (p && (p as any).name) || 'profesional';
    const stName = typeof st === 'string' ? st : 'idle';
    const theme = getPersonalityTheme(pName, stName);
    const meta = STATE_META[stName as keyof typeof STATE_META] || STATE_META.idle;

    // Slow rotation
    groupRef.current.rotation.y = t * 0.2;

    // Recolor the materials in the scene
    scene.traverse((obj) => {
      if ((obj as THREE.Mesh).isMesh) {
        const mat = (obj as THREE.Mesh).material as THREE.MeshPhysicalMaterial;
        if (mat) {
          mat.color.setHex(theme.base);
          mat.emissive.setHex(theme.emissive);
          mat.emissiveIntensity = 0.4 + Math.sin(t * 1.2) * 0.2 * meta.grooveIntensity;
        }
      }
    });
  });

  return (
    <group ref={groupRef} scale={0.8} position={[0, 0, 0]}>
      <primitive object={scene} ref={meshRef} />
    </group>
  );
}

function ParticleField() {
  const pointsRef = useRef<THREE.Points>(null);
  const count = 80;

  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 4.5 + Math.random() * 1.5;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, []);

  useFrame(({ clock }) => {
    if (!pointsRef.current) return;
    pointsRef.current.rotation.y = clock.getElapsedTime() * 0.03;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color={0x40e0d0} size={0.02} transparent opacity={0.4} />
    </points>
  );
}

function ThoughtBubbles() {
  // Disabled — was occluding the brain. Kept empty for compatibility.
  return null;
}

function StageLights() {
  return (
    <>
      <ambientLight intensity={0.3} />
      <directionalLight position={[5, 5, 5]} intensity={0.6} castShadow />
      <directionalLight position={[-5, 3, -5]} intensity={0.4} color={0x4080ff} />
      <pointLight position={[0, 0, 3]} intensity={0.5} color={0x40e0d0} />
    </>
  );
}

export default function BrainBackground() {
  return (
    <div className="fixed inset-0 z-0">
      <Canvas
        camera={{ position: [2, 0, 3], fov: 60, near: 0.1, far: 100 }}
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
          <ThoughtBubbles />
        </Suspense>
        <EffectComposer>
          <Bloom intensity={0.6} luminanceThreshold={0.2} luminanceSmoothing={0.9} />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
