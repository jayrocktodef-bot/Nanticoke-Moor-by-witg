import React, { useState, useEffect, useRef } from 'react';
import { Volume2, VolumeX, Play, Pause, Sparkles, Search, Clock, MessageSquare, ShieldCheck, User, RotateCcw, FastForward, Mic } from 'lucide-react';

const SAMPLE_ORAL_HISTORIES = [
  {
    id: 'oh-1',
    title: 'Recollections of the Davis & Jackson Homesteads',
    speaker: 'Elder Sarah Davis-Cook (b. 1928)',
    date: 'Recorded October 1994, Millsboro, DE',
    duration: '14:22',
    audio_url: '/audio/oh-1.wav',
    transcripts: [
      { time: '00:05', textSec: 5, speaker: 'Sarah Davis-Cook', text: 'My grandfather Levin Davis used to tell us about the timber mills down near Oak Orchard. The whole family worked the land together.' },
      { time: '00:15', textSec: 15, speaker: 'Sarah Davis-Cook', text: 'When the census takers came around in 1900, they did not know how to classify our family, so they recorded us under different headings.' },
      { time: '00:30', textSec: 30, speaker: 'Interviewer', text: 'Did your family keep a family Bible with the births listed?' },
      { time: '00:42', textSec: 42, speaker: 'Sarah Davis-Cook', text: 'Yes, Aunt Martha kept the leather Bible with every marriage written on the inside cover back to 1840.' }
    ]
  },
  {
    id: 'oh-2',
    title: 'Nanticoke River Migration & Fishery Traditions',
    speaker: 'Captain Thomas Jackson (1935–2018)',
    date: 'Recorded June 2005, Vienna, MD',
    duration: '22:05',
    audio_url: '/audio/oh-2.wav',
    transcripts: [
      { time: '00:05', textSec: 5, speaker: 'Thomas Jackson', text: 'We fished the Nanticoke River every spring for shad. The Jackson and Morris clans always traded catches across county lines.' },
      { time: '00:25', textSec: 25, speaker: 'Thomas Jackson', text: 'The old cemetery near Indian River was where my great-uncle Samuel Jackson was laid to rest.' }
    ]
  }
];

