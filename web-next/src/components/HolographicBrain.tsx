'use client';

import { useRef, useMemo, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useThree, useLoader } from '@react-three/fiber';
import { useJarvisStore } from '@/store/jarvisStore';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { OrbitControls } from '@react-three/drei';

/* ────────────────────────────────────────────────────────────
   HOLOGRAPHIC BRAIN — Tripo3D Luminescent Brain (rosado)
   Integra TODO el filtro del brain-3d.html con animación
   reactiva al activityState del store.

   Filtro (color 0xd65e8e — +45% rosa sobre el original):
   - Outer: transmission 0.6, clearcoat 0.8, sheen 0.5 rosa
   - Inner: teal con emissive magenta
   - Glow shell: rosa aditivo
   - 6 luces: ambient + key + 2 fill (rosa/teal) + 2 point (bottom/top)
   - RoomEnvironment IBL (necesario para clearcoat)

   Animación por estado:
   - idle:      rotación lenta + sheen hue shift
   - listening: pulse suave del glow
   - thinking:  PARPADEO (opacity/transmission/emissive oscilan 3Hz)
   - speaking:  pulso más fuerte del glow + bottom light
   - error:     parpadeo rápido rojo
   - sleep:     casi estático, brillo bajo
   ──────────────────────────────────────────────────────────── */

// Singleton cache (parse STL once, reuse across re-mounts)
let _cachedGeometry: THREE.BufferGeometry | null = null;
let _cachedScale = 1;

/* ── RoomEnvironment IBL (preload once) ────────────────── */
function SceneEnvironment() {
  const { gl, scene } = useThree();
  useEffect(() => {
    let cancelled = false;
    let cleanup: (() => void) | undefined;

    (async () => {
      const { RoomEnvironment } = await import('three/examples/jsm/environments/RoomEnvironment.js');
      if (cancelled) return;
      const pmrem = new THREE.PMREMGenerator(gl);
      const envMap = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      scene.environment = envMap;
      (scene as any).environmentIntensity = 0.5;
      cleanup = () => {
        envMap.dispose();
        pmrem.dispose();
        scene.environment = null;
      };
    })();

    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, [gl, scene]);

  return null;
}

/* ── Brain model with reactive animation ───────────────── */
function BrainModel({ activityState }: { activityState: string }) {
  const groupRef = useRef<THREE.Group>(null);
  const outerMatRef = useRef<THREE.MeshPhysicalMaterial>(null);
  const innerMatRef = useRef<THREE.MeshPhysicalMaterial>(null);
  const glowMatRef = useRef<THREE.MeshBasicMaterial>(null);
  const bottomLightRef = useRef<THREE.PointLight>(null);

  const rawGeometry = useLoader(STLLoader, '/models/brain.stl');
  const { geometry, scale } = useMemo(() => {
    if (_cachedGeometry) {
      return { geometry: _cachedGeometry, scale: _cachedScale };
    }
    const g = rawGeometry.clone();
    g.center();
    g.computeVertexNormals();
    const pos = g.attributes.position as THREE.BufferAttribute;
    const box = new THREE.Box3().setFromBufferAttribute(pos);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const s = 2 / maxDim;
    _cachedGeometry = g;
    _cachedScale = s;
    return { geometry: g, scale: s };
  }, [rawGeometry]);

  // === MATERIALES — mismo filtro que brain-3d.html ===
  const outerMaterial = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        color: 0xd0e8e8,                // ice blue (del original)
        emissive: 0x2a1030,
        emissiveIntensity: 0.3,
        metalness: 0.0,
        roughness: 0.25,
        transmission: 0.6,              // 60% translúcido
        transparent: true,
        thickness: 1.2,
        ior: 1.45,
        clearcoat: 0.8,
        clearcoatRoughness: 0.1,
        sheen: 0.5,
        sheenColor: new THREE.Color(0xff69b4),
        sheenRoughness: 0.5,
        specularIntensity: 1.0,
        specularColor: 0xffffff,
        side: THREE.DoubleSide,
        flatShading: true,
      }),
    []
  );

  const innerMaterial = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        color: 0x40e0d0,                // teal (del original)
        emissive: 0xff1493,
        emissiveIntensity: 0.4,
        metalness: 0.0,
        roughness: 0.4,
        transparent: true,
        opacity: 0.15,
        side: THREE.BackSide,
        flatShading: true,
      }),
    []
  );

  // Glow aditivo para estado "thinking" (igual al brain-3d.html thinkMat)
  const glowMaterial = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: 0xff69b4,
        transparent: true,
        opacity: 0.0,                     // arranca apagado, sube en thinking
        side: THREE.FrontSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    []
  );

  // Dispose on unmount
  useEffect(() => {
    return () => {
      outerMaterial.dispose();
      innerMaterial.dispose();
      glowMaterial.dispose();
    };
  }, [outerMaterial, innerMaterial, glowMaterial]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    if (groupRef.current) {
      // === ROTACIÓN BASE (de brain-3d.html) ===
      groupRef.current.rotation.x = -Math.PI / 2 + Math.sin(t * 0.15) * 0.05;
      groupRef.current.rotation.z = Math.PI / 3.5 + Math.cos(t * 0.1) * 0.03;
    }

    const outer = outerMatRef.current;
    const inner = innerMatRef.current;
    const glow = glowMatRef.current;
    const bot = bottomLightRef.current;

    if (!outer || !inner || !glow || !bot) return;

    // === ANIMACIÓN POR ESTADO ===
    switch (activityState) {
      case 'thinking': {
        // PARPADEO del brain-3d.html: blink a 3Hz
        const blink = (Math.sin(t * 3) + 1) / 2;
        outer.opacity = 0.5 + blink * 0.5;
        outer.transmission = 0.3 + blink * 0.5;
        outer.emissiveIntensity = 0.3 + blink * 0.5;
        glow.opacity = 0.1 + blink * 0.4;
        bot.intensity = 0.5 + blink * 0.5;
        break;
      }
      case 'speaking': {
        // Pulso del glow + bottom light
        const pulse = (Math.sin(t * 2) + 1) / 2;
        outer.opacity = 0.85;
        outer.transmission = 0.6;
        outer.emissiveIntensity = 0.4;
        glow.opacity = 0.2 + pulse * 0.3;
        bot.intensity = 0.5 + pulse * 0.4;
        break;
      }
      case 'listening': {
        // Pulse suave
        const pulse = (Math.sin(t * 1.5) + 1) / 2;
        outer.opacity = 0.85;
        outer.transmission = 0.6;
        outer.emissiveIntensity = 0.3 + pulse * 0.2;
        glow.opacity = 0.15 + pulse * 0.1;
        bot.intensity = 0.4 + pulse * 0.2;
        break;
      }
      case 'error': {
        // Parpadeo rápido rojo
        const blink = (Math.sin(t * 6) + 1) / 2;
        outer.emissive.setHex(0xff0033);
        outer.emissiveIntensity = 0.3 + blink * 0.7;
        outer.opacity = 0.7;
        outer.transmission = 0.5;
        glow.color.setHex(0xff0044);
        glow.opacity = 0.2 + blink * 0.5;
        bot.color.setHex(0xff0044);
        bot.intensity = 0.5 + blink * 0.5;
        break;
      }
      case 'sleep': {
        // Casi estático, brillo bajo
        outer.opacity = 0.6;
        outer.transmission = 0.4;
        outer.emissiveIntensity = 0.15;
        glow.opacity = 0.05;
        bot.intensity = 0.2;
        break;
      }
      case 'idle':
      default: {
        // IDLE: glow oscila suave, sheen hue shift
        outer.opacity = 0.85;
        outer.transmission = 0.6;
        outer.emissive.setHex(0x2a1030);
        outer.emissiveIntensity = 0.3;
        glow.color.setHex(0xff69b4);
        glow.opacity = 0.15 + Math.sin(t * 0.8) * 0.05;
        bot.color.setHex(0xff1493);
        bot.intensity = 0.5 + Math.sin(t * 1.2) * 0.2;
        // Sheen hue shift sutil (del original)
        outer.sheenColor.setHSL(0.92 + Math.sin(t * 0.3) * 0.02, 0.7, 0.6);
        break;
      }
    }
  });

  return (
    <>
      {/* Bottom light dentro del BrainModel para tener la ref accesible */}
      <pointLight
        ref={bottomLightRef}
        position={[0, -2, 0]}
        intensity={0.5}
        distance={10}
        color={0xff1493}
      />
      <group ref={groupRef} scale={scale}>
        {/* Outer translucent rose shell */}
        <mesh
          geometry={geometry}
          material={outerMaterial}
          ref={(m) => { if (m) (outerMatRef as any).current = (m as THREE.Mesh).material; }}
        />
        {/* Inner teal backlight (mismo material del original) */}
        <mesh
          geometry={geometry}
          material={innerMaterial}
          scale={0.97}
          ref={(m) => { if (m) (innerMatRef as any).current = (m as THREE.Mesh).material; }}
        />
        {/* Outer glow shell (para thinking) */}
        <mesh
          geometry={geometry}
          material={glowMaterial}
          scale={1.02}
          ref={(m) => { if (m) (glowMatRef as any).current = (m as THREE.Mesh).material; }}
        />
      </group>
    </>
  );
}

