import anthropic

from nexus import config


class AnthropicClient:
    def __init__(self):
        self.model = config.ANTHROPIC_MODEL
        self.name = "Claude (" + self.model + ")"
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # In both calls below, fallbacks="default" lets the API retry on another
    # Claude model if this one declines the request

    def generate(self, system_prompt, user_prompt):
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

        if response.stop_reason == "refusal":
            raise RuntimeError("Claude declined to answer this request.")

        parts = []
        for block in response.content:
            if block.type == "text":
                parts.append(block.text)
        return "".join(parts)

    def stream(self, system_prompt, user_prompt):
        with self.client.beta.messages.stream(
            model=self.model,
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            for text in stream.text_stream:
                yield text
            final_message = stream.get_final_message()

        if final_message.stop_reason == "refusal":
            raise RuntimeError("Claude declined to answer this request.")
