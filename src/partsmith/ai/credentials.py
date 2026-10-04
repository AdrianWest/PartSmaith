"""Customer credential resolution; test .env is never loaded by the app."""

import os


def user_credential():
    key = os.environ.get("OPENAI_API_KEY")
    if key and key.strip():
        return key
    from partsmith.gui.credentials import CredentialStore

    return CredentialStore("OpenAI").read_for_processing()
