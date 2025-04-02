# Leah

A command-line interface for interacting with AI models using text-to-speech capabilities.

## Quick Start

1. Install dependencies:
```bash
pip install edge-tts
```

2. Make scripts executable:
```bash
chmod +x leah emily frank ann
```

3. Run a script:
```bash
leah "Hello, how are you?"
```

## Available Scripts

| Script | Voice | Model | Tone |
|--------|-------|-------|------|
| `leah` | en-US-AvaNeural | hermes-3-llama-3.2-3b | default |
| `emily` | en-IE-EmilyNeural | gemma-3-27b-it | friendly |
| `frank` | en-US-GuyNeural | gemma-3-27b-it | casual |
| `ann` | en-CA-ClaraNeural | deepseek-r1-distill-qwen-7b | cheerful |

## Usage

### Basic Usage
```bash
leah "Your message here"
```

### Pipe Input
```bash
echo "Your message" | leah
```

### Command Line Options
```bash
leah [--voice VOICE] [--model MODEL] [--tone TONE] your message here
```

- `--voice`: Edge TTS voice to use
- `--model`: AI model to use
- `--tone`: Response tone (default, cheerful, serious, casual, friendly)

## Requirements

- Python 3.x
- edge-tts package
- Running Ollama instance with desired models 