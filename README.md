"""
Requirements file for Bengali-to-English Medical Transcription Application.
Install dependencies with: pip install -r requirements.txt
"""

# Core dependencies
PyQt5>=5.15.0
pyaudio>=0.2.11
numpy>=1.20.0
wave>=0.0.2

# Bengali speech recognition
# Note: These packages will need to be installed separately
# BanglaSpeech2Text>=0.0.5
# bangla-speech-recognition>=0.1.0

# Translation dependencies
# BanglaTranslationKit>=0.1.0
googletrans>=4.0.0-rc1

# Export functionality
python-docx>=0.8.11
reportlab>=3.6.1
fpdf2>=2.5.0

# Utilities
tqdm>=4.62.0
requests>=2.26.0
