// Fast, Ultra-Responsive Voice Engine for J.A.R.V.I.S.
// Features:
// 1. ChatGPT Voice Mode (Continuous hands-free multi-turn loop)
// 2. Ultra-Fast Native Speech Recognition (Instant zero-lag acoustic grasping)
// 3. Comprehensive Phonetic & Acoustic Normalizer (Fayaz, Fowzia, ChatGPT, Jarvis, etc.)
// 4. Zero-Dropped Words Duplex Barge-In (Speaks while J.A.R.V.I.S. speaks without losing start words)
// 5. Echo-Shielded Speech Synthesis (Audio output never cuts off or gets canceled by speakers)
// 6. Real-Time Web Audio RMS Metering for Arc Reactor HUD

export interface VoiceOption {
  name: string;
  lang: string;
  default: boolean;
}

export type VoiceMode = 'wake_word' | 'active_listening' | 'push_to_talk' | 'idle';

// Comprehensive Instant Phonetic & Acoustic Normalizer
export function normalizeWhisperPhonetics(text: string): string {
  if (!text) return '';
  let cleaned = text.trim();

  // 1. Remove initial/trailing speech filler sounds
  cleaned = cleaned.replace(/^(um+|uh+|ah+|err+|like)\b[,:\s]*/i, '');
  cleaned = cleaned.replace(/[,:\s]*\b(um+|uh+|ah+|err+)$/i, '');

  // 2. High-Precision Acoustic & Homophone Replacements
  const replacements: [RegExp, string][] = [
    // User Name: Fayaz & Md Fayaz
    [/\b(md|mohammed|mohd)?\s*(fiaz|faiaz|fayas|fayaas|fire us|fire as|phiyaz|faiyaz|fayoz|fayez|faya|fyaas|fiyaz)\b/gi, 'Fayaz'],
    [/\b(md|mohammed|mohd)\s+fayaz\b/gi, 'Md Fayaz'],

    // Family / User Name: Fowzia
    [/\b(fauzia|fouzia|fauziya|fawzia|fawziya|fauza|fauja|phauzia|for zia|four zia|fouzya|fowziya)\b/gi, 'Fowzia'],

    // AI & System Terms
    [/\b(chat\s*gpt|charge\s*gpt|chat\s*jpt|chat\s*gbt|chad\s*gpt|check\s*gpt|track\s*gpt|chatgpt)\b/gi, 'ChatGPT'],
    [/\bo\s*llama\b/gi, 'Ollama'],
    [/\bolama\b/gi, 'Ollama'],
    [/\bquinn\s*3\b/gi, 'Qwen 3'],
    [/\bq\s*wen\b/gi, 'Qwen'],

    // Whisper / STT terms
    [/\bwsiper\b/gi, 'whisper'],
    [/\bwisper\b/gi, 'whisper'],
    [/\bvesper\b/gi, 'whisper'],

    // Assistant naming phonetic homophones
    [/\b(javis|travis|charvis|jarviss|javice)\b/gi, 'Jarvis'],

    // Developer & System Tools
    [/\bu\s*tube\b/gi, 'YouTube'],
    [/\byou\s*tube\b/gi, 'YouTube'],
    [/\bgit\s*hub\b/gi, 'GitHub'],
    [/\bvs\s*code\b/gi, 'VS Code'],
    [/\bpower\s*shell\b/gi, 'PowerShell'],

    // Common speech-to-text acoustic confusions
    [/\bwhat's the whether\b/gi, "what's the weather"],
    [/\bwhats the whether\b/gi, "what's the weather"],
    [/\bhow is the whether\b/gi, "how is the weather"],
    [/\bturn on the whether\b/gi, "turn on the weather"],
    [/\bi satr\b/gi, 'I start'],
    [/\bi satrt\b/gi, 'I start'],
    [/\bi start talking\b/gi, 'I start talking'],
    [/\bwhen i satr\b/gi, 'when I start'],
    [/\bwhen i satrt\b/gi, 'when I start'],
  ];

  for (const [regex, replacement] of replacements) {
    cleaned = cleaned.replace(regex, replacement);
  }

  // Capitalize first character for clean sentence presentation
  if (cleaned.length > 0) {
    cleaned = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  }

  return cleaned;
}

export class SpeechService {
  private recognition: any = null;
  private currentMode: VoiceMode = 'idle';
  private wakeWordEnabled = true;
  private isMuted = false;
  private selectedLanguage = 'en-IN'; // Default to Indian English for optimal regional grasping
  public currentUtterance: SpeechSynthesisUtterance | null = null;

  // Speaker Echo-Gating & TTS Keep-Alive
  private isVocalizing = false;
  private ttsHeartbeat: any = null;
  private ttsSafetyWatcher: any = null;

  // Real-time Audio Metering for Arc Reactor
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private micStream: MediaStream | null = null;
  private animationFrameId: number | null = null;
  private audioLevelCallback: ((level: number) => void) | null = null;

  // Turn-Taking Silence Debouncing & Inactivity Auto-Stop Timers
  private wakeTriggeredThisTurn = false;
  private currentCapturedCommand = '';
  private silenceTimer: any = null;
  private inactivityTimer: any = null;
  private restartTimeout: any = null;
  private maxRecordingTimer: any = null;
  private startIndex = 0;

  // Configurable Parameters
  private vadSilenceTimeout = 950; // ms (snappy, conversational silence pause)
  private voiceFeedback = true;
  private interruptOnWake = true;
  private maxRecordingDuration = 30; // seconds

  // Continuous ChatGPT Voice Mode Session State
  private isContinuousSessionActive = false;
  private continuousIdleTimer: any = null;
  private whisperBackendEnabled = false;

  // Callbacks
  private onActiveCommandCallback: ((transcript: string, isFinal: boolean) => void) | null = null;
  private onWakeWordCallback: ((command: string) => void) | null = null;
  private onWakeWordOnlyCallback: (() => void) | null = null;
  private onWakeActiveCallback: (() => void) | null = null;
  private onWakeLiveTranscriptCallback: ((text: string) => void) | null = null;
  private onActiveLiveTranscriptCallback: ((text: string) => void) | null = null;
  private onErrorCallback: ((error: string) => void) | null = null;
  private onInterruptCallback: (() => void) | null = null;
  private onContinuousSessionChangeCallback: ((active: boolean) => void) | null = null;
  private onContinuousTurnReadyCallback: (() => void) | null = null;

  constructor() {
    if (typeof navigator !== 'undefined' && navigator.language) {
      if (navigator.language.toLowerCase().includes('in')) {
        this.selectedLanguage = 'en-IN';
      } else if (navigator.language.toLowerCase().includes('us')) {
        this.selectedLanguage = 'en-US';
      } else {
        this.selectedLanguage = navigator.language;
      }
    }
    this.initRecognition();
    this.initMicStream();
  }

  public setLanguage(lang: string) {
    if (!lang || lang === 'auto') {
      this.selectedLanguage =
        typeof navigator !== 'undefined' && navigator.language ? navigator.language : 'en-IN';
    } else {
      this.selectedLanguage = lang;
    }
    if (this.recognition) {
      this.recognition.lang = this.selectedLanguage;
    }
  }

  public getLanguage(): string {
    return this.selectedLanguage;
  }

  // --- Real-Time Hardware Microphone Stream (Audio Visualizer) ---
  public async initMicStream() {
    try {
      if (!this.micStream) {
        this.micStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

        const ctx = this.getAudioContext();
        const source = ctx.createMediaStreamSource(this.micStream);
        this.analyser = ctx.createAnalyser();
        this.analyser.fftSize = 64;
        this.analyser.smoothingTimeConstant = 0.3;
        source.connect(this.analyser);

        this.startMeterLoop();
      }
    } catch (e) {
      console.warn('Mic stream initialization notice:', e);
    }
  }

  private startMeterLoop() {
    if (this.animationFrameId) return;
    const bufferLength = this.analyser?.frequencyBinCount || 32;
    const dataArray = new Uint8Array(bufferLength);

    const checkLevel = () => {
      if (this.analyser) {
        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        const normalized = Math.min(1.0, Math.max(0, avg / 128));

        // When JARVIS is vocalizing, mute visualizer so it doesn't bounce from its own voice
        if (this.isVocalizing || this.isSpeakingNow()) {
          this.audioLevelCallback?.(0);
        } else {
          this.audioLevelCallback?.(normalized);
        }
      }
      this.animationFrameId = requestAnimationFrame(checkLevel);
    };
    checkLevel();
  }

  public setAudioLevelCallback(cb: ((level: number) => void) | null) {
    this.audioLevelCallback = cb;
    if (cb && !this.micStream) {
      this.initMicStream();
    }
  }

  // --- Native Web SpeechRecognition Engine ---
  public initRecognition() {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn('SpeechRecognition API is unavailable in this browser.');
      return;
    }

    try {
      if (this.recognition) {
        this.recognition.onstart = null;
        this.recognition.onresult = null;
        this.recognition.onerror = null;
        this.recognition.onend = null;
        try {
          this.recognition.abort();
        } catch {}
        this.recognition = null;
      }

      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.maxAlternatives = 3;
      this.recognition.lang = this.selectedLanguage;

      this.recognition.onresult = (event: any) => {
        // N-Best Alternative Selection across confidence scores
        let fullTranscript = '';
        let isFinalChunk = false;

        const startIdx = Math.max(0, Math.min(this.startIndex, event.results.length));
        for (let i = startIdx; i < event.results.length; ++i) {
          const res = event.results[i];
          let bestChunk = res[0].transcript;
          let bestConfidence = res[0].confidence || 0;
          for (let a = 1; a < res.length; ++a) {
            if (res[a].confidence && res[a].confidence > bestConfidence) {
              bestChunk = res[a].transcript;
              bestConfidence = res[a].confidence;
            }
          }
          fullTranscript += (fullTranscript ? ' ' : '') + bestChunk.trim();
          if (res.isFinal) {
            isFinalChunk = true;
          }
        }

        const rawText = fullTranscript.trim();
        if (!rawText) return;
        const lowerText = rawText.toLowerCase();

        // 0. DUPLEX BARGE-IN (USER SPEAKS WHILE JARVIS IS VOCALIZING)
        if (this.isVocalizing || this.isSpeakingNow()) {
          if (this.interruptOnWake) {
            const bargePattern =
              /\b(hey|hi|ok|okay)?\s*(jarvis|javis|travis|service|jars|java|jobless|charvis|stop|cancel|halt|quiet|wait|hold on)\b/i;
            const shouldBarge = this.isContinuousSessionActive
              ? rawText.trim().length > 1
              : bargePattern.test(lowerText);

            if (shouldBarge) {
              console.log('[VOICE_ENGINE] Duplex barge-in triggered! Halting vocalization.');
              // 1. Immediately silence speech synthesis without dropping the user's spoken words
              this.isVocalizing = false;
              if (this.isSpeechSynthesisSupported()) {
                window.speechSynthesis.cancel();
              }
              clearInterval(this.ttsHeartbeat);
              this.ttsHeartbeat = null;
              clearInterval(this.ttsSafetyWatcher);
              this.ttsSafetyWatcher = null;
              this.currentUtterance = null;
              (window as any).__jarvis_active_utterance = null;
              this.onInterruptCallback?.();

              if (this.voiceFeedback) {
                this.playChime('listen_start');
              }

              // 2. CRITICAL FIX: In Continuous Mode, keep whatever the user spoke right from the start!
              // DO NOT advance startIndex or reset!
              if (this.isContinuousSessionActive) {
                this.currentMode = 'active_listening';
                this.resetContinuousIdleTimer();
                // Smoothly fall through into active_listening block below with full rawText intact!
              } else {
                const afterMatch = lowerText
                  .replace(/.*?\b(jarvis|javis|travis|service|jars|java|jobless|charvis|stop|cancel|halt|quiet|wait)\b/i, '')
                  .replace(/^[,:\s]+/, '')
                  .trim();
                this.startIndex = event.results ? event.results.length : 0;
                this.wakeTriggeredThisTurn = true;
                this.currentCapturedCommand = afterMatch;
                this.onWakeActiveCallback?.();
                return;
              }
            } else {
              // Echo suppression: Ignore assistant's own minor audio reflections
              return;
            }
          } else {
            return;
          }
        }

        // 1. ACTIVE COMMAND / CONTINUOUS CHATGPT VOICE MODE
        if (this.currentMode === 'active_listening' || this.currentMode === 'push_to_talk') {
          clearTimeout(this.inactivityTimer);
          if (this.isContinuousSessionActive) {
            this.resetContinuousIdleTimer();
          }

          // Voice Exit detection
          if (this.isContinuousSessionActive) {
            const exitPattern =
              /\b(goodbye|bye jarvis|stop voice|stop listening|deactivate voice|deactivate|sleep jarvis|go to sleep|standby mode|standby|that's all jarvis|that's all)\b/i;
            if (exitPattern.test(lowerText)) {
              this.startIndex = event.results ? event.results.length : 0;
              this.stopContinuousSession('voice_exit');
              return;
            }
          }

          // Strip any accidental leading wake words if user happened to say "Jarvis, what's..."
          const cleaned = rawText
            .replace(/^(hey|hi|ok|okay)?\s*(jarvis|javis|travis|service|jars|java|jobless|charvis)[,:\s]*/i, '')
            .trim();

          // Instant High-Precision Phonetic Normalization (Fayaz, Fowzia, ChatGPT, etc.)
          const displayCommand = normalizeWhisperPhonetics(cleaned || rawText);

          this.currentCapturedCommand = displayCommand;
          this.onActiveLiveTranscriptCallback?.(displayCommand);

          // Conversational Turn-Taking Silence Debounce
          clearTimeout(this.silenceTimer);
          const silenceDelay = isFinalChunk
            ? Math.max(650, Math.floor(this.vadSilenceTimeout * 0.7))
            : this.vadSilenceTimeout;

          this.silenceTimer = setTimeout(() => {
            const finalQuery = normalizeWhisperPhonetics(this.currentCapturedCommand || displayCommand).trim();
            this.startIndex = event.results ? event.results.length : 0;
            const callback = this.onActiveCommandCallback;

            if (this.isContinuousSessionActive) {
              this.currentCapturedCommand = '';
              this.silenceTimer = null;
              if (finalQuery.length > 0 && callback) {
                callback(finalQuery, true);
              }
            } else {
              this.stopActiveListening();
              this.restartRecognitionSession();
              if (finalQuery.length > 0 && callback) {
                callback(finalQuery, true);
                this.currentCapturedCommand = '';
                this.silenceTimer = null;
              }
            }
          }, silenceDelay);

          return;
        }

        // 2. WAKE-WORD DETECTION MODE ("Hey Jarvis")
        if (this.currentMode === 'wake_word' && this.wakeWordEnabled) {
          const wakePattern =
            /\b(hey|hi|ok|okay|wake up|yo|hello)?\s*(jarvis|javis|travis|service|jars|java|jobless|charvis)\b/i;

          if (!this.wakeTriggeredThisTurn && wakePattern.test(lowerText)) {
            this.wakeTriggeredThisTurn = true;
            if (this.voiceFeedback) {
              this.playChime('wake');
            }
            this.onWakeActiveCallback?.();

            clearTimeout(this.maxRecordingTimer);
            this.maxRecordingTimer = setTimeout(() => {
              if (this.wakeTriggeredThisTurn && this.currentCapturedCommand.trim()) {
                const finalCmd = normalizeWhisperPhonetics(this.currentCapturedCommand.trim());
                this.startIndex = event.results ? event.results.length : 0;
                this.wakeTriggeredThisTurn = false;
                this.currentCapturedCommand = '';
                this.restartRecognitionSession();
                this.onWakeWordCallback?.(finalCmd);
              }
            }, this.maxRecordingDuration * 1000);
          }

          if (this.wakeTriggeredThisTurn) {
            clearTimeout(this.inactivityTimer);

            const match = lowerText.match(
              /\b(jarvis|javis|travis|service|jars|java|jobless|charvis)\b/i
            );
            let commandText = '';
            if (match && match.index !== undefined) {
              const wakeEnd = match.index + match[0].length;
              commandText = rawText.slice(wakeEnd).replace(/^[,:\s]+/, '').trim();
            } else {
              commandText = rawText
                .replace(/^(hey|hi|ok|okay)?\s*(jarvis|javis|travis|service|jars|java|jobless|charvis)[,:\s]*/i, '')
                .trim();
            }

            const normalizedCommand = normalizeWhisperPhonetics(commandText);
            this.currentCapturedCommand = normalizedCommand;
            this.onWakeLiveTranscriptCallback?.(normalizedCommand);

            clearTimeout(this.silenceTimer);
            const silenceDelay = isFinalChunk
              ? Math.max(700, Math.floor(this.vadSilenceTimeout * 0.75))
              : this.vadSilenceTimeout;

            this.silenceTimer = setTimeout(() => {
              clearTimeout(this.maxRecordingTimer);
              const finalCmd = normalizeWhisperPhonetics(this.currentCapturedCommand.trim());
              this.startIndex = event.results ? event.results.length : 0;
              this.wakeTriggeredThisTurn = false;
              this.currentCapturedCommand = '';
              this.silenceTimer = null;

              this.restartRecognitionSession();
              if (finalCmd.length > 0) {
                this.onWakeWordCallback?.(finalCmd);
              } else {
                this.onWakeWordOnlyCallback?.();
              }
            }, silenceDelay);
          }
        }
      };

      this.recognition.onerror = (event: any) => {
        if (event.error === 'not-allowed') {
          this.onErrorCallback?.(
            'Microphone access denied. Please grant microphone access in your browser.'
          );
        } else if (event.error === 'network') {
          console.warn('Speech recognition network glitch, reconnecting...');
        }
      };

      this.recognition.onend = () => {
        this.startIndex = 0;
        if (this.currentMode !== 'idle') {
          clearTimeout(this.restartTimeout);
          this.restartTimeout = setTimeout(() => {
            this.safeStartRecognition();
          }, 150);
        }
      };
    } catch (e) {
      console.warn('Speech recognition initialization error:', e);
    }
  }

  public safeStartRecognition() {
    if (this.currentMode === 'idle') return;
    if (!this.recognition) {
      this.initRecognition();
    }
    try {
      this.recognition?.start();
    } catch (e: any) {
      if (e?.name === 'InvalidStateError') {
        this.initRecognition();
        try {
          this.recognition?.start();
        } catch {}
      }
    }
  }

  public restartRecognitionSession() {
    this.startIndex = 0;
    this.wakeTriggeredThisTurn = false;
    this.currentCapturedCommand = '';
    clearTimeout(this.silenceTimer);
    clearTimeout(this.inactivityTimer);
    this.silenceTimer = null;
    this.inactivityTimer = null;

    if (this.currentMode !== 'idle') {
      this.initRecognition();
      this.safeStartRecognition();
    }
  }

  // --- Web Audio Synthesizer: Futuristic Iron Man HUD Chimes ---
  private getAudioContext(): AudioContext {
    if (!this.audioContext || this.audioContext.state === 'closed') {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioCtx();
    }
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
    return this.audioContext;
  }

  public playChime(type: 'wake' | 'listen_start' | 'listen_stop') {
    try {
      const ctx = this.getAudioContext();
      const now = ctx.currentTime;

      if (type === 'wake') {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.exponentialRampToValueAtTime(1320, now + 0.12);
        gain.gain.setValueAtTime(0.18, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.3);
      } else if (type === 'listen_start') {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(660, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.08);
        gain.gain.setValueAtTime(0.1, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.16);
      } else if (type === 'listen_stop') {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.exponentialRampToValueAtTime(520, now + 0.08);
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.13);
      }
    } catch (e) {
      // Audio playback fails gracefully if autoplay restricted
    }
  }

  // --- Manual Interruption (Invoked by ESC key, [INTERRUPT] button, or Mic click) ---
  public interrupt() {
    this.stopSpeaking();
  }

  public testVoice(voiceName?: string, rate: number = 1.0, pitch: number = 1.0) {
    this.speak(
      "Audio protocols fully operational, Sir. Awaiting your command.",
      { preferredVoice: voiceName, rate, pitch }
    );
  }

  // --- Voice Synthesis (TTS) with Echo-Shielding and Chromium Keep-Alive ---
  public stopSpeaking() {
    clearInterval(this.ttsHeartbeat);
    clearInterval(this.ttsSafetyWatcher);
    this.ttsHeartbeat = null;
    this.ttsSafetyWatcher = null;
    this.isVocalizing = false;
    this.currentUtterance = null;
    (window as any).__jarvis_active_utterance = null;

    if (this.isSpeechSynthesisSupported()) {
      window.speechSynthesis.cancel();
    }

    if (this.isContinuousSessionActive) {
      this.currentMode = 'active_listening';
      this.wakeTriggeredThisTurn = false;
      this.currentCapturedCommand = '';
      this.startIndex = 0;
      setTimeout(() => {
        this.safeStartRecognition();
      }, 100);
    } else if (this.wakeWordEnabled || this.currentMode !== 'idle') {
      setTimeout(() => {
        this.safeStartRecognition();
      }, 100);
    }
  }

  public isSpeakingNow(): boolean {
    return !!(window.speechSynthesis && (window.speechSynthesis.speaking || this.currentUtterance));
  }

  public getAvailableVoices(): VoiceOption[] {
    if (!this.isSpeechSynthesisSupported()) return [];
    return window.speechSynthesis.getVoices().map((v) => ({
      name: v.name,
      lang: v.lang,
      default: v.default,
    }));
  }

  public speak(
    text: string,
    options?: {
      rate?: number;
      pitch?: number;
      preferredVoice?: string;
      onStart?: () => void;
      onEnd?: () => void;
      onError?: (err: any) => void;
    }
  ) {
    if (this.isMuted) return;
    if (!this.isSpeechSynthesisSupported()) return;

    const cleanText = text
      .replace(/```[\s\S]*?```/g, 'Code block omitted.')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/https?:\/\/[^\s)]+/g, 'link')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/#+\s/g, '')
      .replace(/^[-*+]\s+/gm, '')
      .replace(/^>\s+/gm, '')
      .replace(/\{.*?\}/g, '')
      .replace(/SYSTEM TOOL EXECUTION REPORT/g, '')
      .trim();

    if (!cleanText) return;

    clearInterval(this.ttsHeartbeat);
    clearInterval(this.ttsSafetyWatcher);

    try {
      if (window.speechSynthesis.speaking || window.speechSynthesis.pending) {
        window.speechSynthesis.cancel();
      }
    } catch {}

    if (window.speechSynthesis.paused) {
      try {
        window.speechSynthesis.resume();
      } catch {}
    }

    this.isVocalizing = true;
    const ttsStartTime = Date.now();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = options?.rate || 1.05;
    utterance.pitch = options?.pitch || 0.95;

    const voices = window.speechSynthesis.getVoices();
    let selectedVoice: SpeechSynthesisVoice | undefined;

    if (options?.preferredVoice) {
      selectedVoice = voices.find((v) => v.name === options.preferredVoice);
    }

    if (!selectedVoice) {
      selectedVoice =
        voices.find(
          (v) =>
            v.lang === 'en-GB' &&
            (v.name.includes('George') ||
              v.name.includes('Oliver') ||
              v.name.includes('David') ||
              v.name.includes('Natural') ||
              v.name.includes('Male'))
        ) ||
        voices.find((v) => v.lang.includes('en-GB')) ||
        voices.find(
          (v) =>
            v.lang === 'en-IN' &&
            (v.name.includes('Ravi') || v.name.includes('Heera') || v.name.includes('Male'))
        ) ||
        voices.find(
          (v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Online'))
        ) ||
        voices.find((v) => v.lang.startsWith('en')) ||
        voices[0];
    }

    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }

    // Workaround for Chromium 15s TTS silence timeout
    clearInterval(this.ttsHeartbeat);
    this.ttsHeartbeat = setInterval(() => {
      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.pause();
        window.speechSynthesis.resume();
      } else {
        clearInterval(this.ttsHeartbeat);
      }
    }, 10000);

    (window as any).__jarvis_active_utterance = utterance;
    this.currentUtterance = utterance;

    let vocalizingFinished = false;
    const finishVocalizing = () => {
      if (vocalizingFinished) return;
      vocalizingFinished = true;
      clearInterval(this.ttsHeartbeat);
      clearInterval(this.ttsSafetyWatcher);
      this.currentUtterance = null;
      (window as any).__jarvis_active_utterance = null;

      // Allow 250ms for room echo to dissipate before unmuting mic
      setTimeout(() => {
        this.isVocalizing = false;
        if (this.isContinuousSessionActive) {
          this.currentMode = 'active_listening';
          this.wakeTriggeredThisTurn = false;
          this.currentCapturedCommand = '';
          this.startIndex = 0;
          this.resetContinuousIdleTimer();
          this.safeStartRecognition();
          this.onContinuousTurnReadyCallback?.();
        } else if (this.wakeWordEnabled || this.currentMode !== 'idle') {
          this.currentMode = 'wake_word';
          this.wakeTriggeredThisTurn = false;
          this.currentCapturedCommand = '';
          this.startIndex = 0;
          this.safeStartRecognition();
        }
      }, 250);
    };

    // Chromium TTS Safety Watcher: Check only after at least 1500ms have elapsed
    // so we never falsely terminate during initial audio stream initialization
    clearInterval(this.ttsSafetyWatcher);
    this.ttsSafetyWatcher = setInterval(() => {
      const elapsed = Date.now() - ttsStartTime;
      if (
        elapsed > 1500 &&
        !window.speechSynthesis.speaking &&
        !window.speechSynthesis.pending &&
        this.isVocalizing
      ) {
        clearInterval(this.ttsSafetyWatcher);
        finishVocalizing();
        options?.onEnd?.();
      }
    }, 500);

    utterance.onstart = () => {
      this.isVocalizing = true;
      options?.onStart?.();
    };

    utterance.onend = () => {
      finishVocalizing();
      options?.onEnd?.();
    };

    utterance.onerror = (e) => {
      finishVocalizing();
      options?.onError?.(e);
    };

    window.speechSynthesis.speak(utterance);
  }

  // --- Recognition Mode Switching & Setup ---
  public startWakeWordMode(
    onWakeWordDetected: (command: string) => void,
    onWakeWordOnly: () => void,
    onWakeActive: () => void,
    onLiveTranscript: (text: string) => void,
    onError?: (err: string) => void
  ) {
    this.wakeWordEnabled = true;
    this.currentMode = 'wake_word';
    this.wakeTriggeredThisTurn = false;
    this.currentCapturedCommand = '';
    this.onWakeWordCallback = onWakeWordDetected;
    this.onWakeWordOnlyCallback = onWakeWordOnly;
    this.onWakeActiveCallback = onWakeActive;
    this.onWakeLiveTranscriptCallback = onLiveTranscript;
    this.onErrorCallback = onError || null;
    this.initMicStream();
    this.initRecognition();
    this.safeStartRecognition();
  }

  public startActiveListening(
    onResult: (transcript: string, isFinal: boolean) => void,
    onLiveTranscript?: (text: string) => void,
    onTimeout?: () => void,
    onError?: (err: string) => void
  ) {
    this.stopSpeaking();
    this.playChime('listen_start');
    this.currentMode = 'active_listening';
    this.onActiveCommandCallback = onResult;
    this.onActiveLiveTranscriptCallback = onLiveTranscript || null;
    this.onErrorCallback = onError || null;
    this.initMicStream();
    this.initRecognition();
    this.safeStartRecognition();

    clearTimeout(this.inactivityTimer);
    this.inactivityTimer = setTimeout(() => {
      this.stopActiveListening();
      onTimeout?.();
    }, 6000);
  }

  public stopActiveListening() {
    clearTimeout(this.silenceTimer);
    clearTimeout(this.inactivityTimer);
    this.silenceTimer = null;
    this.inactivityTimer = null;
    this.playChime('listen_stop');
    this.onActiveCommandCallback = null;
    this.onActiveLiveTranscriptCallback = null;

    if (this.wakeWordEnabled) {
      this.currentMode = 'wake_word';
      this.wakeTriggeredThisTurn = false;
      this.currentCapturedCommand = '';
      this.initRecognition();
      this.safeStartRecognition();
    } else {
      this.currentMode = 'idle';
      try {
        this.recognition?.stop();
      } catch {}
    }
  }

  public startPushToTalk(
    onResult: (transcript: string, isFinal: boolean) => void,
    onLiveTranscript?: (text: string) => void,
    onError?: (err: string) => void
  ) {
    this.stopSpeaking();
    this.playChime('listen_start');
    this.currentMode = 'push_to_talk';
    this.onActiveCommandCallback = onResult;
    this.onActiveLiveTranscriptCallback = onLiveTranscript || null;
    this.onErrorCallback = onError || null;
    this.initMicStream();
    this.initRecognition();
    this.safeStartRecognition();
  }

  public stopPushToTalk() {
    clearTimeout(this.silenceTimer);
    clearTimeout(this.inactivityTimer);
    this.silenceTimer = null;
    this.inactivityTimer = null;
    this.playChime('listen_stop');

    const finalCmd = normalizeWhisperPhonetics(this.currentCapturedCommand.trim());
    if (finalCmd && this.onActiveCommandCallback) {
      this.onActiveCommandCallback(finalCmd, true);
    }
    this.currentCapturedCommand = '';

    if (this.wakeWordEnabled) {
      this.currentMode = 'wake_word';
      this.wakeTriggeredThisTurn = false;
      this.initRecognition();
      this.safeStartRecognition();
    } else {
      this.currentMode = 'idle';
      try {
        this.recognition?.stop();
      } catch {}
    }
  }

  public setWakeWordEnabled(enabled: boolean) {
    this.wakeWordEnabled = enabled;
    if (!enabled && this.currentMode === 'wake_word') {
      this.currentMode = 'idle';
      try {
        this.recognition?.stop();
      } catch {}
    } else if (enabled && this.currentMode === 'idle') {
      this.currentMode = 'wake_word';
      this.wakeTriggeredThisTurn = false;
      this.safeStartRecognition();
    }
  }

  public getCurrentMode(): VoiceMode {
    return this.currentMode;
  }

  public isSpeechRecognitionSupported(): boolean {
    return !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
  }

  public isSpeechSynthesisSupported(): boolean {
    return 'speechSynthesis' in window;
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    if (this.isMuted) {
      this.stopSpeaking();
    }
    return this.isMuted;
  }

  public getMuted(): boolean {
    return this.isMuted;
  }

  public setVadSilenceTimeout(seconds: number) {
    if (seconds > 0) {
      this.vadSilenceTimeout = Math.floor(seconds * 1000);
    }
  }

  public setVoiceFeedback(enabled: boolean) {
    this.voiceFeedback = enabled;
  }

  public setInterruptOnWake(enabled: boolean) {
    this.interruptOnWake = enabled;
  }

  public setMaxRecordingDuration(seconds: number) {
    if (seconds > 5) {
      this.maxRecordingDuration = seconds;
    }
  }

  public setOnInterrupt(callback: () => void) {
    this.onInterruptCallback = callback;
  }

  // --- Continuous ChatGPT Voice Mode Session Protocol ---
  public isContinuousSession(): boolean {
    return this.isContinuousSessionActive;
  }

  public setOnContinuousSessionChange(cb: ((active: boolean) => void) | null) {
    this.onContinuousSessionChangeCallback = cb;
  }

  public setOnContinuousTurnReady(cb: (() => void) | null) {
    this.onContinuousTurnReadyCallback = cb;
  }

  public startContinuousSession(
    onCommand: (transcript: string, isFinal: boolean) => void,
    onLiveTranscript?: (text: string) => void,
    onError?: (err: string) => void
  ) {
    this.isContinuousSessionActive = true;
    this.currentMode = 'active_listening';
    this.onActiveCommandCallback = onCommand;
    this.onActiveLiveTranscriptCallback = onLiveTranscript || null;
    this.onErrorCallback = onError || null;
    this.onContinuousSessionChangeCallback?.(true);

    if (this.voiceFeedback) {
      this.playChime('listen_start');
    }
    this.resetContinuousIdleTimer();
    this.initMicStream();
    this.initRecognition();
    this.safeStartRecognition();
  }

  public resetContinuousIdleTimer() {
    clearTimeout(this.continuousIdleTimer);
    // 45s conversational idle timeout: returns to wake-word standby if user walks away
    this.continuousIdleTimer = setTimeout(() => {
      console.log('[CONTINUOUS_VOICE] 45s idle timeout reached. Returning to wake-word standby.');
      this.stopContinuousSession('idle_timeout');
    }, 45000);
  }

  public stopContinuousSession(
    reason: 'user_action' | 'voice_exit' | 'idle_timeout' = 'user_action'
  ) {
    clearTimeout(this.continuousIdleTimer);
    clearTimeout(this.silenceTimer);
    clearTimeout(this.inactivityTimer);
    this.continuousIdleTimer = null;
    this.silenceTimer = null;
    this.inactivityTimer = null;
    this.isContinuousSessionActive = false;
    this.onContinuousSessionChangeCallback?.(false);

    if (this.voiceFeedback) {
      this.playChime('listen_stop');
    }

    if (reason === 'voice_exit') {
      this.speak('Going to standby, Sir. Say Hey Jarvis whenever you need me.');
    }

    if (this.wakeWordEnabled) {
      this.currentMode = 'wake_word';
      this.wakeTriggeredThisTurn = false;
      this.currentCapturedCommand = '';
      this.initRecognition();
      this.safeStartRecognition();
    } else {
      this.currentMode = 'idle';
      try {
        this.recognition?.stop();
      } catch {}
    }
  }

  public setWhisperBackendEnabled(enabled: boolean) {
    this.whisperBackendEnabled = enabled;
  }

  public getWhisperBackendEnabled(): boolean {
    return this.whisperBackendEnabled;
  }
}

export const speechService = new SpeechService();
