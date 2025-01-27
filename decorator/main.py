from decorator.generator import add_docstrings_to_file
import json
import os
import click
import re
from pydantic import BaseModel
from typing import Optional


def validate_email(value: str) -> bool:
    if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
        return False
    return True


def validate_github_username(value: str) -> bool:
    if not re.match(r"^[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}$", value):
        return False
    return True


def validate_name(value: str) -> bool:
    if not re.match(r"^[a-zA-Z\s]*$", value):
        return False
    return True


class Settings(BaseModel):
    name: str
    github_username: str
    email: str

    @staticmethod
    def empty() -> "Settings":
        return Settings(name="", github_username="", email="")

    def is_valid(self) -> tuple[bool, str]:
        if not self.name:
            return False, "Name is required"
        if not validate_name(self.name):
            return False, "Invalid name"
        if not self.github_username:
            return False, "GitHub username is required"
        if not validate_github_username(self.github_username):
            return False, "Invalid GitHub username"
        if not self.email:
            return False, "Email is required"
        if not validate_email(self.email):
            return False, "Invalid email"
        return True, ""

    @staticmethod
    def create(
        settings_path: str, name: "str", github_username: str, email: str
    ) -> "Settings":
        settings = Settings(name=name, github_username=github_username, email=email)
        with open(settings_path, "w") as f:
            json.dump(settings.model_dump(), f)
        return settings

    @staticmethod
    def load(settings_path: str) -> Optional["Settings"]:
        if not os.path.exists(settings_path):
            return None
        with open(settings_path, "r") as f:
            data = json.load(f)
            try:
                return Settings.model_validate(data)
            except Exception:
                return None

    def save(self, settings_path: str):
        with open(settings_path, "w") as f:
            json.dump(self.model_dump(), f)


SETTINGS_PATH = os.path.expanduser("~/.docarator_settings.json")
EXTENSION = ".decorator-draft.py"


@click.command(name="draft")
@click.argument("input_file", type=str, required=True)
@click.option(
    "-o", "--output_file", type=str, help="The output file to save the result"
)
@click.option(
    "--skip-draft",
    "-sd",
    is_flag=True,
    default=False,
    help="To directly write the output without draft file.",
)
def draft(input_file: str, output_file: str, skip_draft: bool) -> None:
    settings = Settings.load(SETTINGS_PATH)
    if settings is None:
        click.echo("Invalid settings", err=True)
        click.echo("Please run `docarator configure` to set the settings")
        return

    if not output_file:
        output_file = input_file

    if not skip_draft:
        print(output_file)
        output_file = os.path.splitext(output_file)[0] + EXTENSION
        print(output_file)

    result, message = add_docstrings_to_file(
        settings.name, settings.github_username, settings.email, input_file, output_file
    )
    click.echo(message, err=result)


@click.command(name="finalize")
@click.argument("decorator_draft_file", type=str, required=True)
@click.option(
    "--save-draft",
    "-sd",
    is_flag=True,
    default=False,
    help="To not remove the draft file.",
)
def finalize(decorator_draft_file: str, save_draft: bool) -> None:
    if not os.path.exists(decorator_draft_file):
        click.echo("Invalid decorator draft file path.", err=True)
        return

    output_file = os.path.splitext(decorator_draft_file)[0] + ".py"

    with open(decorator_draft_file, "r") as ddf, open(output_file, "w") as of:
        of.write(ddf.read())

    click.echo(f"Finalized Draft: {decorator_draft_file}")

    if not save_draft:
        os.remove(decorator_draft_file)
        click.echo(f"Draft file {decorator_draft_file} removed.")


@click.command(name="configure")
@click.option("--name", type=str, help="Set the default name")
@click.option("--github-username", type=str, help="Set the default GitHub username")
@click.option("--email", type=str, help="Set the default email")
def configure(name: str, github_username: str, email: str) -> None:
    settings = Settings.load(SETTINGS_PATH)
    if settings is None:
        settings = Settings.empty()

    if name:
        if validate_name(name):
            settings.name = name
        else:
            click.echo(f"Invalid name: {name}", err=True)
            return
    if github_username:
        if validate_github_username(github_username):
            settings.github_username = github_username
        else:
            click.echo(f"Invalid GitHub username: {github_username}", err=True)
            return
    if email:
        if validate_email(email):
            settings.email = email
        else:
            click.echo(f"Invalid email: {email}", err=True)
            return

    is_valid, message = settings.is_valid()

    if is_valid:
        settings.save(SETTINGS_PATH)
        click.echo("Settings saved successfully")
    else:
        click.echo(message, err=True)
        click.echo("Please rerun `docarator configure` to set the settings")


