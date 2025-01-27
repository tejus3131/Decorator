import ast
import astor  # type: ignore
import os


class DocstringGenerator(ast.NodeVisitor):
    """
    description: A class to generate structured docstrings for functions and classes.
    """

    def __init__(self, *, name: str, github_username: str, email: str):
        self.updated_code = ""
        self.author_info = {
            "name": name,
            "github": github_username,
            "email": email,
            "github_url": f"https://github.com/{github_username}",
        }

    def extract_class_metadata(self, node):
        """description: Extract metadata from comments in the class's body."""

        metadata = {
            "name": node.name,
            "description": "",
            "methods": [],
            "classes": [],
            "extra": [],
        }
        if not node.body:
            return metadata

        doc_strings = []
        functions = []
        classes = []

        for stmt in node.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                doc_strings.append(stmt.value.s)
                metadata["extra"].append(stmt)
            elif isinstance(stmt, ast.FunctionDef):
                functions.append(stmt)
            elif isinstance(stmt, ast.ClassDef):
                classes.append(stmt)

        for doc_string in doc_strings:
            if doc_string.startswith("description:"):
                metadata["description"] = doc_string.replace(
                    "description:", "")

        metadata["methods"] = functions
        metadata["classes"] = classes

        return metadata

    def generate_class_docstring(self, metadata):
        """description: Generate a structured docstring based on extracted metadata."""
        docstring_lines = [
            f"# {metadata['name']}",
            "---",
            f"### {metadata['description']}",
            "---",
        ]
        flag = False
        if metadata["methods"]:
            flag = True
            docstring_lines.append("## Methods:")
            for method in metadata["methods"]:
                if method.name.startswith("__"):
                    continue
                docstring_lines.append(
                    f"- `{method.name}()`: {self.extract_function_metadata(method)
                                            ['description']}"
                )
            docstring_lines.append("")
        if metadata["classes"]:
            flag = True
            docstring_lines.append("## Classes:")
            for class_ in metadata["classes"]:
                docstring_lines.append(f"- `{class_.name}`")
            docstring_lines.append("")
        if flag:
            docstring_lines.append("---")
        docstring_lines.append(
            f"Author: `{self.author_info['name']}` <[{self.author_info['github']}]({
                self.author_info['github_url']}), {self.author_info['email']}>"
        )
        return "\n".join(docstring_lines)

    def visit_ClassDef(self, node):
        metadata = self.extract_class_metadata(node)
        for item in metadata["extra"]:
            node.body.remove(item)
        enhanced_docstring = self.generate_class_docstring(metadata)
        node.body.insert(0, ast.Expr(value=ast.Constant(s=enhanced_docstring)))
        self.generic_visit(node)

    def extract_function_metadata(self, node):
        """description: Extract metadata from comments in the function's body."""
        metadata = {
            "name": node.name,
            "description": None,
            "parameters": [],
            "exception_message": None,
            "exceptions": [],
            "returns_message": None,
            "returns": "",
            "is_return": False,
            "example": None,
            "extra": [],
        }
        if not node.body:
            return metadata

        params = node.args.args if node.args.args else []
        param_name = {
            param.arg: {
                "type": param.annotation.id if param.annotation else "...",
                "msg": None,
            }
            for param in params
        }

        # return_args =

        doc_strings = []
        exceptions = []
        returns = None

        if node.returns:
            if isinstance(node.returns, ast.Name):
                returns = node.returns.id
            elif isinstance(node.returns, ast.BinOp):
                if isinstance(node.returns.left, ast.Name):
                    left = node.returns.left.id
                elif isinstance(node.returns.left, ast.Constant):
                    left = node.returns.left.value

                if isinstance(node.returns.right, ast.Name):
                    right = node.returns.right.id
                elif isinstance(node.returns.right, ast.Constant):
                    right = node.returns.right.value

                returns = f"{left} or {right}"

        for stmt in node.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                doc_strings.append(stmt.value.s)
                metadata["extra"].append(stmt)
            elif isinstance(stmt, ast.Raise):
                exceptions.append(
                    (stmt.exc.id, stmt.exe.args.value if stmt.exc.args else "")
                )
            elif isinstance(stmt, ast.Return):
                metadata["is_return"] = True

        for doc_string in doc_strings:
            if doc_string.startswith("description:"):
                metadata["description"] = doc_string.replace(
                    "description:", "")
            elif doc_string.startswith("example:"):
                metadata["example"] = doc_string.replace("example:", "")
            elif doc_string.startswith("return:"):
                metadata["returns_message"] = doc_string.replace("return:", "")
            elif doc_string.startswith("exception:"):
                metadata["exception_message"] = doc_string.replace(
                    "exception:", "")
            else:
                for param in param_name.keys():
                    if doc_string.startswith(f"{param}:"):
                        msg = doc_string.replace(f"{param}:", "")
                        param_name[param]["msg"] = msg
                        break

        metadata["parameters"] = param_name
        metadata["exceptions"] = exceptions
        metadata["returns"] = returns

        return metadata

    def generate_function_docstring(self, metadata):
        """description: Generate a structured docstring based on extracted metadata."""
        docstring_lines = [
            f"# {metadata['name']}",
            "---",
            f"### {metadata['description']}",
            "---",
        ]
        flag = False
        if metadata["parameters"]:
            flag = True
            docstring_lines.append("## Parameters:")
            for param, details in metadata["parameters"].items():
                if param == "self" or param == "cls":
                    docstring_lines.append(f"- `{param}`")
                else:
                    docstring_lines.append(
                        f"- `{param}`: {details['type']} - {details['msg']
                                                            if details['msg'] else '...'}"
                    )
            docstring_lines.append("")
        if metadata["returns"] or metadata["returns_message"]:
            flag = True
            docstring_lines.append("## Returns:")
            docstring_lines.append(
                f"- {metadata['returns']} - {
                    metadata['returns_message'] if metadata['returns_message'] else '...'}"
            )
            docstring_lines.append("")
        elif metadata["is_return"]:
            flag = True
            docstring_lines.append("## Returns:")
            docstring_lines.append(f"- Any - ...")
            docstring_lines.append("")
        if metadata["exception_message"] or metadata["exceptions"]:

            flag = True
            docstring_lines.append("## Raises:")
            if metadata["exception_message"]:
                docstring_lines.append(f"- {metadata['exception_message']}")
            for exception in metadata["exceptions"]:
                docstring_lines.append(f"- `{exception[0]}`: {exception[1]}")
            docstring_lines.append("")
        if flag:
            docstring_lines.append("---")
        if metadata["example"]:
            docstring_lines.append("## Example:")
            docstring_lines.append(f"```python\n{metadata['example']}\n```")
            docstring_lines.append("---")
        docstring_lines.append(
            f"Author: `{self.author_info['name']}` <[{self.author_info['github']}]({
                self.author_info['github_url']}), {self.author_info['email']}>"
        )
        return "\n".join(docstring_lines)

    def visit_FunctionDef(self, node):
        metadata = self.extract_function_metadata(node)
        for item in metadata["extra"]:
            node.body.remove(item)
        enhanced_docstring = self.generate_function_docstring(metadata)
        node.body.insert(0, ast.Expr(value=ast.Constant(s=enhanced_docstring)))
        self.generic_visit(node)

    def extract_async_function_metadata(self, node):
        """
        Extract metadata from comments in the async function's body.
        """
        metadata = {
            "name": node.name,
            "description": "...",
            "parameters": [],
            "exception_message": "...",
            "exceptions": [],
            "returns_message": "...",
            "returns": "",
            "example": None,
            "extra": [],
        }
        if not node.body:
            return metadata

        params = node.args.args if node.args.args else []
        param_name = {
            param.arg: {
                "type": param.annotation.id if param.annotation else "...",
                "msg": None,
            }
            for param in params
        }

        # return_args =

        doc_strings = []
        exceptions = []
        returns = node.returns.id if node.returns else None

        for stmt in node.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                doc_strings.append(stmt.value.s)
                metadata["extra"].append(stmt)
            elif isinstance(stmt, ast.Raise):
                exceptions.append(
                    (stmt.exc.id, stmt.exe.args.value if stmt.exc.args else "")
                )

        for doc_string in doc_strings:
            if doc_string.startswith("description:"):
                metadata["description"] = doc_string.replace(
                    "description:", "")
            elif doc_string.startswith("example:"):
                metadata["example"] = doc_string.replace("example:", "")
            elif doc_string.startswith("return:"):
                metadata["returns_message"] = doc_string.replace("return:", "")
            elif doc_string.startswith("exception:"):
                metadata["exception_message"] = doc_string.replace(
                    "exception:", "")
            else:
                for param in param_name.keys():
                    if doc_string.startswith(f"{param}:"):
                        msg = doc_string.replace(f"{param}:", "")
                        param_name[param]["msg"] = msg
                        break

        metadata["parameters"] = param_name
        metadata["exceptions"] = exceptions
        metadata["returns"] = returns

        return metadata

    def generate_async_function_docstring(self, metadata):
        """
        Generate a structured docstring based on extracted metadata.
        """
        docstring_lines = [
            f"# {metadata['name']}",
            "---",
            f"### {metadata['description']}",
            "---",
        ]
        flag = False
        if metadata["parameters"]:
            flag = True
            docstring_lines.append("## Parameters:")
            for param, details in metadata["parameters"].items():
                if param == "self" or param == "cls":
                    docstring_lines.append(f"- `{param}`")
                else:
                    docstring_lines.append(
                        f"- `{param}`: {details['type']} - {details['msg']
                                                            if details['msg'] else '...'}"
                    )
            docstring_lines.append("")
        if metadata["returns"] or metadata["returns_message"]:
            flag = True
            docstring_lines.append("## Returns:")
            docstring_lines.append(
                f"- {metadata['returns']} - {metadata['returns_message']
                                             if metadata['returns_message'] else '...'}"
            )
            docstring_lines.append("")
        if metadata["exception_message"] or metadata["exceptions"]:
            flag = True
            docstring_lines.append("## Raises:")
            if metadata["exception_message"]:
                docstring_lines.append(f"- {metadata['exception_message']}")
            for exception in metadata["exceptions"]:
                docstring_lines.append(f"- `{exception[0]}`: {exception[1]}")
            docstring_lines.append("")
        if flag:
            docstring_lines.append("---")
        if metadata["example"]:
            docstring_lines.append("## Example:")
            docstring_lines.append(f"```python\n{metadata['example']}\n```")
            docstring_lines.append("---")
        docstring_lines.append(
            f"Author: `{self.author_info['name']}` <[{self.author_info['github']}]({
                self.author_info['github_url']}), {self.author_info['email']}>"
        )
        return "\n".join(docstring_lines)

    def visit_AsyncFunctionDef(self, node):
        metadata = self.extract_async_function_metadata(node)
        for item in metadata["extra"]:
            node.body.remove(item)
        enhanced_docstring = self.generate_async_function_docstring(metadata)
        node.body.insert(0, ast.Expr(value=ast.Str(s=enhanced_docstring)))
        self.generic_visit(node)


def add_docstrings_to_file(
        name,
        github_username,
        email,
        input_file,
        output_file
) ->tuple[bool, str]:
    """
    description: Add structured docstrings to a file.
    """
    with open(input_file, "r") as f:
        source_code = f.read()
    try:
        tree = ast.parse(source_code)
    except Exception as e:
        return False, f"Error in {input_file}\n\n{e.__class__.__name__}: {e.args[0]} at line {e.args[1][1]} in {input_file}"

    docstring_generator = DocstringGenerator(
        name=name, github_username=github_username, email=email
    )

    try:
        docstring_generator.visit(tree)
        updated_code = astor.to_source(tree)
    except Exception as e:
        return False, str(e)
    
    if os.path.exists(output_file):
        os.remove(output_file)
    elif not os.path.exists(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file))

    with open(output_file, "w") as f:
        f.write(updated_code)

    return True, f"Docstrings added to {input_file} and saved to {output_file}"
