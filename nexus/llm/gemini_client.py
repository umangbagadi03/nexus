import time

from google import genai
from google.genai import types

from nexus import config

# Free tier limits are per model, and popular models can be overloaded for a while.
# So try each model in turn, and wait before going through the list again.
MAX_ATTEMPTS = 4
WAIT_SECONDS = 20


def is_temporary(error):
    text = str(error)
    for sign in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"):
        if sign in text:
            return True
    return False


class GeminiClient:
    def __init__(self):
        self.models = [config.GEMINI_MODEL] + config.GEMINI_FALLBACK_MODELS
        self.use_model(config.GEMINI_MODEL)
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    def use_model(self, model):
        self.model = model
        self.name = "Gemini (" + model + ")"

    def settings(self, system_prompt):
        return types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1,
        )

    def wait_before_next_round(self):
        print("  Gemini is busy or out of quota, waiting", WAIT_SECONDS, "seconds")
        time.sleep(WAIT_SECONDS)

    def generate(self, system_prompt, user_prompt):
        for attempt in range(1, MAX_ATTEMPTS + 1):
            for model in self.models:
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=user_prompt,
                        config=self.settings(system_prompt),
                    )
                    self.use_model(model)
                    return response.text or ""
                except Exception as error:
                    if not is_temporary(error):
                        raise
                    last_error = error
                    print("  " + model + " is not available right now")

            if attempt == MAX_ATTEMPTS:
                raise last_error
            self.wait_before_next_round()

        return ""

    def stream(self, system_prompt, user_prompt):
        for attempt in range(1, MAX_ATTEMPTS + 1):
            for model in self.models:
                sent_text = False
                try:
                    chunks = self.client.models.generate_content_stream(
                        model=model,
                        contents=user_prompt,
                        config=self.settings(system_prompt),
                    )
                    for chunk in chunks:
                        if chunk.text:
                            if not sent_text:
                                self.use_model(model)
                            sent_text = True
                            yield chunk.text
                    return
                except Exception as error:
                    # Once text has been sent we cannot start again, the reader would see it twice
                    if sent_text or not is_temporary(error):
                        raise
                    last_error = error
                    print("  " + model + " is not available right now")

            if attempt == MAX_ATTEMPTS:
                raise last_error
            self.wait_before_next_round()
