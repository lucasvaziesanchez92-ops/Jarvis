'use client';

import { useRef, useEffect } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import * as THREE from 'three';
import { useJarvisStore } from '@/store/jarvisStore';

// JARVIS Brain 3D - replica EXACTA del brain-3d.html que el
// usuario suministro como referencia. Material: HIELO AZUL-BLANCO
// (0xd0e8e8) con sheen rosa, NO rosa plano. El usuario reporto
// 'esta peor' y 'demasiado rosado' porque mi fix anterior pinto
// todo de rosa. La referencia es translucida tipo hielo con glow
// sutil. flatShading=true para look low-poly facetado.
//
// Animacion: sutil respiracion. rotation.x = -PI/2 (acostado),
// rotation.z = PI/3.5 (vista lateral anatomica).

const ICE = 0xd0e8e8;
const EMISSIVE = 0x2a1030;
const SHEEN = 0xff69b4;
const GLOW = 0xff69b4;
const BOTTOM_LIGHT_COLOR = 0xff1493;
const FILL_LIGHT_COLOR = 0x40e0d0;

function BrainModel() {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const matRef = useRef<THREE.MeshPhysicalMaterial>(null);
  const glowMatRef = useRef<THREE.MeshBasicMaterial>(null);
  const bottomLightRef = useRef<THREE.PointLight>(null);

  const geometry = useLoader(STLLoader, '/models/brain.stl');

  const { activityState } = useJarvisStore();
  const stateRef = useRef(activityState);
  useEffect(() => { stateRef.current = activityState; }, [activityState]);

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
    const scale = maxDim > 0 ? 1.6 / maxDim : 1;
    if (groupRef.current) groupRef.current.scale.setScalar(scale);
    geometry.computeVertexNormals();
  }, [geometry]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const stName = stateRef.current || 'idle';

    // Brain body: subtle breathing (matches the reference exactly)
    if (groupRef.current) {
      groupRef.current.rotation.x = (-Math.PI / 2) + Math.sin(t * 0.15) * 0.05;
      groupRef.current.rotation.z = (Math.PI / 3.5) + Math.cos(t * 0.1) * 0.03;
      groupRef.current.rotation.y = Math.sin(t * 0.12) * 0.02;
    }

    // Glow shell pulse
    if (glowMatRef.current) {
      glowMatRef.current.opacity = 0.15 + Math.sin(t * 0.8) * 0.05;
    }

    // Bottom light pulse
    if (bottomLightRef.current) {
      bottomLightRef.current.intensity = 0.5 + Math.sin(t * 1.2) * 0.2;
    }

    // Sheen chromatic shift (subtle pink/magenta cycling)
    if (matRef.current && matRef.current.sheenColor) {
      const hue = 0.92 + Math.sin(t * 0.3) * 0.02;
      matRef.current.sheenColor.setHSL(hue, 0.7, 0.6);
    }

    // Activity feedback: idle = normal, thinking = transmission blink,
    // speaking = slight emissive bump, listening = stable.
    if (matRef.current) {
      if (stName === 'thinking') {
        const blink = (Math.sin(t * 4) + 1) / 2;
        matRef.current.transmission = 0.3 + blink * 0.5;
        matRef.current.emissiveIntensity = 0.2 + blink * 0.5;
        matRef.current.opacity = 0.5 + blink * 0.5;
        matRef.current.transparent = true;
      } else if (stName === 'speaking') {
        matRef.current.transmission = 0.6;
        matRef.current.emissiveIntensity = 0.4;
        matRef.current.opacity = 1.0;
        matRef.current.transparent = false;
      } else {
        matRef.current.transmission = 0.6;
        matRef.current.emissiveIntensity = 0.3;
        matRef.current.opacity = 1.0;
        matRef.current.transparent = false;
      }
    }
  });

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      <mesh ref={meshRef} geometry={geometry} castShadow receiveShadow>
        <meshPhysicalMaterial
          ref={matRef}
          color={ICE}
          emissive={EMISSIVE}
          emissiveIntensity={0.3}
          metalness={0}
          roughness={0.25}
          transmission={0.6}
          thickness={1.2}
          ior={1.45}
          clearcoat={0.8}
          clearcoatRoughness={0.1}
          sheen={0.5}
          sheenColor={SHEEN}
          sheenRoughness={0.5}
          specularIntensity={1.0}
          specularColor={0xffffff}
          side={THREE.DoubleSide}
          flatShading={true}
        />
      </mesh>
      {/* Glow shell - additive pink (matches reference) */}
      <mesh ref={glowRef} scale={0.95} geometry={geometry}>
        <meshBasicMaterial
          ref={glowMatRef}
          color={GLOW}
          transparent
          opacity={0.15}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
      {/* Pulsing bottom light */}
      <pointLight
        ref={bottomLightRef}
        position={[0, -2, 0]}
        intensity={0.5}
        color={BOTTOM_LIGHT_COLOR}
      />
    </group>
  );
}

export default function BrainBackground() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none">
      <Canvas
        camera={{ position: [0, 0, 3.2], fov: 45, near: 0.1, far: 50 }}
        gl={{
          antialias: true,
          alpha: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.0,
        }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.5} color={0x404040} />
        <directionalLight position={[5, 5, 5]} intensity={1.2} color={0xffffff} castShadow />
        <directionalLight position={[-3, 2, -2]} intensity={0.6} color={FILL_LIGHT_COLOR} />
        <directionalLight position={[0, -3, 4]} intensity={0.8} color={0x40e0d0} />
        <pointLight position={[0, 3, 0]} intensity={0.4} color={SHEEN} />
        <BrainModel />
        <OrbitControls
          enableDamping
          dampingFactor={0.05}
          minDistance={1.5}
          maxDistance={8}
          target={[0, 0, 0]}
          enablePan={false}
        />
      </Canvas>
    </div>
  );
}
