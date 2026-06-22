'use client';

import { useRef, useMemo, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useThree, useLoader } from '@react-three/fiber';
import { useJarvisStore } from '@/store/jarvisStore';
import { PERSONALITY_THEMES } from '@/constants/colors';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { OrbitControls, Sparkles, Float } from '@react-three/drei';

/* ────────────────────────────────────────────────────────────
   HOLOGRAPHIC BRAIN — Rosa Holográfico Sólido (final)
   Sincronizado con test standalone brain-magenta-rosado.html.

   Filtro (color 0xe090b0 — rosa medio un poco oscuro):
   - Outer: transmission 0.1, clearcoat 0.8, sheen 0.8 rosa,
     opacity 1.0 (SÓLIDO)
   - Inner: rosa medio aditivo
   - Glow shell: rosa medio aditivo
   - RoomEnvironment IBL (necesario para clearcoat)

   Animación por estado:
   - idle:      rotación lenta + glow estable
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
      (scene as any).environmentIntensity = 0.7;  // ↑ subido de 0.5
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
function BrainModel({ activityState, isMobile, activePersonality }: { activityState: string, isMobile: boolean, activePersonality: string }) {
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
    g.scale(0.3, 0.3, 0.3); // Reduced from 0.6 to 0.3 for mobile
    const pos = g.attributes.position as THREE.BufferAttribute;
    const box = new THREE.Box3().setFromBufferAttribute(pos);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const s = 2 / maxDim;
    _cachedGeometry = g;
    _cachedScale = s;
    return { geometry: g, scale: s };
  }, [rawGeometry]);

  // === MATERIALES DINÁMICOS POR PERSONALIDAD ===
  const theme = PERSONALITY_THEMES[activePersonality] || PERSONALITY_THEMES.profesional;
  const baseColor = new THREE.Color(theme.hex);
  
  // Create slightly darker/brighter variants for emissive and sheen
  const emissiveColor = baseColor.clone().multiplyScalar(0.7);
  const glowColor = baseColor.clone().multiplyScalar(1.2);

  const outerMaterial = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        color: baseColor,
        emissive: emissiveColor,
        emissiveIntensity: 0.65,
        metalness: 0.0,
        roughness: 0.28,
        transmission: 0.1,              // muy poco translúcido (sólido)
        transparent: true,
        opacity: 1.0,
        thickness: 1.8,
        ior: 1.45,
        clearcoat: 0.8,
        clearcoatRoughness: 0.1,
        sheen: 0.8,
        sheenColor: glowColor,
        sheenRoughness: 0.4,
        specularIntensity: 1.3,
        specularColor: 0xffffff,
        side: THREE.DoubleSide,
        flatShading: true,
      }),
    [baseColor.getHex()]
  );

  const innerMaterial = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: glowColor,
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending,
        side: THREE.BackSide,
      }),
    [glowColor.getHex()]
  );

  const glowMaterial = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: glowColor,
        transparent: true,
        opacity: 0.15,
        blending: THREE.AdditiveBlending,
        side: THREE.FrontSide,
      }),
    [glowColor.getHex()]
  );

  // Dispose on unmount
  useEffect(() => {
    return () => {
      outerMaterial.dispose();
      innerMaterial.dispose();
      glowMaterial.dispose();
    };
  }, [outerMaterial, innerMaterial, glowMaterial]);

  const currentRotation = useRef({ x: -Math.PI / 2, z: Math.PI / 3.5 });

  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime();

    let rotationSpeed = 0.1;
    let targetScale = 1.0;

    if (activityState === 'thinking') {
      rotationSpeed = 0.5; // Spins much faster
      targetScale = 1.02; 
    } else if (activityState === 'speaking') {
      rotationSpeed = 0.25;
      // Pulse scale to speech
      targetScale = 1.0 + Math.abs(Math.sin(t * 8)) * 0.05; 
    } else if (activityState === 'listening') {
      rotationSpeed = 0.05; // Slow down when listening
      targetScale = 0.98;
    }

    if (groupRef.current) {
      // Rotate dynamically
      currentRotation.current.x += delta * (rotationSpeed * 0.5);
      currentRotation.current.z += delta * rotationSpeed;
      
      // Add a bit of natural bobbing
      groupRef.current.rotation.x = currentRotation.current.x + Math.sin(t * 0.5) * 0.05;
      groupRef.current.rotation.z = currentRotation.current.z + Math.cos(t * 0.5) * 0.05;

      // Smooth scale interpolation
      groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
    }

    const outer = outerMatRef.current;
    const inner = innerMatRef.current;
    const glow = glowMatRef.current;
    const bot = bottomLightRef.current;

    if (!outer || !inner || !glow || !bot) return;

    // === ANIMACIÓN POR ESTADO ===
    
    // Always apply the active personality colors (except in error state)
    if (activityState !== 'error') {
      outer.emissive.copy(emissiveColor);
      glow.color.copy(glowColor);
      bot.color.copy(baseColor);
      outer.sheenColor.copy(glowColor);
    }

    switch (activityState) {
      case 'thinking': {
        // Erratic heavy processing pulse
        const blink = (Math.sin(t * 15) + Math.sin(t * 10)) / 2;
        outer.opacity = 0.8 + blink * 0.2;
        outer.transmission = 0.05;
        outer.emissiveIntensity = 0.8 + blink * 0.4;
        glow.opacity = 0.3 + blink * 0.4;
        bot.intensity = 0.6 + blink * 0.5;
        break;
      }
      case 'speaking': {
        // Deep rhythmic pulse
        const pulse = (Math.sin(t * 8) + 1) / 2;
        outer.opacity = 1.0;
        outer.transmission = 0.1;
        outer.emissiveIntensity = 0.7 + pulse * 0.3;
        glow.opacity = 0.3 + pulse * 0.4;
        bot.intensity = 0.6 + pulse * 0.5;
        break;
      }
      case 'listening': {
        // Smooth alert glow
        const pulse = (Math.sin(t * 2) + 1) / 2;
        outer.opacity = 1.0;
        outer.transmission = 0.1;
        outer.emissiveIntensity = 0.5 + pulse * 0.2;
        glow.opacity = 0.2 + pulse * 0.1;
        bot.intensity = 0.4 + pulse * 0.2;
        break;
      }
      case 'error': {
        // Fast red flashing
        const blink = (Math.sin(t * 6) + 1) / 2;
        outer.emissive.setHex(0xff0033);
        outer.emissiveIntensity = 0.3 + blink * 0.7;
        outer.opacity = 0.85;
        outer.transmission = 0.1;
        glow.color.setHex(0xff0044);
        glow.opacity = 0.2 + blink * 0.5;
        bot.color.setHex(0xff0044);
        bot.intensity = 0.5 + blink * 0.5;
        break;
      }
      case 'sleep': {
        // Almost static, very dim
        outer.opacity = 0.85;
        outer.transmission = 0.08;
        outer.emissiveIntensity = 0.25;
        glow.opacity = 0.1;
        bot.intensity = 0.3;
        break;
      }
      case 'idle':
      default: {
        // IDLE: soft breathing
        outer.opacity = 1.0;
        outer.transmission = 0.1;
        outer.emissiveIntensity = 0.65;
        glow.opacity = 0.3 + Math.sin(t * 1.2) * 0.1;
        bot.intensity = 0.5 + Math.sin(t * 1.5) * 0.25;
        break;
      }
    }
  });

  return (
    <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.5}>
      {/* Bottom light dentro del BrainModel para tener la ref accesible */}
      <pointLight
        ref={bottomLightRef}
        position={[0, -2, 0]}
        intensity={0.3}
        distance={10}
        color={theme.hex}
      />
      <group ref={groupRef} scale={scale * (isMobile ? 0.55 : 0.85)}>
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
          scale={0.96}
          ref={(m) => { if (m) (innerMatRef as any).current = (m as THREE.Mesh).material; }}
        />
        {/* Outer glow shell (para thinking) */}
        <mesh
          geometry={geometry}
          material={glowMaterial}
          scale={1.03}
          ref={(m) => { if (m) (glowMatRef as any).current = (m as THREE.Mesh).material; }}
        />
        {/* Partículas cyan flotando dentro y alrededor */}
        <Sparkles count={isMobile ? 60 : 150} scale={2.5} size={isMobile ? 1.5 : 2.5} color="#00ffff" opacity={0.6} speed={0.5} noise={1} />
        {/* Partículas magenta sutiles */}
        <Sparkles count={isMobile ? 40 : 100} scale={2.2} size={isMobile ? 2 : 3} color={theme.hex} opacity={0.4} speed={0.3} noise={2} />
      </group>
    </Float>
  );
}