export default function OralHistoryPlayer() {
  const [selectedStory, setSelectedStory] = useState(SAMPLE_ORAL_HISTORIES[0]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [audioError, setAudioError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSpeechMode, setIsSpeechMode] = useState(false);

  const audioRef = useRef(null);

  // Sync audio element state on track select or load
  useEffect(() => {
    setAudioError(null);
    setCurrentTime(0);
    setIsPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.load();
    }
  }, [selectedStory]);

  // Audio event listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoadedMetadata = () => {
      setDuration(audio.duration || 0);
      setAudioError(null);
    };
    const handleEnded = () => setIsPlaying(false);
    const handleError = (e) => {
      console.warn('Audio play error, falling back to synthesizer:', e);
      setAudioError('Primary audio stream loading. Speech synthesizer ready as fallback.');
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, []);

  // Sync volume and playback rate
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
      audioRef.current.playbackRate = playbackRate;
    }
  }, [volume, isMuted, playbackRate]);

  // Speech synthesizer fallback stop on unmount/change
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [selectedStory]);

  const togglePlayPause = async () => {
    if (isSpeechMode) {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        if (isPlaying) {
          window.speechSynthesis.pause();
          setIsPlaying(false);
        } else {
          if (window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
            setIsPlaying(true);
          } else {
            window.speechSynthesis.cancel();
            const fullText = selectedStory.transcripts.map(t => `${t.speaker} says: ${t.text}`).join('. ');
            const utterance = new SpeechSynthesisUtterance(fullText);
            utterance.rate = playbackRate;
            utterance.onend = () => setIsPlaying(false);
            utterance.onerror = () => setIsPlaying(false);
            window.speechSynthesis.speak(utterance);
            setIsPlaying(true);
          }
        }
      }
      return;
    }

    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      try {
        await audioRef.current.play();
        setIsPlaying(true);
        setAudioError(null);
      } catch (err) {
        console.error('Failed to play audio:', err);
        // Fallback to speech synthesis if audio playback fails
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
          setIsSpeechMode(true);
          const fullText = selectedStory.transcripts.map(t => `${t.speaker} says: ${t.text}`).join('. ');
          const utterance = new SpeechSynthesisUtterance(fullText);
          utterance.rate = playbackRate;
          utterance.onend = () => setIsPlaying(false);
          window.speechSynthesis.speak(utterance);
          setIsPlaying(true);
        } else {
          setAudioError('Playback failed. Please check your browser audio permissions.');
        }
      }
    }
  };

  const handleSeek = (e) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  };

  const jumpToTimestamp = (sec) => {
    setCurrentTime(sec);
    if (audioRef.current) {
      audioRef.current.currentTime = sec;
      if (!isPlaying) {
        audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
      }
    }
  };

  const formatTime = (sec) => {
    if (!sec || isNaN(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const filteredTranscripts = selectedStory.transcripts.filter(t =>
    t.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.speaker.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* HTML5 Audio Element */}
      <audio
        ref={audioRef}
        src={selectedStory.audio_url}
        preload="auto"
      />

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
                  onClick={() => { setSelectedStory(story); }}
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
            <div className="bg-[#1C1A17] border border-[#332D27] rounded-xl p-5 space-y-4">
              <div className="flex flex-col sm:flex-row items-center gap-4">
                <button
                  onClick={togglePlayPause}
                  aria-label={isPlaying ? "Pause audio recording" : "Play audio recording"}
                  className="w-14 h-14 bg-[#C68B59] hover:bg-[#D4A373] text-[#121110] rounded-full flex items-center justify-center transition-all shadow-lg shrink-0 active:scale-95 cursor-pointer"
                >
                  {isPlaying ? (
                    <Pause className="w-6 h-6 fill-current" />
                  ) : (
                    <Play className="w-6 h-6 fill-current ml-1" />
                  )}
                </button>

                <div className="flex-1 space-y-1 w-full text-center sm:text-left">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-sm text-[#F3EBE3]">{selectedStory.title}</h3>
                    {isSpeechMode && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#C68B59]/20 text-[#D4A373] flex items-center gap-1 border border-[#C68B59]/30">
                        <Mic className="w-3 h-3" /> Speech Synthesizer
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#D4A373]">{selectedStory.speaker}</p>
                  
                  {/* Interactive Scrub / Progress Bar */}
                  <div className="pt-2">
                    <input
                      type="range"
                      min="0"
                      max={duration || 60}
                      step="0.1"
                      value={currentTime}
                      onChange={handleSeek}
                      className="w-full h-2 bg-[#26221E] rounded-lg appearance-none cursor-pointer accent-[#C68B59]"
                    />
                    <div className="flex justify-between text-[11px] font-mono text-[#8C8275] pt-1">
                      <span>{formatTime(currentTime)}</span>
                      <span>{duration ? formatTime(duration) : selectedStory.duration}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Advanced Audio Controls Toolbar */}
              <div className="flex flex-wrap items-center justify-between border-t border-[#26221E] pt-3 gap-3">
                {/* Volume Control */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsMuted(!isMuted)}
                    className="text-[#8C8275] hover:text-[#F3EBE3] transition-colors"
                  >
                    {isMuted || volume === 0 ? <VolumeX className="w-4 h-4 text-red-400" /> : <Volume2 className="w-4 h-4" />}
                  </button>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={isMuted ? 0 : volume}
                    onChange={(e) => { setVolume(parseFloat(e.target.value)); setIsMuted(false); }}
                    className="w-20 h-1.5 bg-[#26221E] rounded-lg appearance-none cursor-pointer accent-[#C68B59]"
                  />
                </div>

                {/* Speed Controls */}
                <div className="flex items-center gap-1.5 text-xs text-[#8C8275]">
                  <span className="font-mono text-[10px] uppercase">Speed:</span>
                  {[1, 1.25, 1.5, 2].map((rate) => (
                    <button
                      key={rate}
                      onClick={() => setPlaybackRate(rate)}
                      className={`px-2 py-0.5 rounded font-mono text-[11px] transition-colors ${
                        playbackRate === rate
                          ? 'bg-[#C68B59] text-[#121110] font-bold'
                          : 'bg-[#26221E] text-[#A8A096] hover:text-[#F3EBE3]'
                      }`}
                    >
                      {rate}x
                    </button>
                  ))}
                </div>

                {/* Toggle Synthetic Speech Narrator */}
                <button
                  onClick={() => setIsSpeechMode(!isSpeechMode)}
                  className={`text-xs font-mono px-2.5 py-1 rounded flex items-center gap-1.5 border transition-all ${
                    isSpeechMode
                      ? 'bg-[#C68B59]/20 text-[#D4A373] border-[#C68B59]'
                      : 'bg-[#26221E] text-[#8C8275] border-transparent hover:text-[#F3EBE3]'
                  }`}
                >
                  <Mic className="w-3 h-3" />
                  <span>{isSpeechMode ? 'Using Speech Synthesizer' : 'Use AI Voice Reader'}</span>
                </button>
              </div>

              {audioError && (
                <div className="text-[11px] font-mono text-amber-300/80 bg-amber-950/30 border border-amber-800/40 rounded p-2">
                  {audioError}
                </div>
              )}
            </div>

            {/* Transcript Search & Filter */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-[#D4A373] uppercase font-semibold flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Timecoded Searchable Transcript (Click timestamp to seek)</span>
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
                    className="bg-[#1C1A17] border border-[#332D27] rounded-xl p-4 space-y-1.5 text-xs text-[#E5E1DB] hover:border-[#C68B59]/60 transition-colors group"
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono text-[#D4A373]">
                      <span className="font-semibold">{t.speaker}</span>
                      <button
                        onClick={() => jumpToTimestamp(t.textSec)}
                        className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#26221E] hover:bg-[#C68B59] hover:text-[#121110] text-[#D4A373] transition-colors cursor-pointer"
                        title="Click to play from this moment"
                      >
                        <Play className="w-3 h-3 fill-current" />
                        <span>{t.time}</span>
                      </button>
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
