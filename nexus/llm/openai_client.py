from openai import OpenAI

from nexus import config


class OpenAIClient:
    def __init__(self):
        self.model = config.OPENAI_MODEL
        self.name = "OpenAI (" + self.model + ")"
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def messages(self, system_prompt, user_prompt):
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def generate(self, system_prompt, user_prompt):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages(system_prompt, user_prompt),
        )
        return response.choices[0].message.content or ""

    def stream(self, system_prompt, user_prompt):
        chunks = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages(system_prompt, user_prompt),
            stream=True,
        )
        for chunk in chunks:
            if len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
