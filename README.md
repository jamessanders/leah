# Leah - AI Assistant Framework

A flexible framework for creating AI assistants with different personalities and personas.

## Features

- Multiple AI personas (cheerful, serious, casual, friendly, professional)
- Text-to-speech voice output
- Configurable response styles
- Command-line interface
- Support for multiple AI models
- Dynamic persona configuration
- Inheritance-based persona settings
- User-specific configuration support

## Prerequisites

- Python 3.8 or higher
- [LMStudio](https://lmstudio.ai/) installed and running locally
- Edge TTS for voice output (optional)

## Installing LMStudio

1. Download LMStudio from [https://lmstudio.ai/](https://lmstudio.ai/)
2. Install the application on your system
3. Launch LMStudio
4. Go to the "Models" tab and download one or more of the following models:
   - deepseek-r1-distill-qwen-7b
   - mistral-7b-instruct
   - llama2-7b-chat
   - neural-chat-7b-v3-1
5. Once downloaded, select a model and click "Start Server"
6. The server will start on `http://localhost:1234`

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/leah.git
cd leah
```

2. Install Python dependencies:
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

5. Make the scripts executable:
```bash
chmod +x src/leah.py
chmod +x leah frank pam hey
```

## Usage

### Basic Usage

```bash
leah "Your message here"
```

### Command Line Options

- `--voice`: Specify the Edge TTS voice to use (overrides persona default)
- `--persona`: Choose the response persona (choices are dynamically loaded from config)
- `--no-voice`: Disable voice output

### User Configuration

You can create a user-specific configuration file named `.hey.config.json` in your home directory. This file will be merged with the default configuration, with your settings taking precedence.

Example `.hey.config.json`:
```json
{
  "url": "http://localhost:1234/v1/chat/completions",
  "personas": {
    "default": {
      "voice": "en-US-JennyNeural"
    },
    "custom": {
      "description": "You are a custom AI assistant.",
      "traits": [
        "Custom trait 1",
        "Custom trait 2"
      ],
      "model": "mistral-7b-instruct",
      "temperature": 0.8,
      "voice": "en-US-GuyNeural"
    }
  }
}
```

This allows you to:
- Override default settings
- Add new personas
- Customize existing personas
- Change API endpoints

### Available Personas

Each persona has its own model, temperature, and voice settings. The following personas are included by default:

- **Default**
  - Model: deepseek-r1-distill-qwen-7b
  - Temperature: 0.7
  - Voice: en-US-AvaNeural
  - Style: Helpful and friendly

- **Cheerful**
  - Model: mistral-7b-instruct
  - Temperature: 0.8
  - Voice: en-US-JennyNeural
  - Style: Enthusiastic and upbeat

- **Serious**
  - Model: llama2-7b-chat
  - Temperature: 0.5
  - Voice: en-US-AndrewNeural
  - Style: Direct and focused

- **Casual**
  - Model: neural-chat-7b-v3-1
  - Temperature: 0.9
  - Voice: en-US-GuyNeural
  - Style: Relaxed and conversational

- **Friendly**
  - Model: mistral-7b-instruct
  - Temperature: 0.7
  - Voice: en-US-SaraNeural
  - Style: Warm and approachable

- **Professional**
  - Model: deepseek-r1-distill-qwen-7b
  - Temperature: 0.6
  - Voice: en-US-DavisNeural
  - Style: Business-appropriate and formal

### Persona Inheritance

All personas inherit their base settings from the "default" persona. When you add a new persona to the `config.json` file, you only need to specify the settings that differ from the default. Any missing settings will automatically use the values from the default persona.

For example, if you want to create a new "poetic" persona that only changes the description and traits but uses the same model, temperature, and voice as the default, you can add:

```json
"poetic": {
  "description": "You are a poetic and creative AI assistant.",
  "traits": [
    "Creative and imaginative",
    "Uses metaphors and imagery",
    "Expressive and artistic"
  ]
}
```

The system will automatically use the model, temperature, and voice from the default persona.

### Examples

```bash
# Basic usage with voice output
leah "Hello, how are you?"

# Disable voice output
leah --no-voice "Hello, how are you?"

# Use a different voice (overrides persona default)
leah --voice "en-US-JennyNeural" "Hello, how are you?"

# Use a different persona
leah --persona cheerful "Hello, how are you?"

# Read message from stdin
echo "Hello, how are you?" | leah
```

### Personality Scripts

The framework includes several personality scripts:

- `leah`: Default personality
- `frank`: Serious and direct personality
- `pam`: Professional and polished personality
- `hey`: Quick persona selector

Each script can be used directly:
```bash
frank "What's the weather like?"
pam "Can you help me with my project?"
hey cheerful "Tell me a joke"
```

The `hey` script provides a quick way to select a persona and send a message in one command:
```bash
hey <persona> <message>
```

## Project Structure

```
leah/
├── README.md
├── requirements.txt
├── src/
│   └── leah.py
├── leah
├── frank
├── pam
└── hey
```

## Contributing

Feel free to submit issues and enhancement requests!