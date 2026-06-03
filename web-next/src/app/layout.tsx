import type { Metadata } from 'next';
import './globals.css';
import ErrorBoundary from '@/components/ErrorBoundary';
import { Toaster } from '@/components/ui/sonner';
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";

const inter = Inter({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: 'JARVIS — Neural Interface',
  description: 'AI Personal Assistant powered by LangGraph + Ollama Cloud',
};

function EnvScript() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || '';
  const json = JSON.stringify({ API_URL: apiUrl });
  return (
    <script
      dangerouslySetInnerHTML={{
        __html: `window.__ENV = ${json};`,
      }}
    />
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={cn("font-sans", inter.variable)}>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <meta name="theme-color" content="#0a0a0f" />
        <meta name="mobile-web-app-capable" content="yes" />
        <EnvScript />
      </head>
      <body className="antialiased bg-[#0a0a0f] min-h-screen overflow-hidden dark">
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
        <Toaster position="top-center" theme="dark" />
      </body>
    </html>
  );
}
