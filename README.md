# Market Assistant

This project is an MVP that shows how AI can help users find products in stores and suggests recipes based on available ingredients. It combines natural language processing (NPL) with a product database to create an intuitive shopping assistant.

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

## Technology Stack AS IS

- **Backend**: Python with FastAPI
- **Frontend**: <i>HTML, CSS, JavaScript</i>
- **AI/ML**: <i>Ollama for natural language processing</i>
- **Database**: Supabase (PostgreSQL)
- **Containerization**: Docker
- **Speech Processing**: Faster Whisper for speech-to-text

## Limitations

As this is an MVP:
- Limited product database
- Basic recipe suggestions
- Requires local Ollama instance
- Limited voice recognition capabilities
- Frontend is essentially a prototype

## Possible improvements

- Vector database for semantic product search
- Fine-tuned Domain-specific Language Models (DSLMs) for improved accuracy
- Expanded product database
- More sophisticated recipe recommendations
- Cloud-based deployment
- Mobile app
- Improved voice interaction
- User accounts and personalization

# Getting Started
### Prerequisites
- Docker
- Python 3.9+

## To build the docker image and run it

```
docker-compose build --no-cache
docker-compose up -d --force-recreate
```
## To import database from dump
Make sure you have already installed Supabase on your machine.
[Supabase installation guide](https://supabase.com/docs/guides/local-development/cli/getting-started?queryGroups=platform&platform=windows&queryGroups=access-method&access-method=studio)
```
cd database
pg_restore -U postgres -h localhost -p 54322 -d postgres --clean --if-exists -F c full_backup.dump

```

## To install Ollama with Qwen model on Docker

1. Pull the Ollama Docker image:

```
docker pull ollama/ollama
```
2. Run the Ollama Docker container:
```
docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
```
3. Download the Qwen model:

```
docker exec -it ollama ollama pull qwen2.5:7b
```
4. Verify the model is installed:

```
docker exec -it ollama ollama list
```