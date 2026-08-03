import sys
from pathlib import Path

# Ensure the RAG_FINANCE root (where config.py lives) is on the path.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import config
from anthropic import Anthropic

from summarization.prompt import SUMMARY_PROMPT


class ClaudeSummarizer:

    def __init__(
        self,
        api_key: str,
        model: str = config.LLM_MODEL,
    ):

        self.client = Anthropic(api_key=api_key)
        self.model = model

    def summarize(self, messages):

        conversation = "\n".join(
            f"{m.role}: {m.message}"
            for m in messages
        )

        prompt = SUMMARY_PROMPT.format(
            conversation=conversation
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=config.SUMMARIZER_MAX_TOKENS,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.content[0].text