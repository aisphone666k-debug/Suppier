import configparser
import os
from typing import Optional
import httpx

from src.application.inquiry_generator import AnswerGeneratorPort, QuotationChunkContext


class GeminiApiException(RuntimeError):
    """Raised when Gemini API request fails or returns an error."""
    pass


class GeminiAnswerGenerator(AnswerGeneratorPort):
    """Concrete adapter connecting to Google Gemini Generative AI API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key or self._load_api_key()
        self.model_name = model_name or self._load_model_name()
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _load_model_name() -> str:
        """Loads model name from environment variable or credentials.ini, defaulting to gemini-2.5-flash."""
        env_model = os.environ.get("GEMINI_MODEL")
        if env_model and env_model.strip():
            return env_model.strip()

        if os.path.exists("credentials.ini"):
            config = configparser.ConfigParser()
            config.read("credentials.ini")
            if "gemini" in config and "model" in config["gemini"]:
                return config["gemini"]["model"].strip()

        return "gemini-2.5-flash"

    @staticmethod
    def _load_api_key() -> str:
        """Loads API key from credentials.ini or environment variable."""
        if os.path.exists("credentials.ini"):
            config = configparser.ConfigParser()
            config.read("credentials.ini")
            if "gemini" in config and "api_key" in config["gemini"] and config["gemini"]["api_key"].strip():
                return config["gemini"]["api_key"].strip()

        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key and env_key.strip():
            return env_key.strip()

        raise GeminiApiException(
            "Gemini API Key not found. Please set GEMINI_API_KEY environment variable or populate credentials.ini."
        )

    def _build_system_prompt(self, context_chunks: list[QuotationChunkContext]) -> str:
        lines = [
            "You are QuotationFinder AI, an intelligent, agentic industrial procurement assistant.",
            "Answer the user's question accurately and concisely based strictly on the verified quotations provided below.",
            "Key behavioral guidelines:",
            "1. When user asks general or overview questions (e.g. 'มีอะไรบ้าง', 'มีอะบ้าง', 'overview', 'what do you have'):",
            "   - Group and summarize the available items by product category or vendor.",
            "   - Provide clear bullet points with vendor names, model/part numbers, price ranges, and quotation status.",
            "2. When user asks about technical specifications, types, or models (e.g. 'สายพานนี้เป็นเเบบไหน', 'what type is this'):",
            "   - Analyze both the item descriptions and the Technical Context / Snippet provided.",
            "   - Clearly explain the specific type, cross-section/profile, dimension, and industrial application.",
            "3. Always answer in the exact language requested by the user (Thai for Thai questions, English for English questions, Japanese for Japanese questions).",
            "4. Always state the vendor name, quotation number, exact unit price, currency, and validity status when relevant.",
            "5. If the provided context does not contain the answer, state clearly that the quotation details are not available in the verified database.",
            "\n--- VERIFIED QUOTATIONS CONTEXT ---",
        ]
        for idx, chunk in enumerate(context_chunks, 1):
            lines.append(f"[{idx}] Quotation No: {chunk.quotation_number}")
            lines.append(f"    Vendor: {chunk.vendor_name}")
            lines.append(f"    Validity: {chunk.validity_summary}")
            lines.append(f"    Items: {chunk.items_summary}")
            if chunk.raw_text_snippet:
                lines.append(f"    Technical Context / Snippet: {chunk.raw_text_snippet}")
            lines.append("")
        lines.append("--- END OF CONTEXT ---\n")
        return "\n".join(lines)

    def generate_answer(self, query: str, context_chunks: list[QuotationChunkContext]) -> str:
        if not self.api_key:
            raise GeminiApiException("Gemini API key is required but missing.")

        system_context = self._build_system_prompt(context_chunks)
        user_message = f"{system_context}\nUser Question: {query}\nAnswer:"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": user_message}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            },
        }

        # Bypass local corporate proxy for googleapis if configured
        client_proxies = None
        if "NO_PROXY" in os.environ and "googleapis.com" in os.environ["NO_PROXY"]:
            client_proxies = {"http": None, "https": None}

        try:
            with httpx.Client(timeout=self.timeout_seconds, proxy=client_proxies) as client:
                response = client.post(url, json=payload)
        except Exception as e:
            raise GeminiApiException(f"Network error contacting Gemini API: {e}") from e

        if response.status_code != 200:
            try:
                err_body = response.json()
                msg = err_body.get("error", {}).get("message", response.text)
                status = err_body.get("error", {}).get("status", "ERROR")
            except Exception:
                msg = response.text
                status = "ERROR"
            raise GeminiApiException(f"Gemini API returned status {response.status_code} ({status}): {msg}")

        data = response.json()
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                return "No response generated by Gemini."
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError) as e:
            raise GeminiApiException(f"Unexpected response structure from Gemini API: {e}") from e