/* ── Fallback mientras carga el STL ───────────────────── */
function Fallback() {
  return (
    <mesh>
      <icosahedronGeometry args={[0.7, 1]} />
      <meshBasicMaterial color="#ffffff" wireframe />
    </mesh>
  );
}

/* ── Componente principal ─────────────────────────────── */
export default function HolographicBrain() {
  const { activityState, persona } = useJarvisStore();
  const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  const activePersonality = persona?.name || 'profesional';
  const theme = PERSONALITY_THEMES[activePersonality] || PERSONALITY_THEMES.profesional;

  return (
    <div className="fixed inset-0 z-0 pointer-events-none">
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
        {/* IBL via RoomEnvironment (necesario para clearcoat) */}
        <SceneEnvironment />

        {/* === 5 luces fijas del brain-3d.html (la 6ta, la bottom, está dentro de BrainModel) === */}
        <ambientLight intensity={0.5} color={0x404040} />
        <directionalLight position={[5, 5, 5]} intensity={1.2} color={0xffffff} />
        <directionalLight position={[-3, 2, -2]} intensity={0.6} color={0xffffff} />
        <directionalLight position={[0, -3, 4]} intensity={0.8} color={0x40e0d0} />
        <pointLight position={[0, 3, 0]} intensity={0.4} distance={8} color={0xffffff} />

        <Suspense fallback={<Fallback />}>
          <BrainModel activityState={activityState} isMobile={isMobile} activePersonality={activePersonality} />
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
