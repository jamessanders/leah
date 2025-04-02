# Leah

A Python script that processes messages and generates text-to-speech responses using Ollama and Edge TTS.

## Features

- Process messages using Ollama API
- Generate text-to-speech responses using Edge TTS
- Multiple response tones (default, cheerful, serious, casual, friendly)
- Configurable AI model selection
- Voice output can be disabled
- Streaming response output
- Clean, modular code structure

## Prerequisites

- Python 3.8 or higher
- Ollama running locally (default: http://localhost:11434)
- Edge TTS for voice synthesis
- Pygame for audio playback

## Installation

1. Clone the repository:
```bash
git clone https://github.com/jsanders/leah.git
cd leah
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

3. Install Edge TTS:
```bash
pip install edge-tts
```

4. Install Pygame:
```bash
pip install pygame
```

5. Make the script executable:
```bash
chmod +x src/leah.py
```

## Usage

### Basic Usage

```bash
leah "Your message here"
```

### Command Line Options

- `--voice`: Specify the Edge TTS voice to use (default: en-US-AvaNeural)
- `--model`: Specify the AI model to use (default: gemma-3-27b-it)
- `--tone`: Choose the response tone (default, cheerful, serious, casual, friendly)
- `--no-voice`: Disable voice output

### Examples

```bash
# Basic usage with voice output
leah "Hello, how are you?"

# Disable voice output
leah --no-voice "Hello, how are you?"

# Use a different voice
leah --voice "en-US-JennyNeural" "Hello, how are you?"

# Use a different model
leah --model "llama2" "Hello, how are you?"

# Use a different tone
leah --tone cheerful "Hello, how are you?"

# Read message from stdin
echo "Hello, how are you?" | leah
```

## Configuration

The script uses a `config.json` file for configuration. You can modify the following settings:

- `url`: Ollama API URL
- `headers`: API request headers
- `temperature`: Response temperature (0.0 to 1.0)
- `tones`: Response tone configurations

Example `config.json`:
```json
{
    "url": "http://localhost:11434/api/chat",
    "headers": {
        "Content-Type": "application/json"
    },
    "temperature": 0.7,
    "tones": {
        "default": {
            "description": "You are a helpful and friendly AI assistant.",
            "traits": [
                "Professional and courteous",
                "Clear and concise",
                "Helpful and informative"
            ]
        },
        "cheerful": {
            "description": "You are an enthusiastic and upbeat AI assistant.",
            "traits": [
                "Energetic and positive",
                "Friendly and engaging",
                "Optimistic and encouraging"
            ]
        }
    }
}
```

## Project Structure

```
leah/
├── README.md
├── requirements.txt
├── config.json
└── src/
    └── leah.py
```

## Contributing

Feel free to submit issues and enhancement requests! 