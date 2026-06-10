'use client';

import { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import * as THREE from 'three';

// Minimal brain 3D: just the user-supplied STL, rotated to the
// anatomical 3/4 lateral view (frontal lobe on the left,
// cerebellum on the right — matching the user's reference image).
// No particles, no bloom, no postprocessing, no animation. The
// user said 'el cerebro esta mal colocado' so the only thing we
// show is the brain in the right pose with the right color.

const PINK = 0xe91e63;
const PINK_SHEEN = 0xff80ab;

function BrainModel() {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const scaleRef = useRef<number>(1);

  const geometry = useLoader(STLLoader, '/models/brain.stl');

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
    scaleRef.current = maxDim > 0 ? 1.6 / maxDim : 1;
    // STL exports often come with the longitudinal axis along Z.
    // We rotate it -90deg around X so the brain is in the classic
    // anatomical pose (face pointing forward, not 'standing up
    // vertically' as the user reported).
    geometry.rotateX(-Math.PI / 2);
    geometry.computeBoundingBox();
    geometry.computeVertexNormals();
  }, [geometry]);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const t = clock.getElapsedTime();
    // Gentle 3/4 lateral pose, no full spin. The user explicitly
    // said the brain should look like the reference (3/4 static).
    groupRef.current.rotation.y = Math.PI * 0.18 + Math.sin(t * 0.3) * 0.04;
    groupRef.current.rotation.x = 0;
    groupRef.current.rotation.z = 0;
  });

  return (
    <group ref={groupRef} scale={scaleRef.current} position={[0, 0, 0]}>
      <mesh ref={meshRef} geometry={geometry}>
        <meshPhysicalMaterial
          color={PINK}
          emissive={PINK}
          emissiveIntensity={0.15}
          metalness={0}
          roughness={0.35}
          clearcoat={0.6}
          clearcoatRoughness={0.2}
          sheen={0.5}
          sheenColor={PINK_SHEEN}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
}

export default function BrainBackground() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none">
      <Canvas
        camera={{ position: [0, 0.2, 3.2], fov: 45, near: 0.1, far: 50 }}
        gl={{
          antialias: true,
          alpha: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.2,
        }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.55} />
        <directionalLight position={[5, 5, 5]} intensity={0.7} color={0xffffff} />
        <directionalLight position={[-3, 2, -2]} intensity={0.4} color={PINK_SHEEN} />
        <pointLight position={[0, 2, 0]} intensity={0.4} color={0xff80ab} />
        <pointLight position={[0, -2, 0]} intensity={0.3} color={0xe91e63} />
        <BrainModel />
      </Canvas>
    </div>
  );
}
