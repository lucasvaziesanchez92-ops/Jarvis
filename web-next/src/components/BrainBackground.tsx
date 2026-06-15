'use client';

import dynamic from 'next/dynamic';

// Holographic brain — native React/Three.js component
// (was an iframe pointing to /brain-standalone.html; now a real
//  component that integrates with activityState and renders the
//  STL-based faceted translucent brain with RoomEnvironment IBL)
const HolographicBrain = dynamic(() => import('@/components/HolographicBrain'), {
  ssr: false,
  loading: () => <div className="fixed inset-0 z-0 bg-black" />,
});

export default function BrainBackground() {
  return <HolographicBrain />;
}
