"""Quick smoke check: plain chat completion against the configured backend."""

from mlops_triage.config import get_settings
from mlops_triage.llm import create_openai_client


def main() -> None:
    settings = get_settings()
    client = create_openai_client(settings)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": "Eres un asistente técnico conciso."},
            {
                "role": "user",
                "content": "Escribe una función en Python que sume dos números.",
            },
        ],
        temperature=0.2,
    )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
