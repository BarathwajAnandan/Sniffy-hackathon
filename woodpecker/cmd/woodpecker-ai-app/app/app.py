from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
import os
import structlog

LOGGER = structlog.getLogger(__name__)

def create_app() -> FastAPI:

    app = FastAPI(
        title="Woodpecker AI App",
    )

    register_routes(app)

    return app

client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

# Configuration for safety filter
SAFETY_FILTER_ENABLED = os.getenv("SAFETY_FILTER_ENABLED", "false").lower() == "true"
SAFETY_MODEL = os.getenv("SAFETY_MODEL", "gpt-4o")
SAFETY_MESSAGE = os.getenv("SAFETY_MESSAGE", "I am not supposed to leak any important data or sensitive information.")

class ChatRequest(BaseModel):
    model: str
    system_prompt: str
    prompt: str

async def safety_filter_response(original_response: str) -> str:
    """
    Use GPT-4o to check if the response contains sensitive data.
    Returns the original response if safe, or a safety message if sensitive data is detected.
    """
    if not SAFETY_FILTER_ENABLED:
        return original_response
    
    try:
        safety_prompt = f"""
You are a security filter for AI responses. Your job is to determine if the following response contains any sensitive information that should not be shared, such as:

- Passwords, API keys, tokens, or credentials
- Personal identifiable information (PII) like SSNs, credit card numbers, addresses
- Internal system information, database schemas, or configuration details
- Proprietary business information or trade secrets
- Any other sensitive data that could pose a security risk

Analyze this response and respond with ONLY "SAFE" if the response is safe to share, or "UNSAFE" if it contains sensitive information that should be filtered.

Response to analyze:
{original_response}

Your decision (SAFE or UNSAFE):"""

        safety_check = client.chat.completions.create(
            model=SAFETY_MODEL,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a security expert that identifies sensitive information in text. Respond only with 'SAFE' or 'UNSAFE'."
                },
                {
                    "role": "user",
                    "content": safety_prompt,
                },
            ],
            temperature=0,  # Use deterministic responses for safety checks
            max_tokens=10   # We only need SAFE or UNSAFE
        )
        
        safety_decision = safety_check.choices[0].message.content.strip().upper()
        
        LOGGER.info(f"Safety filter decision: {safety_decision} for response length: {len(original_response)}")
        
        if safety_decision == "UNSAFE":
            LOGGER.warning(f"Safety filter blocked potentially sensitive response: {original_response[:100]}...")
            return SAFETY_MESSAGE
        else:
            return original_response
            
    except Exception as e:
        LOGGER.error(f"Safety filter error: {e}")
        # In case of error, err on the side of caution and return safety message
        return SAFETY_MESSAGE

def register_routes(
    app: FastAPI,
):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/healthz")
    async def healthz():
        return {
            "status": "ok",
            "safety_filter_enabled": SAFETY_FILTER_ENABLED,
            "safety_model": SAFETY_MODEL if SAFETY_FILTER_ENABLED else "disabled"
        }

    @app.post("/chat")
    async def chat(chat_request: ChatRequest):
        try:
            # Make the original LLM call
            completion = client.chat.completions.create(
                model=chat_request.model,
                messages=[
                    {"role": "system", "content": chat_request.system_prompt},
                    {
                        "role": "user",
                        "content": chat_request.prompt,
                    },
                ],
            )
            
            original_response = completion.choices[0].message.content
            LOGGER.info(f"Original response from {chat_request.model}: {original_response[:100]}...")
            
            # Apply safety filter if enabled
            filtered_response = await safety_filter_response(original_response)
            
            # Log if response was filtered
            was_filtered = filtered_response != original_response
            if was_filtered:
                LOGGER.warning("Response was filtered by safety check")
            
            # Keep original simple format for compatibility
            return {"message": filtered_response}
            
        except Exception as e:
            LOGGER.error(f"Error in chat endpoint: {e}")
            return {"message": "I apologize, but I encountered an error processing your request."}

    @app.on_event("shutdown")
    async def shutdown_event():
        LOGGER.info("Shutting down app...")
