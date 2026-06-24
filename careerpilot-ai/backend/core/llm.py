"""
LLM factory - returns a configured chat model based on settings.

ROOT CAUSE FIX:
The google-genai / langchain-google-genai SDK ignores the
google_api_key= kwarg in some versions and always tries
google.auth.default() (ADC) for gRPC transport initialization.

THE ONLY RELIABLE FIX is to set os.environ["GOOGLE_API_KEY"]
BEFORE importing or instantiating anything from langchain_google_genai.
We do this explicitly here at call time (not module import time).
"""
import os
from backend.core.config import get_settings


def _configure_google_auth():
    """
    Set GOOGLE_API_KEY in the process environment so the underlying
    google-auth / gRPC transport never attempts ADC.
    Must be called before any langchain_google_genai import.
    """
    settings = get_settings()
    key = settings.google_api_key.strip()
    if not key:
        raise ValueError(
            "GOOGLE_API_KEY is empty in your .env file. "
            "Please add your Gemini API key: GOOGLE_API_KEY=your_key_here"
        )
    # These are ALL the env vars the google SDK checks, set all of them.
    os.environ["GOOGLE_API_KEY"] = key
    os.environ["GEMINI_API_KEY"] = key
    # Disable ADC fallback by pointing to a dummy credentials file
    # (only if real ADC is not already configured — don't break prod)
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_CLOUD_PROJECT"] = os.environ.get("GOOGLE_CLOUD_PROJECT", "careerpilot")
    return settings


def get_llm(temperature: float = 0.3):
    """Return a configured LangChain chat model."""
    settings = get_settings()

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = settings.openai_api_key.strip()
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is empty in your .env file. "
                "Please add your OpenAI API key."
            )
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature,
            api_key=api_key,
        )

    # --- Gemini ---
    _configure_google_auth()

    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=temperature,
        google_api_key=os.environ["GOOGLE_API_KEY"],
    )


def get_embeddings():
    """Return configured embeddings model."""
    settings = get_settings()

    if settings.llm_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(api_key=settings.openai_api_key.strip())

    _configure_google_auth()

    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.environ["GOOGLE_API_KEY"],
    )
