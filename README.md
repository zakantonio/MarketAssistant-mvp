# Market Assistant

Market Assistant is an MVP (Minimum Viable Product) that helps users find products in stores and suggests recipes based on available ingredients. It combines natural language processing with a product database to create an intuitive shopping assistant.

## Features

- **Product Search**: Find products in the store and get their exact location (aisle, section, shelf)
- **Recipe Suggestions**: Get recipe ideas based on ingredients you have
- **Voice Interface**: Interact with the assistant using voice commands
- **Responsive UI**: Access the assistant from any device

## Architecture

The project consists of three main components:

1. **Client**: Web interface for user interaction
2. **Main API**: Handles user requests, NLP processing, and coordinates with the product database
3. **Product API**: Manages the product and recipe database

## Technology Stack

- **Backend**: Python with FastAPI
- **Frontend**: HTML, CSS, JavaScript
- **AI/ML**: Ollama for natural language processing
- **Database**: Supabase
- **Containerization**: Docker
- **Speech Processing**: Faster Whisper for speech-to-text, Piper for text-to-speech

## Getting Started

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU (optional, for better AI performance)
- Ollama running locally or accessible via network

### Environment Setup

1. Clone the repository
2. Create a `.env` file based on `.env.example`
3. Make sure Ollama is running and accessible

### Running with Docker
```
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

## Limitations

As this is an MVP:
- Limited product database
- Basic recipe suggestions
- Requires local Ollama instance
- Limited voice recognition capabilities
- Frontend is essentially a prototype

## Future Improvements

- Expanded product database
- More sophisticated recipe recommendations
- Cloud-based deployment
- Mobile app
- Improved voice interaction
- User accounts and personalization

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT) for more information.

## Acknowledgments

- Ollama for providing the LLM capabilities
- Supabase for the database infrastructure
- FastAPI for the API framework