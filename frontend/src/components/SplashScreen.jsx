import React, { useState, useEffect } from 'react';
import { Archive, Library, Shield, Users, DatabaseZap } from 'lucide-react';

export default function SplashScreen({ onEnter }) {
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);

  const handleEnter = () => {
    setIsAnimatingOut(true);
    setTimeout(() => {
      onEnter();
    }, 600); // Wait for exit animation
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-gray-950 text-gray-100 overflow-y-auto overflow-x-hidden transition-opacity duration-700 ease-in-out ${isAnimatingOut ? 'opacity-0' : 'opacity-100'}`}>
      
      {/* Background Decorative Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-900/20 rounded-full blur-[120px] mix-blend-screen" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-indigo-900/20 rounded-full blur-[120px] mix-blend-screen" />
        <div className="absolute top-[40%] left-[30%] w-[40%] h-[40%] bg-purple-900/10 rounded-full blur-[100px] mix-blend-screen" />
      </div>

      <div className="relative z-10 max-w-4xl w-full mx-auto px-6 py-12 md:py-20 flex flex-col items-center">
        
        {/* Header Section */}
        <div className="text-center mb-12 animate-fade-in-up" style={{ animationDelay: '0.1s', animationFillMode: 'both' }}>
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 mb-6 shadow-lg shadow-indigo-500/30">
            <Archive className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl md:text-6xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-gray-100 to-gray-400 mb-4">
            Nanticoke & Delmarva Moor
          </h1>
          <h2 className="text-2xl md:text-3xl font-semibold text-indigo-400">
            Historical Archive
          </h2>
          <div className="h-1 w-24 bg-gradient-to-r from-indigo-500 to-transparent mx-auto mt-6 rounded-full opacity-50" />
        </div>

        {/* Content Grid */}
        <div className="grid md:grid-cols-2 gap-8 w-full mb-16">
          
          {/* About Card */}
          <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800 rounded-3xl p-8 hover:bg-gray-800/50 transition-colors duration-300 animate-fade-in-up" style={{ animationDelay: '0.3s', animationFillMode: 'both' }}>
            <div className="flex items-center gap-3 mb-4">
              <Library className="w-6 h-6 text-indigo-400" />
              <h3 className="text-xl font-bold text-gray-200">About the Project</h3>
            </div>
            <p className="text-gray-400 leading-relaxed text-sm md:text-base">
              A comprehensive digital preservation effort documenting the rich history, 
              lineage, and interconnected families of the Nanticoke Indians and Delmarva Moor 
              communities. This archive permanently safeguards obituaries, photos, relationships, 
              and historical records for future generations.
            </p>
          </div>

          {/* Credits & Sources Card */}
          <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800 rounded-3xl p-8 hover:bg-gray-800/50 transition-colors duration-300 flex flex-col gap-6 animate-fade-in-up" style={{ animationDelay: '0.5s', animationFillMode: 'both' }}>
            
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Users className="w-5 h-5 text-emerald-400" />
                <h3 className="text-lg font-bold text-gray-200">Curated By</h3>
              </div>
              <p className="text-gray-400 text-sm">
                Developed and curated by <span className="text-gray-200 font-medium">Jequan</span> / <span className="text-gray-200 font-medium">Written in the Genome</span>.
              </p>
            </div>

            <div className="h-px w-full bg-gray-800/50" />

            <div>
              <div className="flex items-center gap-3 mb-3">
                <DatabaseZap className="w-5 h-5 text-amber-400" />
                <h3 className="text-lg font-bold text-gray-200">Sources & Acknowledgments</h3>
              </div>
              <ul className="text-sm text-gray-400 space-y-2">
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-gray-600 mt-1.5 shrink-0" />
                  <span><strong>Mitsawokett Archives:</strong> Foundational historical records and lineage data.</span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-gray-600 mt-1.5 shrink-0" />
                  <span><strong>Find A Grave:</strong> Cemetery records, dates, and memorial verification.</span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-gray-600 mt-1.5 shrink-0" />
                  <span><strong>Community Contributions:</strong> Preserved obituaries and family photographs.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Enter Action */}
        <div className="animate-fade-in-up" style={{ animationDelay: '0.7s', animationFillMode: 'both' }}>
          <button 
            onClick={handleEnter}
            className="group relative inline-flex items-center justify-center gap-3 px-10 py-5 bg-white text-gray-950 font-bold text-lg rounded-full overflow-hidden transition-transform hover:scale-105 active:scale-95 shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)]"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-100 to-white opacity-0 group-hover:opacity-100 transition-opacity" />
            <span className="relative z-10">Enter Archive</span>
            <Shield className="w-5 h-5 relative z-10" />
          </button>
          <p className="text-center text-gray-600 text-xs mt-6 uppercase tracking-widest font-medium">
            Permanent Digital Preservation
          </p>
        </div>

      </div>

      <style dangerouslySetInnerHTML={{__html: `
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in-up {
          animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        }
      `}} />
    </div>
  );
}
