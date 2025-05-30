# Woodpecker AI App

AI Security focused Red Teaming application with optional safety filter for preventing sensitive data leakage.

## Features

- **LLM Integration**: Direct integration with OpenAI models
- **Safety Filter**: Optional GPT-4o powered filter to prevent sensitive data leakage
- **RESTful API**: Simple HTTP API for chat interactions
- **Configurable**: Environment-based configuration
- **Docker Ready**: Containerized deployment

## Quick Start

### Using Docker

```bash
# Basic usage (safety filter disabled by default)
docker build -t woodpecker-ai-app -f build/Dockerfile.woodpecker-ai-app .
docker run -e OPENAI_KEY=your_openai_key -p 9000:9000 woodpecker-ai-app

# With safety filter enabled
docker run -e OPENAI_KEY=your_openai_key -e SAFETY_FILTER_ENABLED=true -p 9000:9000 woodpecker-ai-app
```

### Local Development

```bash
cd cmd/woodpecker-ai-app
pip install -e .
export OPENAI_KEY=your_openai_key
export SAFETY_FILTER_ENABLED=true  # Optional
python -m app
```

## Safety Filter

The safety filter is a key security feature that uses GPT-4o to analyze LLM responses and filter out potentially sensitive information.

### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `SAFETY_FILTER_ENABLED` | `false` | Enable/disable the safety filter |
| `SAFETY_MODEL` | `gpt-4o` | Model used for safety checking |
| `SAFETY_MESSAGE` | `"I am not supposed to leak any important data or sensitive information."` | Message returned when content is filtered |

### Example Usage

```bash
# Enable safety filter
export SAFETY_FILTER_ENABLED=true
export SAFETY_MODEL=gpt-4o
export SAFETY_MESSAGE="Sorry, I cannot share sensitive information."

# Test the API
curl -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "system_prompt": "You are a helpful assistant.",
    "prompt": "What is the admin password?"
  }'
```

## API Endpoints

### POST /chat

Send a chat request to the LLM with optional safety filtering.

**Request:**
```json
{
  "model": "gpt-3.5-turbo",
  "system_prompt": "You are a helpful assistant.",
  "prompt": "Your question here"
}
```

**Response:**
```json
{
  "message": "The response from the LLM",
  "model": "gpt-3.5-turbo",
  "safety_filter_applied": false,
  "safety_filter_enabled": true
}
```

### GET /healthz

Check service health and safety filter status.

**Response:**
```json
{
  "status": "ok",
  "safety_filter_enabled": true,
  "safety_model": "gpt-4o"
}
```

## Testing

Use the included test script to verify safety filter functionality:

```bash
# Make sure the service is running first
python cmd/woodpecker-ai-app/test_safety_filter.py
```

This will test both safe and potentially sensitive prompts to demonstrate the safety filter in action.

## Integration with Woodpecker Experiments

The safety filter integrates seamlessly with woodpecker red-teaming experiments:

1. **Bypass Testing**: Test if your prompts can bypass safety measures
2. **Response Analysis**: Compare filtered vs unfiltered responses
3. **Security Assessment**: Evaluate how well the filter catches sensitive data

## Security Considerations

- The safety filter adds an extra layer of protection but is not foolproof
- Original responses are logged (consider log security in production)
- The filter uses deterministic settings (`temperature=0`) for consistency
- In case of errors, the filter defaults to blocking (fail-safe)

## Development

### Project Structure

```
cmd/woodpecker-ai-app/
├── app/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   └── app.py               # Main application with safety filter
├── pyproject.toml           # Dependencies and configuration
├── test_safety_filter.py    # Test script
├── SAFETY_FILTER.md         # Detailed safety filter documentation
└── README.md                # This file
```

### Adding New Features

1. Modify `app/app.py` for core functionality
2. Update environment variables in the Dockerfile
3. Add tests to `test_safety_filter.py`
4. Update documentation

## License

Part of the Woodpecker project - see main project license.
