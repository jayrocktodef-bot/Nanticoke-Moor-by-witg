import React, { useState } from 'react';
import { Volume2, Play, Pause, Sparkles, Search, Clock, MessageSquare, ShieldCheck, User } from 'lucide-react';

const SAMPLE_ORAL_HISTORIES = [
  {
    id: 'oh-1',
    title: 'Recollections of the Davis & Jackson Homesteads',
    speaker: 'Elder Sarah Davis-Cook (b. 1928)',
    date: 'Recorded October 1994, Millsboro, DE',
    duration: '14:22',
    audio_url: '',
    transcripts: [
      { time: '00:15', speaker: 'Sarah Davis-Cook', text: 'My grandfather Levin Davis used to tell us about the timber mills down near Oak Orchard. The whole family worked the land together.' },
      { time: '02:40', speaker: 'Sarah Davis-Cook', text: 'When the census takers came around in 1900, they did not know how to classify our family, so they recorded us under different headings.' },
      { time: '06:10', speaker: 'Interviewer', text: 'Did your family keep a family Bible with the births listed?' },
      { time: '06:22', speaker: 'Sarah Davis-Cook', text: 'Yes, Aunt Martha kept the leather Bible with every marriage written on the inside cover back to 1840.' }
    ]
  },
  {
    id: 'oh-2',
    title: 'Nanticoke River Migration & Fishery Traditions',
    speaker: 'Captain Thomas Jackson (1935–2018)',
    date: 'Recorded June 2005, Vienna, MD',
    duration: '22:05',
    audio_url: '',
    transcripts: [
      { time: '01:05', speaker: 'Thomas Jackson', text: 'We fished the Nanticoke River every spring for shad. The Jackson and Morris clans always traded catches across county lines.' },
      { time: '05:30', speaker: 'Thomas Jackson', text: 'The old cemetery near Indian River was where my great-uncle Samuel Jackson was laid to rest.' }
    ]
  }
];

export default function OralHistoryPlayer() {
  const [selectedStory, setSelectedStory] = useState(SAMPLE_ORAL_HISTORIES[0]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredTranscripts = selectedStory.transcripts.filter(t =>
    t.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.speaker.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-[#C68B59]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[#C68B59] font-mono text-xs font-semibold uppercase tracking-wider mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Oral History & Community Testimony</span>
            </div>
            <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3]">
              Archival Voice Recordings & Timecoded Transcripts
            </h2>
            <p className="text-xs text-[#A8A096] mt-1 max-w-xl">
              Listen to firsthand oral histories, elder recollections, and traditional knowledge preserved across Delmarva generations.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Story Selector Sidebar */}
        <div className="lg:col-span-1 bg-[#141210] border border-[#26221E] rounded-2xl p-5 space-y-3 shadow-xl">
          <div className="flex items-center gap-2 font-semibold text-xs text-[#F3EBE3] border-b border-[#26221E] pb-3">
            <Volume2 className="w-4 h-4 text-[#C68B59]" />
            <span>Preserved Oral Testimonies</span>
          </div>

          <div className="space-y-2">
            {SAMPLE_ORAL_HISTORIES.map(story => {
              const isSelected = selectedStory.id === story.id;
              return (
                <div
                  key={story.id}
                  onClick={() => { setSelectedStory(story); setIsPlaying(false); }}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer space-y-1 ${
                    isSelected
                      ? 'bg-[#C68B59]/15 border-[#C68B59] text-[#F3EBE3]'
                      : 'bg-[#1C1A17] border-[#332D27] hover:border-[#6E665B] text-[#A8A096]'
                  }`}
                >
                  <h4 className="font-semibold text-xs text-[#F3EBE3]">{story.title}</h4>
                  <p className="text-[11px] text-[#D4A373]">{story.speaker}</p>
                  <div className="flex justify-between text-[10px] text-[#8C8275] font-mono pt-1">
                    <span>{story.date}</span>
                    <span>{story.duration}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Audio Player & Interactive Transcript */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-6 shadow-xl space-y-6">
            {/* Audio Controls Container */}
            <div className="bg-[#1C1A17] border border-[#332D27] rounded-xl p-5 flex flex-col sm:flex-row items-center gap-4">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="w-12 h-12 bg-[#C68B59] hover:bg-[#D4A373] text-[#121110] rounded-full flex items-center justify-center transition-all shadow-lg shrink-0 active:scale-95"
              >
                {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-0.5" />}
              </button>

              <div className="flex-1 space-y-1 w-full text-center sm:text-left">
                <h3 className="font-bold text-sm text-[#F3EBE3]">{selectedStory.title}</h3>
                <p className="text-xs text-[#D4A373]">{selectedStory.speaker}</p>
                
                {/* Waveform placeholder bar */}
                <div className="w-full bg-[#26221E] h-2 rounded-full overflow-hidden mt-2">
                  <div
                    className={`h-full bg-[#C68B59] transition-all duration-300 ${isPlaying ? 'w-1/3 animate-pulse' : 'w-0'}`}
                  />
                </div>
              </div>

              <span className="text-xs font-mono text-[#8C8275] shrink-0">{selectedStory.duration}</span>
            </div>

            {/* Transcript Search & Filter */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-[#D4A373] uppercase font-semibold flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Timecoded Searchable Transcript</span>
                </span>

                <div className="relative w-48 sm:w-64">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-2 text-[#8C8275]" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search in testimony..."
                    className="w-full bg-[#1C1A17] border border-[#332D27] focus:border-[#C68B59] rounded-lg pl-8 pr-3 py-1 text-xs text-[#F3EBE3] placeholder-[#6E665B] outline-none"
                  />
                </div>
              </div>

              {/* Transcript list */}
              <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar pr-2">
                {filteredTranscripts.map((t, idx) => (
                  <div
                    key={idx}
                    className="bg-[#1C1A17] border border-[#332D27] rounded-xl p-4 space-y-1 text-xs text-[#E5E1DB] hover:border-[#6E665B] transition-colors"
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono text-[#D4A373]">
                      <span className="font-semibold">{t.speaker}</span>
                      <span className="flex items-center gap-1 text-[#8C8275]">
                        <Clock className="w-3 h-3" />
                        {t.time}
                      </span>
                    </div>
                    <p className="font-serif leading-relaxed text-[#F3EBE3]">
                      "{t.text}"
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
