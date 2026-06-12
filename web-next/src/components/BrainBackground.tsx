'use client';

// JARVIS Brain 3D — uses the user's reference HTML directly as
// the renderer. The reference is /brain-standalone.html in
// `New folder (2)/` (the user-supplied Tripo replica), which
// renders the brain in the exact pose + material the user asked
// for: ice-blue (#d0e8e8) with pink sheen (#ff69b4), flatShading,
// view rotated -PI/2 (lateral anatomical), camera (0, 0.5, 3.5).
//
// We embed it in an iframe so we don't re-implement Three.js, and
// we keep the same activity state behaviour via postMessage.

import { useEffect, useRef } from 'react';
import { useJarvisStore } from '@/store/jarvisStore';

export default function BrainBackground() {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const { activityState } = useJarvisStore();

  // Push activity state to the iframe so the brain can react
  // (e.g. blink on thinking). The reference HTML doesn't know
  // about our state, so we send a message; the HTML can listen
  // and act on it. (Reference HTML ignores it today — keeping
  // the same pose and color always — but this is the hook for
  // future integration.)
  useEffect(() => {
    if (!iframeRef.current?.contentWindow) return;
    try {
      iframeRef.current.contentWindow.postMessage(
        { type: 'jarvis:activity', state: activityState },
        '*',
      );
    } catch {
      /* sandbox restrictions in some browsers — safe to ignore */
    }
  }, [activityState]);

  return (
    <div className="fixed inset-0 z-0 pointer-events-auto">
      <iframe
        ref={iframeRef}
        src="/brain-standalone.html"
        title="JARVIS Brain"
        className="w-full h-full border-0"
        style={{ background: 'transparent' }}
        // The reference HTML loads three.js + STL via CDN. We let
        // the iframe do all the rendering work — we just host it.
        loading="eager"
      />
    </div>
  );
}
