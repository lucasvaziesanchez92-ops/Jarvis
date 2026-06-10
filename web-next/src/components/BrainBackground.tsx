'use client';

import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';

// Brain 3D using the user's GLB model (1.6MB) which has materials
// already built in. The user said 'el cerebro esta mal' so we
// load the original high-quality model and apply a fixed anatomical
// pose. We force every material to the JARVIS pink/magenta color
// so the brain matches the UI theme regardless of what colors
// the GLB shipped with.

const PINK = '#e91e63';
const PINK_BRIGHT = '#ff80ab';

function BrainModel() {
  const groupRef = useRef<THREE.Group>(null);
  const gltf = useGLTF('/models/brain.glb');

  // Traverse and recolor every material to the JARVIS pink
  // palette. The original GLB ships with reddish materials which
  // is what the user reported ('esta peor', 'no me gusto').
  gltf.scene.traverse((child: THREE.Object3D) => {
    if ((child as THREE.Mesh).isMesh) {
      const mesh = child as THREE.Mesh;
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      mats.forEach((m) => {
        if (!m) return;
        if ((m as THREE.MeshStandardMaterial).color) {
          (m as THREE.MeshStandardMaterial).color = new THREE.Color(PINK);
        }
        if ((m as THREE.MeshStandardMaterial).emissive) {
          (m as THREE.MeshStandardMaterial).emissive = new THREE.Color(PINK_BRIGHT);
          (m as THREE.MeshStandardMaterial).emissiveIntensity = 0.25;
        }
        if ((m as THREE.MeshStandardMaterial).roughness !== undefined) {
          (m as THREE.MeshStandardMaterial).roughness = 0.4;
        }
        if ((m as THREE.MeshStandardMaterial).metalness !== undefined) {
          (m as THREE.MeshStandardMaterial).metalness = 0.0;
        }
      });
      mesh.castShadow = false;
      mesh.receiveShadow = false;
    }
  });

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const t = clock.getElapsedTime();
    // Fixed 3/4 anatomical pose. Subtle breath-like sway, no spin.
    groupRef.current.rotation.y = -0.3 + Math.sin(t * 0.3) * 0.04;
    groupRef.current.rotation.x = 0.0 + Math.sin(t * 0.25) * 0.02;
  });

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      <primitive object={gltf.scene} scale={2.2} position={[0, 0, 0]} />
    </group>
  );
}

useGLTF.preload('/models/brain.glb');

export default function BrainBackground() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none">
      <Canvas
        camera={{ position: [0, 0.3, 4.5], fov: 35, near: 0.1, far: 50 }}
        gl={{
          antialias: true,
          alpha: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.0,
        }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} color={'#ffffff'} />
        <directionalLight position={[-3, 3, -2]} intensity={0.5} color={PINK_BRIGHT} />
        <pointLight position={[0, 2, 3]} intensity={0.5} color={PINK_BRIGHT} />
        <pointLight position={[0, -2, 1]} intensity={0.3} color={PINK} />
        <BrainModel />
      </Canvas>
    </div>
  );
}
