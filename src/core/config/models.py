#!/usr/bin/env python3
"""Списки моделей по умолчанию"""

FALLBACK_MODELS = {
    "yellow": [
        "meta-llama/llama-3.1-70b-instruct:free",
        "nvidia/llama-3.1-nemotron-70b-instruct:free",
        "google/gemini-2.0-flash-thinking-exp:free",
        "openai/gpt-oss-20b:free",
        "qwen/qwen-2.5-32b-instruct:free",
    ],
    "red": [
        "openai/gpt-oss-120b:free",
        "deepseek/deepseek-r1:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "meta-llama/llama-3.2-90b-vision-instruct:free",
        "google/gemini-2.5-pro-exp-03-25:free",
    ],
    "blue": [
        "meta-llama/llama-3.2-3b-instruct:free",
        "google/gemma-2-9b-it:free",
        "mistralai/mistral-7b-instruct:free",
        "microsoft/phi-3-mini-4k-instruct:free",
        "google/gemma-2-2b-it:free",
    ]
}
