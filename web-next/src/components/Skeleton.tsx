'use client';

/* ── Skeleton ────────────────────────────────────────────────────────────
   Loading placeholder component with pulse animation.
   ─────────────────────────────────────────────────────────────────────── */

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  rounded?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
}

export function Skeleton({ className = '', width, height, rounded = 'md' }: SkeletonProps) {
  const radiusClass = {
    sm: 'rounded-sm',
    md: 'rounded-lg',
    lg: 'rounded-xl',
    xl: 'rounded-2xl',
    full: 'rounded-full',
  }[rounded];

  return (
    <div
      className={`animate-pulse bg-white/[0.03] ${radiusClass} ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    />
  );
}

/* ── NoteCardSkeleton ──────────────────────────────────────────────────── */
export function NoteCardSkeleton() {
  return (
    <div className="glass-base rounded-xl p-3.5 space-y-2">
      <div className="flex items-center gap-2">
        <Skeleton width={14} height={14} rounded="sm" />
        <Skeleton width="60%" height={14} />
      </div>
      <Skeleton width="90%" height={11} />
      <Skeleton width="40%" height={11} />
      <div className="flex gap-1.5">
        <Skeleton width={40} height={18} rounded="full" />
        <Skeleton width={50} height={18} rounded="full" />
      </div>
    </div>
  );
}

/* ── TaskItemSkeleton ─────────────────────────────────────────────────── */
export function TaskItemSkeleton() {
  return (
    <div className="flex items-center gap-3 px-3 py-3 glass-base rounded-xl">
      <Skeleton width={20} height={20} rounded="md" />
      <Skeleton width="70%" height={13} />
      <Skeleton width={6} height={6} rounded="full" />
    </div>
  );
}

/* ── ChatMessageSkeleton ───────────────────────────────────────────────── */
export function ChatMessageSkeleton({ role = 'assistant' }: { role?: 'user' | 'assistant' }) {
  return (
    <div className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-[85%] px-3.5 py-2.5 rounded-2xl space-y-1.5">
        <div className="flex items-center gap-1.5">
          <Skeleton width={14} height={14} rounded="full" />
          <Skeleton width={50} height={9} />
        </div>
        <Skeleton width="80%" height={13} />
        <Skeleton width="50%" height={13} />
      </div>
    </div>
  );
}

/* ── EmailItemSkeleton ─────────────────────────────────────────────────── */
export function EmailItemSkeleton() {
  return (
    <div className="flex items-center gap-3 px-3 py-3 glass-base rounded-xl">
      <Skeleton width={36} height={36} rounded="full" />
      <div className="flex-1 space-y-1.5">
        <Skeleton width="40%" height={12} />
        <Skeleton width="70%" height={11} />
      </div>
      <Skeleton width={50} height={9} />
    </div>
  );
}

/* ── BrainSkeleton ───────────────────────────────────────────────────── */
export function BrainSkeleton() {
  return (
    <div className="w-full h-full flex items-center justify-center">
      <div className="relative w-32 h-32">
        <Skeleton width={128} height={128} rounded="full" className="opacity-20" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-16 h-16 rounded-full border-2 border-cyan-400/20 animate-spin" 
               style={{ borderTopColor: '#00d4ff', borderRightColor: 'transparent' }} />
        </div>
      </div>
    </div>
  );
}
