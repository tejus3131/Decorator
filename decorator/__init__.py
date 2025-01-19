from decorator.main import add_docstrings_to_file
import argparse


def main() -> None:
    name = "Tejus Gupta"
    github_username = "tejus3131"
    email = "tejus3131@gmail.com"

    parser = argparse.ArgumentParser(description="Add docstrings to a file")
    parser.add_argument("input_file", type=str, help="The input file to process")
    parser.add_argument(
        "output_file", type=str, help="The output file to save the result"
    )
    args = parser.parse_args()

    add_docstrings_to_file(
        name, github_username, email, args.input_file, args.output_file
    )


if __name__ == "__main__":
    main()
