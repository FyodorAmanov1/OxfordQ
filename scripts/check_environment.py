"""Print availability only; never print API credentials."""
import importlib.metadata
import inspect
import os

from google import genai
from google.genai import types

from orchestrator.audio import discover_audio
from orchestrator.models import OrchestrationConfig

for name in ("mido", "music21", "pydantic", "google-genai", "numpy"):
    print(name, importlib.metadata.version(name))
print("Gemini key configured:", bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")))
print("SDK retry configuration:", types.HttpRetryOptions(attempts=1).attempts)
client = genai.Client(api_key="local-sdk-shape-check", http_options=types.HttpOptions(timeout=1000))
parameters = inspect.signature(client.interactions.create).parameters
print("SDK accepts structured Interactions body:", "response_format" in parameters or
      any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()))
client.close()
exe, font = discover_audio(OrchestrationConfig())
print("FluidSynth:", exe or "not installed")
print("SoundFont:", font or "not installed")
