'use client';

import { useRef, useMemo, useState, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import * as THREE from 'three';
import { useJarvisStore } from '@/store/jarvisStore';

// JARVIS Brain v2 - Ice Material + Particles + States
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

function IceBrain() {
  const groupRef = useRef<THREE.Group>(null);
  const mainMeshRef = useRef<THREE.Mesh>(null);
  const innerMeshRef = useRef<THREE.Mesh>(null);
  const glowMeshRef = useRef<THREE.Mesh>(null);

  const { persona, activityState } = useJarvisStore();
  const personaStateRef = useRef({ persona, activityState });
  useEffect(() => { personaStateRef.current = { persona, activityState }; }, [persona, activityState]);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const t = clock.getElapsedTime();
    const { persona: p, activityState: st } = personaStateRef.current;
    const pName = typeof p === 'string' ? p : (p && (p as any).name) || 'profesional';
    const stName = typeof st === 'string' ? st : 'idle';
    const theme = getPersonalityTheme(pName, stName);
    const meta = STATE_META[stName as keyof typeof STATE_META] || STATE_META.idle;

    groupRef.current.rotation.y = t * 0.15;

    if (mainMeshRef.current) {
      const mat = mainMeshRef.current.material as THREE.MeshPhysicalMaterial;
      if (mat) {
        mat.color.setHex(theme.base);
        mat.emissive.setHex(theme.emissive);
        mat.emissiveIntensity = 0.5 + Math.sin(t * 1.2) * 0.2 * meta.grooveIntensity;
      }
    }
    if (innerMeshRef.current) {
      const mat = innerMeshRef.current.material as THREE.MeshStandardMaterial;
      if (mat) {
        mat.color.setHex(theme.base);
        mat.emissive.setHex(theme.edge);
        mat.emissiveIntensity = 0.3 + Math.sin(t * 2) * 0.15 * meta.rimIntensity;
      }
    }
    if (glowMeshRef.current) {
      const mat = glowMeshRef.current.material as THREE.MeshBasicMaterial;
      if (mat) {
        mat.color.setHex(theme.edge);
        mat.opacity = 0.3 + Math.sin(t * 1.5) * 0.1;
      }
    }
  });

  return (
    <group ref={groupRef}>
      <mesh ref={mainMeshRef} castShadow receiveShadow>
        <icosahedronGeometry args={[1.2, 4]} />
        <meshPhysicalMaterial
          color={0xd0e8e8}
          emissive={0x2a1030}
          emissiveIntensity={0.5}
          roughness={0.15}
          metalness={0.2}
          transmission={0.6}
          thickness={0.5}
          ior={1.5}
          clearcoat={0.5}
          clearcoatRoughness={0.2}
        />
      </mesh>
      <mesh ref={innerMeshRef}>
        <icosahedronGeometry args={[0.9, 2]} />
        <meshStandardMaterial
          color={0x40e0d0}
          emissive={0x40e0d0}
          emissiveIntensity={0.3}
          transparent
          opacity={0.6}
        />
      </mesh>
      <mesh ref={glowMeshRef} scale={1.5}>
        <icosahedronGeometry args={[1.2, 1]} />
        <meshBasicMaterial
          color={0x40e0d0}
          wireframe
          transparent
          opacity={0.3}
        />
      </mesh>
    </group>
  );
}

function ParticleField() {
  const pointsRef = useRef<THREE.Points>(null);
  const count = 200;

  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 2.5 + Math.random() * 1.5;
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
    pointsRef.current.rotation.y = clock.getElapsedTime() * 0.05;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color={0x40e0d0} size={0.03} transparent opacity={0.6} />
    </points>
  );
}

function ThoughtBubbles() {
  const groupRef = useRef<THREE.Group>(null);
  const count = 6;

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const t = clock.getElapsedTime();
    groupRef.current.children.forEach((bubble, i) => {
      const offset = (i / count) * Math.PI * 2;
      bubble.position.y = Math.sin(t * 0.5 + offset) * 0.3 + 1.5;
      bubble.position.x = Math.cos(t * 0.3 + offset) * 1.5;
      const scale = 0.05 + Math.abs(Math.sin(t + offset)) * 0.08;
      (bubble as THREE.Mesh).scale.setScalar(scale);
    });
  });

  return (
    <group ref={groupRef}>
      {Array.from({ length: count }).map((_, i) => (
        <mesh key={i}>
          <sphereGeometry args={[1, 8, 8]} />
          <meshBasicMaterial color={0x00d4ff} transparent opacity={0.4} />
        </mesh>
      ))}
    </group>
  );
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
        camera={{ position: [3, 0, 4], fov: 45, near: 0.1, far: 100 }}
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
          <IceBrain />
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
