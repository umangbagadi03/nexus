import requests

from nexus import config

API_URL = "https://api.github.com"


def get_headers():
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = "Bearer " + config.GITHUB_TOKEN
    return headers


def github_get(path, params=None):
    url = API_URL + path
    response = requests.get(url, headers=get_headers(), params=params, timeout=30)

    if response.status_code == 403 or response.status_code == 429:
        message = "GitHub rate limit reached."
        if not config.GITHUB_TOKEN:
            message += " Add GITHUB_TOKEN to your .env file to get 5000 requests per hour."
        raise RuntimeError(message)

    response.raise_for_status()
    return response.json()