@click.command(name="rules")
@click.option(
    "--class-only",
    "-c",
    is_flag=True,
    default=False,
    help="To display only `class` related docstrings rules.",
)
@click.option(
    "--function-only",
    "-f",
    is_flag=True,
    default=False,
    help="To display only `function` related docstrings rules.",
)
def rules(class_only: bool, function_only: bool) -> None:
    if class_only:
        click.echo(
            click.style(
                "Here are some simple rules to follow for adding docstrings to your classes:\n",
                fg="cyan",
            )
        )

        click.echo(click.style("Class Docstrings:", fg="green"))
        click.echo(
            click.style(
                "    - Start with `description:` followed by a brief description of the class.",
                fg="yellow",
            )
        )
        click.echo(click.style("    - Example:", fg="yellow"))
        click.echo(
            click.style(
                '''
        ```python
        """
        description: A class to handle user authentication.
        """
        ```
        ''',
                fg="white",
            )
        )

        click.echo(
            click.style(
                "These rules will help the `Decorator` to extract and generate structured docstrings for your `class`.",
                fg="cyan",
            )
        )

    elif function_only:
        click.echo(
            click.style(
                "Here are some simple rules to follow for adding docstrings to your functions:\n",
                fg="cyan",
            )
        )

        click.echo(click.style("Function Docstrings:", fg="green"))
        click.echo(
            click.style(
                "    - Start with `description:` followed by a brief description of the function.",
                fg="yellow",
            )
        )
        click.echo(
            click.style(
                "    - For each parameter, use `param_name:` followed by a brief description.",
                fg="yellow",
            )
        )
        click.echo(
            click.style(
                "    - For return values, use `return:` followed by a brief description.",
                fg="yellow",
            )
        )
        click.echo(
            click.style(
                "    - For exceptions, use `exception:` followed by a brief description.",
                fg="yellow",
            )
        )
        click.echo(click.style("    - Example:", fg="yellow"))
        click.echo(
            click.style(
                '''
        ```python
        """
        description: Authenticate a user based on username and password.
        username: The username of the user.
        password: The password of the user.
        return: True if authentication is successful, False otherwise.
        exception: ValueError if the username or password is invalid.
        """
        ```
        ''',
                fg="white",
            )
        )

        click.echo(
            click.style(
                "These rules will help the `Decorator` to extract and generate structured docstrings for your `function.",
                fg="cyan",
            )
        )

    else:
        click.echo(
            click.style(
                "Here are some simple rules to follow for adding docstrings to your classes and functions:\n",
                fg="cyan",
            )
        )

        click.echo(click.style("1. Class Docstrings:", fg="green"))
        click.echo(
            click.style(
                "    - Start with `description:` followed by a brief description of the class.",
                fg="yellow",
            )
        )
        click.echo(click.style("    - Example:", fg="yellow"))
        click.echo(
            click.style(
                '''
        ```python
        """
        description: A class to handle user authentication.
        """
        ```
        ''',
                fg="white",
            )
        )

        click.echo(click.style("2. Function Docstrings:", fg="green"))
        click.echo(
            click.style(
                "    - Start with `description:` followed by a brief description of the function.",
                fg="yellow",
            )
        )
        click.echo(
            click.style(
                "    - For each parameter, use `param_name:` followed by a brief description.",
                fg="yellow",
            )
        )
        click.echo(
            click.style(
                "    - For return values, use `return:` followed by a brief description.",
                fg="yellow",
            )
        )
        click.echo(
            click.style(
                "    - For exceptions, use `exception:` followed by a brief description.",
                fg="yellow",
            )
        )
        click.echo(click.style("    - Example:", fg="yellow"))
        click.echo(
            click.style(
                '''
        ```python
        """
        description: Authenticate a user based on username and password.
        username: The username of the user.
        password: The password of the user.
        return: True if authentication is successful, False otherwise.
        exception: ValueError if the username or password is invalid.
        """
        ```
        ''',
                fg="white",
            )
        )

        click.echo(
            click.style(
                "These rules will help the `Decorator` to extract and generate structured docstrings for your code.",
                fg="cyan",
            )
        )


@click.group()
def main() -> None:
    pass


main.add_command(draft)
main.add_command(finalize)
main.add_command(configure)
main.add_command(rules)

if __name__ == "__main__":
    main()
