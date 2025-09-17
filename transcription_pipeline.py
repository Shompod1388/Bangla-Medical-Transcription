"""
Transcription pipeline module for Bengali-to-English Medical Transcription
with real speech recognition capabilities
"""
import os
import time
import threading
import numpy as np
import queue
import tempfile
import wave
import pyaudio
import speech_recognition as sr
from googletrans import Translator

class TranscriptionPipeline:
    """
    Handles the audio capture, speech recognition, and translation pipeline.
    
    This implementation uses the microphone to capture real audio and
    attempts to recognize Bengali speech using available speech recognition APIs.
    """
    
    def __init__(self):
        """Initialize the transcription pipeline"""
        self.is_running = False
        self.is_paused = False
        self.audio_queue = queue.Queue()
        self.lock = threading.Lock()
        self.current_bengali_text = ""
        self.current_english_text = ""
        
        # Callback functions for updates
        self.on_bengali_update = None
        self.on_english_update = None
        
        # Audio settings
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000  # Common rate for speech recognition
        self.chunk_size = 1024  # Smaller chunks for Mac M1
        self.audio = pyaudio.PyAudio()
        
        # Speech recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300  # Adjust based on environment
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.5  # Shorter pauses for medical speech
        
        # Translation
        self.translator = Translator()
        
        # Bengali medical terms and their English translations (fallback)
        self.bengali_medical_terms = {


        }
        
        # Initialize threads
        self.recording_thread = None
        self.processing_thread = None
        
    def start(self):
        """Start audio capture and transcription"""
        self.is_running = True
        self.is_paused = False
        
        # Start the recording thread
        self.recording_thread = threading.Thread(target=self._recording_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        # Start the processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        print("Transcription started")
        
    def stop(self):
        """Stop audio capture and transcription"""
        self.is_running = False
        self.is_paused = False
        
        # Wait for threads to end
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)
            self.recording_thread = None
            
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
            self.processing_thread = None
        
        print("Transcription stopped")
        
        # Return the current text
        return self.current_bengali_text, self.current_english_text
        
    def pause(self):
        """Pause transcription"""
        self.is_paused = True
        print("Transcription paused")
        
    def resume(self):
        """Resume transcription"""
        self.is_paused = False
        print("Transcription resumed")
        
    def _recording_loop(self):
        """Continuously record audio from the microphone"""
        try:
            # Open the microphone stream
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            print("Microphone stream opened")
            
            # Main recording loop
            while self.is_running:
                if not self.is_paused:
                    # Read audio data
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Calculate audio level (for visualization)
                    audio_array = np.frombuffer(data, dtype=np.int16)
                    audio_level = np.abs(audio_array).mean() / 32768.0  # Normalize to 0-1
                    
                    # Add to queue
                    self.audio_queue.put((data, audio_level))
                else:
                    # When paused, just sleep
                    time.sleep(0.1)
            
            # Clean up
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"Error in recording loop: {str(e)}")
            
    def _processing_loop(self):
        """Process recorded audio for speech recognition"""
        # Buffer for collecting audio segments
        audio_buffer = []
        last_process_time = time.time()
        
        try:
            while self.is_running:
                # Process audio in chunks
                current_time = time.time()
                process_interval = 3.0  # Process every 3 seconds
                
                # Collect audio data from queue
                while not self.audio_queue.empty():
                    data, level = self.audio_queue.get()
                    audio_buffer.append(data)
                
                # Process if we have enough audio and enough time has passed
                if audio_buffer and (current_time - last_process_time) >= process_interval:
                    # Create a temporary WAV file
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                        temp_filename = temp_file.name
                        
                    # Write audio buffer to WAV file
                    with wave.open(temp_filename, 'wb') as wf:
                        wf.setnchannels(self.channels)
                        wf.setsampwidth(self.audio.get_sample_size(self.format))
                        wf.setframerate(self.rate)
                        wf.writeframes(b''.join(audio_buffer))
                    
                    # Recognize speech from the WAV file
                    try:
                        with sr.AudioFile(temp_filename) as source:
                            audio_data = self.recognizer.record(source)
                            
                            # Try to recognize Bengali speech
                            try:
                                # Try Google's speech recognition with Bengali language
                                text = self.recognizer.recognize_google(audio_data, language="bn-BD")
                                
                                if text:
                                    # Update Bengali text
                                    if not self.current_bengali_text:
                                        self.current_bengali_text = text
                                    else:
                                        self.current_bengali_text += " " + text
                                    
                                    # Notify listeners
                                    if self.on_bengali_update:
                                        self.on_bengali_update(self.current_bengali_text)
                                    
                                    # Translate to English
                                    try:
                                        translation = self.translator.translate(text, src='bn', dest='en')
                                        english_text = translation.text
                                        
                                        # Update English text
                                        if not self.current_english_text:
                                            self.current_english_text = english_text
                                        else:
                                            self.current_english_text += " " + english_text
                                        
                                        # Notify listeners
                                        if self.on_english_update:
                                            self.on_english_update(self.current_english_text)
                                            
                                    except Exception as e:
                                        print(f"Translation error: {str(e)}")
                                        # Use fallback translation if available
                                        if text in self.bengali_medical_terms:
                                            english_text = self.bengali_medical_terms[text]
                                            self.current_english_text += " " + english_text
                                            if self.on_english_update:
                                                self.on_english_update(self.current_english_text)
                            
                            except sr.UnknownValueError:
                                print("Speech Recognition could not understand audio")
                            except sr.RequestError as e:
                                print(f"Could not request results from Google Speech Recognition service; {e}")
                    
                    except Exception as e:
                        print(f"Error processing audio file: {str(e)}")
                    
                    # Clean up
                    try:
                        os.unlink(temp_filename)
                    except:
                        pass
                    
                    # Reset for next processing
                    audio_buffer = []
                    last_process_time = current_time
                
                # Sleep to prevent CPU overuse
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error in processing loop: {str(e)}")
            
    def update_bengali_text(self, text):
        """
        Update the Bengali text and generate a new English translation.
        This is used when the user manually edits the Bengali text.
        
        Args:
            text (str): The new Bengali text
            
        Returns:
            str: The English translation
        """
        self.current_bengali_text = text
        
        # Translate to English
        try:
            translation = self.translator.translate(text, src='bn', dest='en')
            self.current_english_text = translation.text
        except Exception as e:
            print(f"Translation error: {str(e)}")
            # Fallback to simple word-by-word translation
            words = text.split()
            translated_words = []
            for word in words:
                if word in self.bengali_medical_terms:
                    translated_words.append(self.bengali_medical_terms[word])
                else:
                    translated_words.append(word)
            self.current_english_text = " ".join(translated_words)
        
        return self.current_english_text
