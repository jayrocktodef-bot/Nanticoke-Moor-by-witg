import React, { useState } from 'react';
import { Archive, Library, Shield, Users, DatabaseZap, ChevronDown, ChevronUp } from 'lucide-react';

export default function SplashScreen({ onEnter }) {
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);
  const [expandedAbout, setExpandedAbout] = useState(false);
  const [expandedSources, setExpandedSources] = useState(false);

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

        {/* Content Bento Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full mb-12 items-stretch">

          {/* Bento Card 1: About */}
          <div className="splash-fade-up flex" style={{ animationDelay: '0.3s' }}>
            <div 
              className="bento-card bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] rounded-3xl p-6 sm:p-8 transition-all flex flex-col justify-between shadow-xl"
              style={{ minHeight: '100%' }}
            >
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-9 h-9 rounded-xl bg-[#C68B59]/15 border border-[#C68B59]/30 flex items-center justify-center shrink-0">
                    <Library className="w-4 h-4 text-[#C68B59]" />
                  </div>
                  <h3 style={{
                    fontFamily: "'Cormorant Garamond', Georgia, serif",
                    fontSize: '1.35rem', fontWeight: 700, color: '#F3EBE3',
                  }}>About the Project</h3>
                </div>
                <p className="text-[#A8A096] text-sm leading-relaxed mb-3">
                  A comprehensive digital preservation effort documenting the rich history,
                  lineage, and interconnected families of the Nanticoke Indians.
                  This archive permanently safeguards obituaries, photos, relationships,
                  and historical records for future generations.
                </p>

                {expandedAbout && (
                  <div className="mt-3 pt-3 border-t border-[#2D2722] text-xs text-[#C5BCB2] space-y-2 animate-fade-in">
                    <p className="leading-relaxed">
                      Focuses on the historic Native American and tri-racial isolate communities centered in Kent and Sussex Counties (Delaware) and Cumberland and Salem Counties (Southern New Jersey).
                    </p>
                    <p className="leading-relaxed">
                      Features 3,820 individual records, 2,609 verified photographs and descent charts, 522 historical obituaries, and 357 primary documentation sources.
                    </p>
                  </div>
                )}
              </div>

              <button
                onClick={() => setExpandedAbout(!expandedAbout)}
                className="mt-4 inline-flex items-center gap-1.5 text-xs font-mono font-semibold text-[#D4A373] hover:text-[#F3EBE3] transition-colors py-1 self-start"
              >
                <span>{expandedAbout ? 'Show Less' : 'Learn More Details'}</span>
                {expandedAbout ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Bento Card 2: Credits & Sources */}
          <div className="splash-fade-up flex" style={{ animationDelay: '0.5s' }}>
            <div 
              className="bento-card bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] rounded-3xl p-6 sm:p-8 transition-all flex flex-col justify-between shadow-xl"
              style={{ minHeight: '100%' }}
            >
              <div className="space-y-5">
                {/* Curated by */}
                <div>
                  <div className="flex items-center gap-2.5 mb-2">
                    <Users className="w-4 h-4 text-[#D4A373] shrink-0" />
                    <h3 style={{
                      fontFamily: "'Cormorant Garamond', Georgia, serif",
                      fontSize: '1.2rem', fontWeight: 700, color: '#F3EBE3',
                    }}>Curated By</h3>
                  </div>
                  <p className="text-[#A8A096] text-xs sm:text-sm">
                    Developed and curated by{' '}
                    <span className="text-[#D4A373] font-semibold">Jequan</span>
                    {' '}/{' '}
                    <span className="text-[#D4A373] font-semibold">Written in the Genome</span>.
                  </p>
                </div>

                <div className="h-px bg-[#26221E] w-full" />

                {/* Sources */}
                <div>
                  <div className="flex items-center gap-2.5 mb-3">
                    <DatabaseZap className="w-4 h-4 text-[#C68B59] shrink-0" />
                    <h3 style={{
                      fontFamily: "'Cormorant Garamond', Georgia, serif",
                      fontSize: '1.2rem', fontWeight: 700, color: '#F3EBE3',
                    }}>Sources & Acknowledgments</h3>
                  </div>
                  <ul className="text-[#A8A096] text-xs sm:text-sm space-y-2.5">
                    {[
                      ['Mitsawokett Archives', 'Foundational historical records and lineage data.'],
                      ['Find A Grave', 'Cemetery records, dates, and memorial verification.'],
                      ['Community Contributions', 'Preserved obituaries and family photographs.'],
                    ].map(([title, desc]) => (
                      <li key={title} className="flex items-start gap-2.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-[#C68B59] mt-1.5 shrink-0" />
                        <span><strong className="text-[#D4A373] font-semibold">{title}:</strong> {desc}</span>
                      </li>
                    ))}
                  </ul>

                  {expandedSources && (
                    <div className="mt-3 pt-3 border-t border-[#2D2722] text-xs text-[#C5BCB2] space-y-2 animate-fade-in">
                      <p className="leading-relaxed">
                        <strong className="text-[#D4A373]">Institutional Repositories:</strong> Smithsonian National Museum of the American Indian (NMAI) Frank G. Speck Collections, Delaware Public Archives, and Salem County Historical Society.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={() => setExpandedSources(!expandedSources)}
                className="mt-4 inline-flex items-center gap-1.5 text-xs font-mono font-semibold text-[#D4A373] hover:text-[#F3EBE3] transition-colors py-1 self-start"
              >
                <span>{expandedSources ? 'Show Less' : 'View Full Archive Sources'}</span>
                {expandedSources ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
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
