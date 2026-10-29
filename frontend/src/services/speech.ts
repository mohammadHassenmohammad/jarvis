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

// Adaptive Gap Calculator: Analyzes sentence completion and speech pacing
export function calculateAdaptiveSilenceGap(
  text: string,
  isFinalChunk: boolean,
  baseTimeoutMs: number = 1800
): number {
  const cleaned = text.trim();
  if (!cleaned) return Math.max(1600, baseTimeoutMs);

  const words = cleaned.toLowerCase().split(/\s+/);
  const lastWord = words[words.length - 1].replace(/[^a-z]/g, '');

  // Conjunctions, prepositions, and unfinished clause connectors:
  // User is taking a breath or finding words -> provide generous gap so they are not cut off
  const continuationWords = new Set([
    'and', 'or', 'but', 'so', 'because', 'although', 'though', 'since',
    'to', 'for', 'with', 'about', 'in', 'on', 'at', 'by', 'from', 'into', 'onto',
    'that', 'which', 'who', 'whose', 'where', 'when', 'why', 'how', 'what',
    'if', 'then', 'else', 'as', 'than',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'the', 'a', 'an', 'my', 'your', 'his', 'her', 'their', 'our',
    'like', 'also', 'actually', 'mean', 'plus', 'minus', 'such', 'well'
  ]);

  // If ends with comma, ellipsis, or connector word -> generous pause (2500ms)
  if (cleaned.endsWith(',') || cleaned.endsWith('...') || continuationWords.has(lastWord)) {
    return Math.max(2500, baseTimeoutMs + 700);
  }

  // If very short utterance (1-2 words), user is likely just beginning to speak -> allow generous gap (2200ms)
  if (words.length <= 2) {
    return Math.max(2200, baseTimeoutMs + 400);
  }

  // If terminal punctuation exists (. ? !) or final chunk reported, thought is syntactically closed
  if (/[.?!]$/.test(cleaned) || isFinalChunk) {
    return Math.max(1600, Math.min(baseTimeoutMs, 1800));
  }

  // Standard conversational sentence gap
  return Math.max(1800, baseTimeoutMs);
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
  private isMicLocked = false; // Master hardware lock: absolute microphone silence while speaking/thinking
  private isRecognitionRunning = false; // Prevents duplicate concurrent recognition activations
  private lastChimeTime = 0; // Prevents duplicate chime playback
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
  private onVocalizingChangeCallback: ((isSpeaking: boolean) => void) | null = null;

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
  public async ensureMicrophoneAccess(): Promise<boolean> {
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
        if (ctx.state === 'suspended') {
          await ctx.resume();
        }
        const source = ctx.createMediaStreamSource(this.micStream);
        this.analyser = ctx.createAnalyser();
        this.analyser.fftSize = 64;
        this.analyser.smoothingTimeConstant = 0.3;
        source.connect(this.analyser);

        this.startMeterLoop();
      }
      return true;
    } catch (e) {
      console.warn('Microphone permission or stream access notice:', e);
      return false;
    }
  }

  public async initMicStream() {
    await this.ensureMicrophoneAccess();
  }

  private startMeterLoop() {
    if (this.animationFrameId) return;
    const bufferLength = this.analyser?.frequencyBinCount || 32;
    const dataArray = new Uint8Array(bufferLength);
    let smoothedLevel = 0;
    let lastDispatchedLevel = 0;
    let lastDispatchTime = 0;

    const checkLevel = () => {
      if (this.analyser) {
        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        // Noise floor gate: discard ambient background floor (< 4)
        const normalized = Math.min(1.0, Math.max(0, (avg - 4) / 120));
        const target = (this.isVocalizing || this.isSpeakingNow() || this.isMicLocked) ? 0 : normalized;

        // Smooth exponential attack/decay (eliminates high-frequency DOM jitter/glittering)
        smoothedLevel = target > smoothedLevel
          ? smoothedLevel * 0.45 + target * 0.55 // snappy attack
          : smoothedLevel * 0.82 + target * 0.18; // smooth, cinematic decay

        const now = performance.now();
        // Dispatch at a stable ~25fps rate with a deadband threshold to stop DOM glittering
        if (now - lastDispatchTime > 40) {
          if (Math.abs(smoothedLevel - lastDispatchedLevel) > 0.02 || (smoothedLevel === 0 && lastDispatchedLevel !== 0)) {
            lastDispatchedLevel = smoothedLevel;
            lastDispatchTime = now;
            this.audioLevelCallback?.(Number(smoothedLevel.toFixed(2)));
          }
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

        // 0. ABSOLUTE GATE: When microphone is locked or JARVIS is vocalizing (speaking), DO NOT process microphone audio!
        // As requested: "until the speech is not completed it should not listen me until I press ESC to stop it"
        if (this.isMicrophoneLocked()) {
          return;
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
            .replace(/^(hey|hi|hai|hay|ok|okay|hello|yo|wake\s*up|dear)?\s*(jarvis|jar\s*vis|jar\s*ves|javis|travis|service|services|starbucks|jars|java|jobless|charvis|darvis|javes|jarves|harvest)[,:\s]*/i, '')
            .trim();

          // Instant High-Precision Phonetic Normalization (Fayaz, Fowzia, ChatGPT, etc.)
          const displayCommand = normalizeWhisperPhonetics(cleaned || rawText);

          this.currentCapturedCommand = displayCommand;
          this.onActiveLiveTranscriptCallback?.(displayCommand);

          // Conversational Turn-Taking Adaptive Silence Debounce
          clearTimeout(this.silenceTimer);
          const silenceDelay = calculateAdaptiveSilenceGap(displayCommand, isFinalChunk, this.vadSilenceTimeout);

          this.silenceTimer = setTimeout(() => {
            const finalQuery = normalizeWhisperPhonetics(this.currentCapturedCommand || displayCommand).trim();
            this.startIndex = event.results ? event.results.length : 0;
            const callback = this.onActiveCommandCallback;

            if (this.isContinuousSessionActive) {
              this.currentCapturedCommand = '';
              this.silenceTimer = null;
              if (finalQuery.length > 0 && callback) {
                callback(finalQuery, true);
              } else if (finalQuery.length === 0 && /\b(jarvis|jar\s*vis|jar\s*ves|javis|travis)\b/i.test(lowerText)) {
                // If user in continuous mode simply said "Hey Jarvis", acknowledge gracefully
                if (this.voiceFeedback) this.playChime('wake');
                this.speak('Yes, Sir? I am listening.');
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
            /\b(hey|hi|hai|hay|ok|okay|hello|yo|wake\s*up|dear|a|the)?\s*(jarvis|jar\s*vis|jar\s*ves|javis|travis|service|services|starbucks|jars|java|jobless|charvis|darvis|javes|jarves|harvest)\b/i;

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
              /\b(jarvis|jar\s*vis|jar\s*ves|javis|travis|service|services|starbucks|jars|java|jobless|charvis|darvis|javes|jarves|harvest)\b/i
            );
            let commandText = '';
            if (match && match.index !== undefined) {
              const wakeEnd = match.index + match[0].length;
              commandText = rawText.slice(wakeEnd).replace(/^[,:\s]+/, '').trim();
            } else {
              commandText = rawText
                .replace(/^(hey|hi|hai|hay|ok|okay|hello|yo|wake\s*up|dear)?\s*(jarvis|jar\s*vis|jar\s*ves|javis|travis|service|services|starbucks|jars|java|jobless|charvis|darvis|javes|jarves|harvest)[,:\s]*/i, '')
                .trim();
            }

            const normalizedCommand = normalizeWhisperPhonetics(commandText);
            this.currentCapturedCommand = normalizedCommand;
            this.onWakeLiveTranscriptCallback?.(normalizedCommand);

            clearTimeout(this.silenceTimer);
            const silenceDelay = calculateAdaptiveSilenceGap(normalizedCommand, isFinalChunk, this.vadSilenceTimeout);

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

      this.recognition.onstart = () => {
        this.isRecognitionRunning = true;
      };

      this.recognition.onerror = (event: any) => {
        if (event.error === 'not-allowed') {
          this.onErrorCallback?.(
            'Microphone access denied. Please click the Arc Reactor to grant microphone access.'
          );
        } else if (event.error === 'network') {
          console.warn('Speech recognition network glitch, reconnecting...');
        } else if (event.error === 'no-speech') {
          // Conversational silence pause - handled automatically by onend
        }
      };

      this.recognition.onend = () => {
        this.isRecognitionRunning = false;
        this.startIndex = 0;
        // If microphone is locked, system is vocalizing, or mode is idle, DO NOT restart
        if (this.isMicrophoneLocked() || this.currentMode === 'idle') {
          return;
        }
        clearTimeout(this.restartTimeout);
        this.restartTimeout = setTimeout(() => {
          if (!this.isMicrophoneLocked() && this.currentMode !== 'idle') {
            this.safeStartRecognition();
          }
        }, 150);
      };
    } catch (e) {
      console.warn('Speech recognition initialization error:', e);
    }
  }

  public safeStartRecognition() {
    if (this.currentMode === 'idle' || this.isMicrophoneLocked()) return;
    if (this.isRecognitionRunning && this.recognition) return;

    if (!this.recognition) {
      this.initRecognition();
    }
    try {
      this.recognition?.start();
      this.isRecognitionRunning = true;
    } catch (e: any) {
      if (e?.name === 'InvalidStateError') {
        // Recognition is already active in browser; flag running and do not recreate
        this.isRecognitionRunning = true;
      } else {
        console.warn('[SPEECH] Error starting recognition, creating fresh session:', e);
        this.initRecognition();
        try {
          this.recognition?.start();
          this.isRecognitionRunning = true;
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

    if (this.currentMode !== 'idle' && !this.isMicrophoneLocked()) {
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
    const nowMs = Date.now();
    // Prevent duplicate listening start chimes within 1.8 seconds
    if (type === 'listen_start' && nowMs - this.lastChimeTime < 1800) {
      return;
    }
    if (type === 'listen_start') {
      this.lastChimeTime = nowMs;
    }

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

  // --- Master Microphone Lock Gate (Disables mic during speech and thinking) ---
  public lockMicrophone(_reason?: string) {
    this.isMicLocked = true;
    this.isRecognitionRunning = false;
    if (_reason) {
      console.debug('[MIC_LOCK] Locked:', _reason);
    }
    clearTimeout(this.silenceTimer);
    clearTimeout(this.inactivityTimer);
    clearTimeout(this.restartTimeout);
    this.silenceTimer = null;
    this.inactivityTimer = null;
    this.restartTimeout = null;
    this.currentCapturedCommand = '';
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
    } catch {}
  }

  public unlockMicrophone() {
    this.isMicLocked = false;
    this.isVocalizing = false;
    this.isRecognitionRunning = false;
  }

  public isMicrophoneLocked(): boolean {
    return this.isMicLocked || this.isVocalizing || !!this.currentUtterance;
  }

  // --- Voice Synthesis (TTS) with Echo-Shielding and Chromium Keep-Alive ---
  public stopSpeaking() {
    clearInterval(this.ttsHeartbeat);
    clearTimeout(this.ttsSafetyWatcher);
    this.ttsHeartbeat = null;
    this.ttsSafetyWatcher = null;
    this.currentUtterance = null;
    (window as any).__jarvis_active_utterance = null;

    if (this.isSpeechSynthesisSupported()) {
      try {
        window.speechSynthesis.cancel();
      } catch {}
    }

    this.isVocalizing = false;
    this.isMicLocked = false;
    this.isRecognitionRunning = false;
    this.onVocalizingChangeCallback?.(false);
    this.onInterruptCallback?.();

    // Immediately resume listening after interruption!
    // As requested: "until I press esc to stop it once it gets over again it start listen to me"
    setTimeout(() => {
      this.currentMode = this.isContinuousSessionActive ? 'active_listening' : (this.wakeWordEnabled ? 'wake_word' : 'idle');
      this.wakeTriggeredThisTurn = false;
      this.currentCapturedCommand = '';
      this.startIndex = 0;
      if (this.isContinuousSessionActive) {
        this.resetContinuousIdleTimer();
      }
      this.safeStartRecognition();
      if (this.voiceFeedback) {
        this.playChime('listen_start');
      }
    }, 120);
  }

  public setOnVocalizingChange(cb: ((isSpeaking: boolean) => void) | null) {
    this.onVocalizingChangeCallback = cb;
  }

  public isSpeakingNow(): boolean {
    return this.isVocalizing || !!this.currentUtterance;
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

    if (!cleanText) {
      this.unlockMicrophone();
      options?.onEnd?.();
      return;
    }

    clearInterval(this.ttsHeartbeat);
    clearTimeout(this.ttsSafetyWatcher);

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

    // LOCK MICROPHONE COMPLETELY: System is vocalizing through speakers
    this.lockMicrophone('TTS speech vocalization starting');
    this.isVocalizing = true;
    this.onVocalizingChangeCallback?.(true);
    const ttsStartTime = Date.now();

    const words = cleanText.split(/\s+/).filter(Boolean).length;
    const rate = options?.rate || 1.02;
    // Average speech pace: ~135 words/minute at 1.0x -> ~440ms per word + 600ms base padding
    const estimatedDurationMs = Math.max(1800, Math.round((words * 440) / rate) + 600);

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = rate;
    utterance.pitch = options?.pitch || 0.98;

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

      // Failsafe: if speechSynthesis is still reporting speaking, extend by 350ms
      if (window.speechSynthesis && window.speechSynthesis.speaking) {
        setTimeout(() => {
          vocalizingFinished = false;
          finishVocalizing();
        }, 350);
        return;
      }

      vocalizingFinished = true;
      clearInterval(this.ttsHeartbeat);
      clearTimeout(this.ttsSafetyWatcher);
      this.ttsHeartbeat = null;
      this.ttsSafetyWatcher = null;
      this.currentUtterance = null;
      (window as any).__jarvis_active_utterance = null;

      // Clean 500ms acoustic dissipation cooldown to ensure speakers are 100% silent
      // and room echo has cleared before the mic opens
      setTimeout(() => {
        this.isVocalizing = false;
        this.isMicLocked = false;
        this.currentMode = this.isContinuousSessionActive ? 'active_listening' : (this.wakeWordEnabled ? 'wake_word' : 'idle');
        this.wakeTriggeredThisTurn = false;
        this.currentCapturedCommand = '';
        this.startIndex = 0;
        if (this.isContinuousSessionActive) {
          this.resetContinuousIdleTimer();
        }
        this.safeStartRecognition();

        this.onVocalizingChangeCallback?.(false);
        if (this.isContinuousSessionActive) {
          this.onContinuousTurnReadyCallback?.();
        }
        if (this.voiceFeedback && this.isContinuousSessionActive) {
          this.playChime('listen_start');
        }
        options?.onEnd?.();
      }, 500);
    };

    // Watchdog Failsafe: Only triggers if onend never fired and a massive timeout has passed
    clearTimeout(this.ttsSafetyWatcher);
    this.ttsSafetyWatcher = setTimeout(() => {
      if (this.isVocalizing) {
        console.warn('[SPEECH] Watchdog timer elapsed; releasing vocalizing lock.');
        finishVocalizing();
      }
    }, Math.max(12000, estimatedDurationMs * 2 + 5000));

    utterance.onstart = () => {
      this.isVocalizing = true;
      this.isMicLocked = true;
      options?.onStart?.();
    };

    utterance.onend = () => {
      const elapsed = Date.now() - ttsStartTime;
      // In some versions of Chromium on Windows, onend can fire prematurely if the utterance was chunked.
      // If elapsed time is significantly less than minimum physical speech duration, wait out the remaining duration:
      const remainingMs = Math.max(0, (estimatedDurationMs * 0.8) - elapsed);
      if (remainingMs > 200) {
        setTimeout(() => {
          finishVocalizing();
        }, remainingMs);
      } else {
        finishVocalizing();
      }
    };

    utterance.onerror = (e) => {
      console.warn('[SPEECH] SpeechSynthesis error:', e);
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
    this.isMicLocked = false;
    this.isVocalizing = false;
    this.wakeTriggeredThisTurn = false;
    this.currentCapturedCommand = '';
    this.startIndex = 0;
    this.onWakeWordCallback = onWakeWordDetected;
    this.onWakeWordOnlyCallback = onWakeWordOnly;
    this.onWakeActiveCallback = onWakeActive;
    this.onWakeLiveTranscriptCallback = onLiveTranscript;
    this.onErrorCallback = onError || null;
    this.initMicStream();
    if (!this.recognition) {
      this.initRecognition();
    }
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

  public getInterruptOnWake(): boolean {
    return this.interruptOnWake;
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
    if (!this.recognition) {
      this.initRecognition();
    }
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