/* ── Fallback mientras carga el STL ───────────────────── */
function Fallback() {
  return (
    <mesh>
      <icosahedronGeometry args={[0.7, 1]} />
      <meshBasicMaterial color="#ff69b4" wireframe />
    </mesh>
  );
}

/* ── Componente principal ─────────────────────────────── */
export default function HolographicBrain() {
  const { activityState } = useJarvisStore();
  const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

  return (
    <div className="fixed inset-0 z-0" style={{ background: '#000000' }}>
      <Canvas
        camera={{ position: [0, 0.5, 2.8], fov: 45, near: 0.1, far: 1000 }}
        dpr={1.5}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance',
          stencil: false,
        }}
        onCreated={({ gl }) => {
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.0;
        }}
      >
        <color attach="background" args={['#000000']} />

        {/* IBL via RoomEnvironment (necesario para clearcoat) */}
        <SceneEnvironment />

        {/* === 5 luces fijas del brain-3d.html (la 6ta, la bottom, está dentro de BrainModel) === */}
        <ambientLight intensity={0.5} color={0x404040} />
        <directionalLight position={[5, 5, 5]} intensity={1.2} color={0xffffff} />
        <directionalLight position={[-3, 2, -2]} intensity={0.6} color={0xff69b4} />
        <directionalLight position={[0, -3, 4]} intensity={0.8} color={0x40e0d0} />
        <pointLight position={[0, 3, 0]} intensity={0.4} distance={8} color={0xff69b4} />

        <Suspense fallback={<Fallback />}>
          <BrainModel activityState={activityState} />
        </Suspense>

        <OrbitControls 
          enableDamping 
          dampingFactor={0.05} 
          minDistance={1.5} 
          maxDistance={8} 
          target={[0, 0, 0]} 
        />
      </Canvas>
    </div>
  );
}
