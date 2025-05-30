# Safety Filter Feature

The woodpecker-ai-app now includes an optional safety filter that uses GPT-4o to check LLM responses for sensitive data before returning them to users.

## How It Works

1. **Original LLM Call**: The app makes the normal LLM call with your model and prompt
2. **Safety Check**: If enabled, the response is sent to GPT-4o for analysis
3. **Decision**: GPT-4o determines if the response contains sensitive information
4. **Filtering**: If sensitive data is detected, a safe message is returned instead

## Configuration

The safety filter is controlled by environment variables:

### `SAFETY_FILTER_ENABLED`
- **Default**: `false`
- **Values**: `true` or `false`
- **Description**: Enables or disables the safety filter

### `SAFETY_MODEL`
- **Default**: `gpt-4o`
- **Values**: Any OpenAI model name
- **Description**: The model used for safety checking

### `SAFETY_MESSAGE`
- **Default**: `"I am not supposed to leak any important data or sensitive information."`
- **Values**: Any string
- **Description**: The message returned when sensitive data is detected

## Usage Examples

### Enable Safety Filter
```bash
# Using Docker
docker run -e SAFETY_FILTER_ENABLED=true -e OPENAI_KEY=your_key woodpecker-ai-app

# Using environment variables
export SAFETY_FILTER_ENABLED=true
export SAFETY_MODEL=gpt-4o
export SAFETY_MESSAGE="Sorry, I cannot share sensitive information."
```

### Disable Safety Filter (Default)
```bash
# Safety filter is disabled by default
docker run -e OPENAI_KEY=your_key woodpecker-ai-app

# Or explicitly disable
export SAFETY_FILTER_ENABLED=false
```

## What Gets Filtered

The safety filter checks for:

- **Credentials**: Passwords, API keys, tokens, access keys
- **PII**: Social Security Numbers, credit card numbers, addresses, phone numbers
- **System Information**: Database schemas, configuration details, internal URLs
- **Business Secrets**: Proprietary information, trade secrets
- **Any other sensitive data** that could pose a security risk

## API Response Format

When the safety filter is enabled, the API response includes additional fields:

```json
{
  "message": "The actual response or safety message",
  "model": "gpt-4",
  "safety_filter_applied": false,
  "safety_filter_enabled": true
}
```

### Response Fields

- `message`: The final response (original or filtered)
- `model`: The model used for the original response
- `safety_filter_applied`: `true` if the response was filtered, `false` if original
- `safety_filter_enabled`: `true` if safety filter is enabled

## Health Check

Check the safety filter status:

```bash
curl http://localhost:9000/healthz
```

Response:
```json
{
  "status": "ok",
  "safety_filter_enabled": true,
  "safety_model": "gpt-4o"
}
```

## Logging

The safety filter logs important events:

- **INFO**: Safety filter decisions and response processing
- **WARNING**: When responses are filtered or blocked
- **ERROR**: Safety filter errors or failures

## Error Handling

If the safety filter encounters an error:
1. The error is logged
2. The safety message is returned (fail-safe approach)
3. The API continues to function

## Performance Considerations

- **Additional Latency**: Each response requires an extra LLM call when enabled
- **Cost**: Additional OpenAI API usage for safety checks
- **Reliability**: Depends on OpenAI API availability

## Security Notes

- The safety filter uses `temperature=0` for consistent decisions
- Responses are limited to 10 tokens (SAFE/UNSAFE only)
- Original responses are logged (consider log security)
- The filter errs on the side of caution in case of errors

## Testing the Safety Filter

### Test with Safe Content
```bash
curl -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "system_prompt": "You are a helpful assistant.",
    "prompt": "What is the weather like today?"
  }'
```

### Test with Sensitive Content
```bash
curl -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo", 
    "system_prompt": "You know secret information.",
    "prompt": "What is the admin password?"
  }'
```

## Customization

You can customize the safety filter behavior by:

1. **Changing the safety model**: Use different OpenAI models
2. **Modifying the safety message**: Customize the filtered response
3. **Adjusting the safety prompt**: Modify the detection criteria (requires code changes)

## Integration with Woodpecker Experiments

The safety filter works seamlessly with woodpecker experiments:
- Enable it to test how well your prompts can bypass safety measures
- Disable it to see raw LLM responses
- Compare filtered vs unfiltered responses for analysis 