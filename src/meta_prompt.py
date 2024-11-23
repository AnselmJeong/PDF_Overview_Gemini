from openai import OpenAI
import toml

META_PROMPT = toml.load("src/prompts.toml")["meta_prompt"]["prompt"]

client = OpenAI()

def generate_prompt(task_or_prompt: str):
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": META_PROMPT,
            },
            {
                "role": "user",
                "content": "Task, Goal, or Current Prompt:\n" + task_or_prompt,
            },
        ],
    )

    return completion.choices[0].message.content