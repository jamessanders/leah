# Leah

A command-line interface for interacting with AI models using text-to-speech capabilities.

## Features

- Multiple AI models support
- Text-to-speech using Microsoft Edge TTS voices
- Different response tones (cheerful, serious, casual, friendly, irish_female)
- Streaming responses
- Command-line interface with multiple convenience scripts

## Requirements

- Python 3.x
- edge-tts package
- A running Ollama instance with the desired models

## Installation

1. Clone the repository:
```bash
git clone git@github.com:jamessanders/leah.git
cd leah
```

2. Install the required Python package:
```bash
pip install edge-tts
```

3. Make the scripts executable:
```bash
chmod +x leah emily frank ann
```

## Usage

The main script is `leah.py`, but there are several convenience scripts available:

### Basic Usage

```bash
leah "Your message here"
```

### Available Scripts

- `leah`: Default voice (en-US-AvaNeural) with default model
- `emily`: Irish voice (en-IE-EmilyNeural) with gemma-3-27b-it model
- `frank`: Male voice (en-US-GuyNeural) with gemma-3-27b-it model
- `ann`: Canadian voice (en-CA-ClaraNeural) with deepseek-r1-distill-qwen-7b model

### Command Line Options

```bash
python leah.py [--voice VOICE] [--model MODEL] [--tone TONE] your message here
```

- `--voice`: Edge TTS voice to use
- `--model`: AI model to use
- `--tone`: Response tone (default, cheerful, serious, casual, friendly, irish_female)

### Piping Input

You can also pipe text to the script:

```bash
echo "Your message" | leah
```

## License

MIT License 