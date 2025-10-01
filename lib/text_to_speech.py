import os
from google.cloud import texttospeech
from dotenv import load_dotenv
import tempfile
import pygame
from typing import Optional
import time
import json
from datetime import datetime
from pathlib import Path

class TextToSpeech:
    """Text-to-speech handler using Google Cloud TTS with usage tracking."""
    
    # Voice tier definitions with monthly free character limits
    VOICE_TIERS = {
        'standard': {
            'free_chars': 4_000_000,  # 4 million characters per month
            'patterns': ['Standard'],
            'price_per_million': 4.00  # USD (after free tier)
        },
        'wavenet': {
            'free_chars': 1_000_000,  # 1 million characters per month
            'patterns': ['WaveNet'],
            'price_per_million': 16.00  # USD (after free tier)
        },
        'neural2': {
            'free_chars': 1_000_000,  # 1 million characters per month
            'patterns': ['Neural2'],
            'price_per_million': 16.00  # USD (after free tier)
        },
        'studio': {
            'free_chars': 100_000,  # 100k characters per month
            'patterns': ['Studio'],
            'price_per_million': 160.00  # USD (after free tier)
        },
        'journey': {
            'free_chars': 100_000,  # 100k characters per month
            'patterns': ['Journey'],
            'price_per_million': 100.00  # USD (after free tier)
        },
        'chirp': {
            'free_chars': 100_000,  # 100k characters per month
            'patterns': ['Chirp', 'Chirp3'],
            'price_per_million': 100.00  # USD (after free tier)
        },
        'polyglot': {
            'free_chars': 100_000,  # 100k characters per month
            'patterns': ['Polyglot'],
            'price_per_million': 100.00  # USD (after free tier)
        }
    }
    
    def __init__(self, voice_name: str = "en-US-Standard-A", language_code: str = "en-US", 
                 speaking_rate: float = 1.0, pitch: float = 0.0, 
                 enforce_free_tier: bool = True, usage_file: str = "tts_usage.json",
                 fallback_voice: Optional[str] = None):
        """
        Initialize the Text-to-Speech system.
        
        :param voice_name: Google Cloud TTS voice name (e.g., 'en-US-Standard-A', 'en-GB-Standard-A')
        :param language_code: Language code (e.g., 'en-US', 'en-GB', 'nb-NO' for Norwegian)
        :param speaking_rate: Speaking rate (0.25 to 4.0, default 1.0)
        :param pitch: Voice pitch (-20.0 to 20.0, default 0.0)
        :param enforce_free_tier: If True, block requests that would exceed free tier
        :param usage_file: Path to file for tracking character usage
        :param fallback_voice: Optional fallback voice to use when primary voice quota is exhausted
        """
        print("🔊 Initializing Google Cloud Text-to-Speech...")
        
        # Load environment variables
        load_dotenv()
        
        # Check if credentials are set
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_path:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS environment variable is not set. "
                "Please set it in your .env file to point to your Google Cloud credentials JSON file."
            )
        
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Google Cloud credentials file not found at: {credentials_path}. "
                f"Please ensure the file exists and the path in .env is correct."
            )
        
        try:
            # Initialize the Google Cloud TTS client
            self.client = texttospeech.TextToSpeechClient()
            
            # Store voice configuration
            self.primary_voice_name = voice_name  # Original preferred voice
            self.voice_name = voice_name  # Currently active voice
            self.fallback_voice = fallback_voice  # Fallback voice when quota exhausted
            self.language_code = language_code
            self.speaking_rate = speaking_rate
            self.pitch = pitch
            self.enforce_free_tier = enforce_free_tier
            self.usage_file = usage_file
            self.using_fallback = False  # Track if we're currently using fallback
            
            # Determine voice tiers
            self.voice_tier = self._determine_voice_tier(voice_name)
            self.fallback_tier = self._determine_voice_tier(fallback_voice) if fallback_voice else None
            
            # Load usage data
            self.usage_data = self._load_usage()
            
            # Initialize pygame mixer for audio playback
            pygame.mixer.init()
            
            # Test the connection by listing available voices (optional)
            self._test_connection()
            
            # Check if we should start with fallback due to quota
            self._check_and_switch_voice()
            
            print(f"✅ Text-to-Speech initialized successfully!")
            print(f"🗣️  Primary Voice: {self.primary_voice_name} ({language_code})")
            print(f"💎 Primary Tier: {self.voice_tier.upper()}")
            print(f"📊 Free Tier Limit: {self.VOICE_TIERS[self.voice_tier]['free_chars']:,} chars/month")
            
            if self.fallback_voice:
                print(f"🔄 Fallback Voice: {self.fallback_voice}")
                print(f"💎 Fallback Tier: {self.fallback_tier.upper()}")
                print(f"📊 Fallback Limit: {self.VOICE_TIERS[self.fallback_tier]['free_chars']:,} chars/month")
            
            self._print_usage_stats()
            
        except Exception as e:
            print(f"❌ Error initializing Google Cloud TTS: {e}")
            raise
    
    def _determine_voice_tier(self, voice_name: str) -> str:
        """Determine which tier a voice belongs to based on its name."""
        for tier, info in self.VOICE_TIERS.items():
            for pattern in info['patterns']:
                if pattern in voice_name:
                    return tier
        # Default to standard if no pattern matches
        return 'standard'
    
    def _load_usage(self) -> dict:
        """Load usage data from file."""
        if os.path.exists(self.usage_file):
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    # Check if we need to reset for new month
                    if data.get('month') != datetime.now().strftime('%Y-%m'):
                        return self._create_new_usage_data()
                    return data
            except Exception as e:
                print(f"⚠️  Could not load usage data: {e}. Creating new file.")
        return self._create_new_usage_data()
    
    def _create_new_usage_data(self) -> dict:
        """Create fresh usage data structure."""
        return {
            'month': datetime.now().strftime('%Y-%m'),
            'tiers': {tier: 0 for tier in self.VOICE_TIERS.keys()},
            'total_requests': 0,
            'last_updated': datetime.now().isoformat()
        }
    
    def _save_usage(self):
        """Save usage data to file."""
        try:
            self.usage_data['last_updated'] = datetime.now().isoformat()
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save usage data: {e}")
    
    def _update_usage(self, char_count: int):
        """Update usage statistics."""
        # Update usage for the currently active voice tier
        active_tier = self._determine_voice_tier(self.voice_name)
        self.usage_data['tiers'][active_tier] += char_count
        self.usage_data['total_requests'] += 1
        self._save_usage()
    
    def _check_and_switch_voice(self) -> bool:
        """
        Check if we should switch between primary and fallback voice.
        Returns True if voice was switched.
        """
        if not self.fallback_voice:
            return False
        
        # Check if it's a new month - if so, switch back to primary
        if self.using_fallback and self.usage_data.get('month') == datetime.now().strftime('%Y-%m'):
            # New month detected, check if primary voice has quota
            primary_usage = self.usage_data['tiers'][self.voice_tier]
            primary_limit = self.VOICE_TIERS[self.voice_tier]['free_chars']
            
            if primary_usage == 0:  # Fresh month, switch back to primary
                self.voice_name = self.primary_voice_name
                self.using_fallback = False
                print(f"🔄 New month detected! Switched back to primary voice: {self.primary_voice_name}")
                return True
        
        # Check if primary voice is exhausted and we should use fallback
        if not self.using_fallback:
            primary_usage = self.usage_data['tiers'][self.voice_tier]
            primary_limit = self.VOICE_TIERS[self.voice_tier]['free_chars']
            
            # If primary is at or near limit, switch to fallback
            if primary_usage >= primary_limit * 0.99:  # 99% threshold
                fallback_usage = self.usage_data['tiers'][self.fallback_tier]
                fallback_limit = self.VOICE_TIERS[self.fallback_tier]['free_chars']
                
                if fallback_usage < fallback_limit:
                    self.voice_name = self.fallback_voice
                    self.using_fallback = True
                    print(f"🔄 Primary voice quota exhausted. Switching to fallback: {self.fallback_voice}")
                    return True
        
        return False
    
    def _check_quota(self, text: str) -> tuple[bool, str]:
        """
        Check if the request would exceed free tier quota.
        Automatically switches to fallback if available and primary is exhausted.
        
        :param text: Text to synthesize
        :return: Tuple of (allowed: bool, message: str)
        """
        if not self.enforce_free_tier:
            return True, ""
        
        char_count = len(text)
        active_tier = self._determine_voice_tier(self.voice_name)
        current_usage = self.usage_data['tiers'][active_tier]
        free_limit = self.VOICE_TIERS[active_tier]['free_chars']
        
        if current_usage + char_count > free_limit:
            # Try to switch to fallback voice if available
            if self.fallback_voice and not self.using_fallback:
                fallback_tier = self._determine_voice_tier(self.fallback_voice)
                fallback_usage = self.usage_data['tiers'][fallback_tier]
                fallback_limit = self.VOICE_TIERS[fallback_tier]['free_chars']
                
                if fallback_usage + char_count <= fallback_limit:
                    # Switch to fallback
                    self.voice_name = self.fallback_voice
                    self.using_fallback = True
                    print(f"\n🔄 Primary voice quota exhausted. Automatically switching to fallback: {self.fallback_voice}")
                    print(f"   Primary ({self.voice_tier.upper()}): {current_usage:,}/{free_limit:,} used")
                    print(f"   Fallback ({fallback_tier.upper()}): {fallback_usage:,}/{fallback_limit:,} used\n")
                    return True, ""
            
            # No fallback available or fallback also exhausted
            remaining = free_limit - current_usage
            fallback_info = ""
            if self.fallback_voice:
                fallback_tier = self._determine_voice_tier(self.fallback_voice)
                fallback_usage = self.usage_data['tiers'][fallback_tier]
                fallback_limit = self.VOICE_TIERS[fallback_tier]['free_chars']
                fallback_info = f"   Fallback ({fallback_tier.upper()}): {fallback_usage:,}/{fallback_limit:,} used\n"
            
            message = (
                f"❌ FREE TIER LIMIT EXCEEDED!\n"
                f"   Active Voice: {self.voice_name}\n"
                f"   Voice Tier: {active_tier.upper()}\n"
                f"   This request: {char_count:,} characters\n"
                f"   Current usage: {current_usage:,}/{free_limit:,} characters\n"
                f"   Remaining: {remaining:,} characters\n"
                f"{fallback_info}"
                f"   To continue using TTS, either:\n"
                f"   1. Wait until next month (resets on 1st)\n"
                f"   2. Switch to a different voice with available quota\n"
                f"   3. Set enforce_free_tier=False (will incur charges)\n"
            )
            return False, message
        
        return True, ""
    
    def _print_usage_stats(self):
        """Print current usage statistics."""
        print(f"📊 Monthly Usage ({self.usage_data['month']}):")
        
        # Show primary voice stats
        primary_usage = self.usage_data['tiers'][self.voice_tier]
        primary_limit = self.VOICE_TIERS[self.voice_tier]['free_chars']
        primary_percentage = (primary_usage / primary_limit) * 100
        primary_remaining = primary_limit - primary_usage
        
        active_marker = "🎤" if not self.using_fallback else "💤"
        print(f"   {active_marker} Primary ({self.voice_tier.upper()}): {primary_usage:,}/{primary_limit:,} chars ({primary_percentage:.1f}%)")
        
        # Show fallback voice stats if configured
        if self.fallback_voice and self.fallback_tier:
            fallback_usage = self.usage_data['tiers'][self.fallback_tier]
            fallback_limit = self.VOICE_TIERS[self.fallback_tier]['free_chars']
            fallback_percentage = (fallback_usage / fallback_limit) * 100
            
            active_marker = "🎤" if self.using_fallback else "💤"
            print(f"   {active_marker} Fallback ({self.fallback_tier.upper()}): {fallback_usage:,}/{fallback_limit:,} chars ({fallback_percentage:.1f}%)")
        
        # Show status of active voice
        if self.using_fallback:
            print(f"   ℹ️  Currently using: FALLBACK voice")
        else:
            print(f"   ℹ️  Currently using: PRIMARY voice")
            if primary_percentage > 80:
                print(f"   ⚠️  WARNING: Primary voice approaching limit! Will auto-switch to fallback.")
        
        if self.enforce_free_tier:
            print(f"   🛡️  Free tier protection: ENABLED")
        else:
            print(f"   ⚠️  Free tier protection: DISABLED (charges may apply)")
    
    def get_usage_stats(self) -> dict:
        """Get detailed usage statistics."""
        active_tier = self._determine_voice_tier(self.voice_name)
        stats = {
            'month': self.usage_data['month'],
            'active_voice': self.voice_name,
            'using_fallback': self.using_fallback,
            'primary_voice': self.primary_voice_name,
            'primary_tier': self.voice_tier,
            'primary_usage': self.usage_data['tiers'][self.voice_tier],
            'primary_limit': self.VOICE_TIERS[self.voice_tier]['free_chars'],
            'primary_remaining': self.VOICE_TIERS[self.voice_tier]['free_chars'] - self.usage_data['tiers'][self.voice_tier],
            'total_requests': self.usage_data['total_requests'],
            'all_tiers': self.usage_data['tiers']
        }
        stats['primary_percentage_used'] = (stats['primary_usage'] / stats['primary_limit']) * 100
        
        if self.fallback_voice:
            stats['fallback_voice'] = self.fallback_voice
            stats['fallback_tier'] = self.fallback_tier
            stats['fallback_usage'] = self.usage_data['tiers'][self.fallback_tier]
            stats['fallback_limit'] = self.VOICE_TIERS[self.fallback_tier]['free_chars']
            stats['fallback_remaining'] = stats['fallback_limit'] - stats['fallback_usage']
            stats['fallback_percentage_used'] = (stats['fallback_usage'] / stats['fallback_limit']) * 100
        
        return stats
    
    def get_active_voice_info(self) -> dict:
        """Get information about the currently active voice."""
        return {
            'voice_name': self.voice_name,
            'is_primary': not self.using_fallback,
            'is_fallback': self.using_fallback,
            'primary_voice': self.primary_voice_name,
            'fallback_voice': self.fallback_voice
        }
    
    def _test_connection(self):
        """Test the connection to Google Cloud TTS API."""
        try:
            # This will fail if credentials are invalid
            response = self.client.list_voices()
            print(f"✅ Successfully connected to Google Cloud TTS API")
            print(f"📋 Available voices: {len(response.voices)} voices found")
        except Exception as e:
            print(f"⚠️  Warning: Could not verify connection to Google Cloud TTS: {e}")
    
    def set_voice(self, voice_name: str, language_code: Optional[str] = None):
        """
        Change the voice settings.
        
        :param voice_name: New voice name
        :param language_code: Optional new language code
        """
        self.voice_name = voice_name
        if language_code:
            self.language_code = language_code
        print(f"🗣️  Voice updated to: {voice_name} ({self.language_code})")
    
    def set_speaking_rate(self, rate: float):
        """
        Change the speaking rate.
        
        :param rate: Speaking rate (0.25 to 4.0)
        """
        if 0.25 <= rate <= 4.0:
            self.speaking_rate = rate
            print(f"⚡ Speaking rate set to: {rate}x")
        else:
            raise ValueError("Speaking rate must be between 0.25 and 4.0")
    
    def set_pitch(self, pitch: float):
        """
        Change the voice pitch.
        
        :param pitch: Voice pitch (-20.0 to 20.0)
        """
        if -20.0 <= pitch <= 20.0:
            self.pitch = pitch
            print(f"🎵 Pitch set to: {pitch}")
        else:
            raise ValueError("Pitch must be between -20.0 and 20.0")
    
    def synthesize_to_file(self, text: str, output_file: str) -> str:
        """
        Synthesize text to an audio file.
        
        :param text: Text to synthesize
        :param output_file: Path to save the audio file
        :return: Path to the saved audio file
        """
        if not text or not text.strip():
            print("⚠️  Warning: Empty text provided, skipping synthesis")
            return ""
        
        # Check quota before making API call
        allowed, message = self._check_quota(text)
        if not allowed:
            print(message)
            return ""
        
        try:
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name
            )
            
            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=self.speaking_rate,
                pitch=self.pitch
            )
            
            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Write the response to the output file
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            
            # Update usage tracking
            self._update_usage(len(text))
            
            return output_file
            
        except Exception as e:
            print(f"❌ Error synthesizing speech: {e}")
            return ""
    
    def speak(self, text: str, wait_until_done: bool = True) -> bool:
        """
        Convert text to speech and play it immediately.
        
        :param text: Text to speak
        :param wait_until_done: If True, block until speech is finished
        :return: True if successful, False otherwise
        """
        if not text or not text.strip():
            return False
        
        try:
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_filename = temp_file.name
            
            # Synthesize speech to the temp file
            audio_file = self.synthesize_to_file(text, temp_filename)
            
            if not audio_file:
                return False
            
            # Play the audio file
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for playback to finish if requested
            if wait_until_done:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            
            # Clean up the temporary file after playback
            if wait_until_done:
                try:
                    os.remove(temp_filename)
                except:
                    pass  # Ignore errors when deleting temp files
            
            return True
            
        except Exception as e:
            print(f"❌ Error speaking text: {e}")
            return False
    
    def speak_streaming(self, text_generator, chunk_on: str = "."):
        """
        Speak text as it's being generated (streaming mode).
        This accumulates text until a sentence boundary and speaks it.
        
        :param text_generator: Generator that yields text tokens
        :param chunk_on: Character to chunk on (default: "." for sentences)
        """
        buffer = ""
        
        for token in text_generator:
            buffer += token.content
            
            # Check if we have a complete sentence
            if chunk_on in buffer:
                # Find the last occurrence of the chunk character
                last_chunk_idx = buffer.rfind(chunk_on)
                
                # Extract the complete sentence(s)
                to_speak = buffer[:last_chunk_idx + 1].strip()
                
                # Keep the remainder for the next iteration
                buffer = buffer[last_chunk_idx + 1:]
                
                # Speak the complete sentence(s)
                if to_speak:
                    # Print the text being spoken
                    print(to_speak, end="", flush=True)
                    # Speak it (non-blocking to continue receiving tokens)
                    self.speak(to_speak, wait_until_done=True)
        
        # Speak any remaining text in the buffer
        if buffer.strip():
            print(buffer.strip(), end="", flush=True)
            self.speak(buffer.strip(), wait_until_done=True)
        
        print()  # New line at the end
    
    def list_available_voices(self, language_code: Optional[str] = None, show_pricing: bool = True):
        """
        List all available voices from Google Cloud TTS with pricing tiers.
        
        :param language_code: Optional language code to filter voices (e.g., 'en-US', 'en-GB')
        :param show_pricing: If True, show pricing tier information
        """
        try:
            response = self.client.list_voices()
            
            print("\n📋 Available Google Cloud TTS Voices:")
            if show_pricing:
                print("💡 Pricing Tiers (free characters per month):")
                for tier, info in self.VOICE_TIERS.items():
                    print(f"   {tier.upper()}: {info['free_chars']:,} chars/month")
            print("-" * 80)
            
            # Group voices by tier
            voices_by_tier = {tier: [] for tier in self.VOICE_TIERS.keys()}
            other_voices = []
            
            for voice in response.voices:
                # Filter by language if specified
                if language_code:
                    # Check if any of the voice's languages match (prefix match)
                    if not any(lang.startswith(language_code) for lang in voice.language_codes):
                        continue
                
                # Determine tier
                tier = self._determine_voice_tier(voice.name)
                if tier in voices_by_tier:
                    voices_by_tier[tier].append(voice)
                else:
                    other_voices.append(voice)
            
            # Print voices grouped by tier (most free characters first)
            for tier in ['standard', 'wavenet', 'neural2', 'journey', 'chirp', 'studio', 'polyglot']:
                if voices_by_tier[tier]:
                    print(f"\n🎯 {tier.upper()} VOICES ({self.VOICE_TIERS[tier]['free_chars']:,} free/month):")
                    print("-" * 80)
                    for voice in voices_by_tier[tier]:
                        print(f"Voice: {voice.name}")
                        print(f"  Languages: {', '.join(voice.language_codes)}")
                        print(f"  Gender: {texttospeech.SsmlVoiceGender(voice.ssml_gender).name}")
                        print(f"  Sample Rate: {voice.natural_sample_rate_hertz} Hz")
                        print()
            
            if other_voices:
                print(f"\n📌 OTHER VOICES:")
                print("-" * 80)
                for voice in other_voices:
                    print(f"Voice: {voice.name}")
                    print(f"  Languages: {', '.join(voice.language_codes)}")
                    print()
                
        except Exception as e:
            print(f"❌ Error listing voices: {e}")
    
    def stop(self):
        """Stop any currently playing audio."""
        pygame.mixer.music.stop()
    
    def __del__(self):
        """Cleanup when the object is destroyed."""
        try:
            pygame.mixer.quit()
        except:
            pass
