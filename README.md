# Leah - AI Assistant Framework

A flexible framework for creating AI assistants with different personalities and tones.

## Features

- Multiple AI personalities (cheerful, serious, casual, friendly, professional)
- Text-to-speech voice output
- Configurable response tones
- Command-line interface
- Support for multiple AI models

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
chmod +x leah frank pam
```

## Usage

### Basic Usage

```bash
leah "Your message here"
```

### Command Line Options

- `--voice`: Specify the Edge TTS voice to use (default: en-US-AvaNeural)
- `--model`: Specify the AI model to use (default: deepseek-r1-distill-qwen-7b)
- `--tone`: Choose the response tone (default, cheerful, serious, casual, friendly, professional)
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
leah --model "mistral-7b-instruct" "Hello, how are you?"

# Use a different tone
leah --tone cheerful "Hello, how are you?"

# Read message from stdin
echo "Hello, how are you?" | leah
```

### Personality Scripts

The framework includes several personality scripts:

- `leah`: Default personality
- `frank`: Serious and direct personality
- `pam`: Professional and polished personality

Each script can be used directly:
```bash
frank "What's the weather like?"
pam "Can you help me with my project?"
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
└── pam
```

## Contributing

Feel free to submit issues and enhancement requests!