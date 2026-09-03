import React, { useState } from 'react';
import { Archive, Library, Shield, Users, DatabaseZap } from 'lucide-react';

export default function SplashScreen({ onEnter }) {
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);

  const handleEnter = () => {
    setIsAnimatingOut(true);
    setTimeout(() => {
      onEnter();
    }, 700);
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto overflow-x-hidden transition-opacity duration-300 ease-out custom-scrollbar"
      style={{
        background: '#0F0E0D',
        color: '#E5E1DB',
        opacity: isAnimatingOut ? 0 : 1,
      }}
    >
      {/* Background warm glow orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div style={{
          position: 'absolute', top: '-15%', left: '-10%',
          width: '55%', height: '55%',
          background: 'radial-gradient(circle, rgba(198,139,89,0.12) 0%, transparent 70%)',
          filter: 'blur(80px)',
        }} />
        <div style={{
          position: 'absolute', bottom: '-15%', right: '-10%',
          width: '55%', height: '55%',
          background: 'radial-gradient(circle, rgba(212,163,115,0.10) 0%, transparent 70%)',
          filter: 'blur(80px)',
        }} />
        <div style={{
          position: 'absolute', top: '35%', left: '25%',
          width: '50%', height: '40%',
          background: 'radial-gradient(circle, rgba(198,139,89,0.06) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }} />
        {/* Subtle grain texture line across top */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '1px',
          background: 'linear-gradient(90deg, transparent, #C68B59 40%, #D4A373 60%, transparent)',
          opacity: 0.3,
        }} />
      </div>

      {/* Centering container that preserves top margin on smaller viewports */}
      <div className="min-h-full w-full flex flex-col items-center justify-center py-10 sm:py-14 md:py-16 px-4 sm:px-6">
        <div className="relative z-10 max-w-4xl w-full mx-auto my-auto flex flex-col items-center">

        {/* Header */}
        <div className="text-center mb-12 splash-fade-up" style={{ animationDelay: '0.1s' }}>
          {/* Icon */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 80, height: 80, borderRadius: 20,
            background: 'linear-gradient(135deg, #C68B59, #8B5E3C)',
            marginBottom: 24,
            boxShadow: '0 8px 32px rgba(198,139,89,0.35)',
            border: '1px solid rgba(212,163,115,0.3)',
          }}>
            <Archive style={{ width: 36, height: 36, color: '#F3EBE3' }} />
          </div>

          {/* Main title — Cormorant Garamond serif to match the app */}
          <h1 style={{
            fontFamily: "'Cormorant Garamond', 'Cinzel', Georgia, serif",
            fontSize: 'clamp(2.4rem, 6vw, 4.5rem)',
            fontWeight: 700,
            letterSpacing: '-0.01em',
            background: 'linear-gradient(135deg, #F3EBE3 20%, #C68B59 80%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            marginBottom: 12,
            lineHeight: 1.1,
          }}>
            Tidewater Families
          </h1>

          {/* Subtitle */}
          <h2 style={{
            fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
            fontSize: 'clamp(1rem, 2.5vw, 1.35rem)',
            fontWeight: 500,
            color: '#A8A096',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
          }}>
            Historical Archive
          </h2>

          {/* Divider */}
          <div style={{
            height: 1, width: 80,
            background: 'linear-gradient(90deg, transparent, #C68B59, transparent)',
            margin: '20px auto 0',
            opacity: 0.6,
          }} />
        </div>

        {/* Content Cards */}
        <div className="grid md:grid-cols-2 gap-6 w-full mb-14">

          {/* About */}
          <div className="splash-fade-up" style={{ animationDelay: '0.3s' }}>
            <div style={{
              background: '#1C1A17',
              border: '1px solid #332D27',
              borderRadius: 20,
              padding: '28px 28px',
              height: '100%',
              transition: 'border-color 0.2s',
            }}
              onMouseEnter={e => e.currentTarget.style.borderColor = '#C68B59'}
              onMouseLeave={e => e.currentTarget.style.borderColor = '#332D27'}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                <Library style={{ width: 20, height: 20, color: '#C68B59', flexShrink: 0 }} />
                <h3 style={{
                  fontFamily: "'Cormorant Garamond', Georgia, serif",
                  fontSize: '1.2rem', fontWeight: 700, color: '#F3EBE3',
                }}>About the Project</h3>
              </div>
              <p style={{ color: '#A8A096', lineHeight: 1.75, fontSize: '0.9rem' }}>
                A comprehensive digital preservation effort documenting the rich history,
                lineage, and interconnected families of the Nanticoke Indians.
                This archive permanently safeguards obituaries, photos, relationships,
                and historical records for future generations.
              </p>
            </div>
          </div>

          {/* Credits & Sources */}
          <div className="splash-fade-up" style={{ animationDelay: '0.5s' }}>
            <div style={{
              background: '#1C1A17',
              border: '1px solid #332D27',
              borderRadius: 20,
              padding: '28px 28px',
              display: 'flex', flexDirection: 'column', gap: 20,
              height: '100%',
              transition: 'border-color 0.2s',
            }}
              onMouseEnter={e => e.currentTarget.style.borderColor = '#C68B59'}
              onMouseLeave={e => e.currentTarget.style.borderColor = '#332D27'}
            >
              {/* Curated by */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <Users style={{ width: 18, height: 18, color: '#D4A373', flexShrink: 0 }} />
                  <h3 style={{
                    fontFamily: "'Cormorant Garamond', Georgia, serif",
                    fontSize: '1.1rem', fontWeight: 700, color: '#F3EBE3',
                  }}>Curated By</h3>
                </div>
                <p style={{ color: '#A8A096', fontSize: '0.875rem' }}>
                  Developed and curated by{' '}
                  <span style={{ color: '#D4A373', fontWeight: 600 }}>Jequan</span>
                  {' '}/{' '}
                  <span style={{ color: '#D4A373', fontWeight: 600 }}>Written in the Genome</span>.
                </p>
              </div>

              <div style={{ height: 1, background: '#26221E' }} />

              {/* Sources */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                  <DatabaseZap style={{ width: 18, height: 18, color: '#C68B59', flexShrink: 0 }} />
                  <h3 style={{
                    fontFamily: "'Cormorant Garamond', Georgia, serif",
                    fontSize: '1.1rem', fontWeight: 700, color: '#F3EBE3',
                  }}>Sources & Acknowledgments</h3>
                </div>
                <ul style={{ color: '#A8A096', fontSize: '0.875rem', display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {[
                    ['Mitsawokett Archives', 'Foundational historical records and lineage data.'],
                    ['Find A Grave', 'Cemetery records, dates, and memorial verification.'],
                    ['Community Contributions', 'Preserved obituaries and family photographs.'],
                  ].map(([title, desc]) => (
                    <li key={title} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                      <div style={{
                        width: 6, height: 6, borderRadius: '50%',
                        background: '#C68B59', marginTop: 5, flexShrink: 0,
                      }} />
                      <span><strong style={{ color: '#D4A373', fontWeight: 600 }}>{title}:</strong> {desc}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="splash-fade-up" style={{ animationDelay: '0.7s' }}>
          <button
            onClick={handleEnter}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 12,
              padding: '16px 40px',
              background: 'linear-gradient(135deg, #C68B59, #8B5E3C)',
              color: '#F3EBE3',
              fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
              fontWeight: 700, fontSize: '1rem',
              borderRadius: 999,
              border: '1px solid rgba(212,163,115,0.4)',
              cursor: 'pointer',
              boxShadow: '0 0 40px rgba(198,139,89,0.3)',
              transition: 'transform 0.15s, box-shadow 0.15s',
              letterSpacing: '0.02em',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'scale(1.04)';
              e.currentTarget.style.boxShadow = '0 0 60px rgba(198,139,89,0.45)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.boxShadow = '0 0 40px rgba(198,139,89,0.3)';
            }}
            onMouseDown={e => { e.currentTarget.style.transform = 'scale(0.97)'; }}
            onMouseUp={e => { e.currentTarget.style.transform = 'scale(1.04)'; }}
          >
            Enter Archive
            <Shield style={{ width: 18, height: 18 }} />
          </button>
          <p style={{
            textAlign: 'center', color: '#4A4540',
            fontSize: '0.7rem', marginTop: 20,
            letterSpacing: '0.18em', textTransform: 'uppercase', fontWeight: 500,
          }}>
            Permanent Digital Preservation
          </p>
        </div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes splashFadeUp {
          from { opacity: 0; transform: translateY(18px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .splash-fade-up {
          opacity: 0;
          animation: splashFadeUp 0.85s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      ` }} />
    </div>
  );
}
