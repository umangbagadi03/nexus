import json

import requests

from nexus import config


class OllamaClient:
    def __init__(self):
        self.model = config.OLLAMA_MODEL
        self.name = "Ollama (" + self.model + ")"
        self.url = config.OLLAMA_URL + "/api/chat"

    def send(self, system_prompt, user_prompt, stream):
        body = {
            "model": self.model,
            "stream": stream,
            "options": {"temperature": 0.1},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = requests.post(self.url, json=body, timeout=300, stream=stream)
        except requests.ConnectionError:
            raise RuntimeError(
                "Could not reach Ollama at " + config.OLLAMA_URL + ". "
                "Start it with `ollama serve`, or set an API key for another provider in .env."
            )

        response.raise_for_status()
        return response

    def generate(self, system_prompt, user_prompt):
        response = self.send(system_prompt, user_prompt, False)
        return response.json()["message"]["content"]

    def stream(self, system_prompt, user_prompt):
        # Ollama sends one JSON object per line
        response = self.send(system_prompt, user_prompt, True)
        for line in response.iter_lines():
            if line:
                text = json.loads(line)["message"]["content"]
                if text:
                    yield text
