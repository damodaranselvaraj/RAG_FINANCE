from anthropic import Anthropic

from summarization.prompt import SUMMARY_PROMPT


class ClaudeSummarizer:

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-5"
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
            max_tokens=400,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.content[0].text