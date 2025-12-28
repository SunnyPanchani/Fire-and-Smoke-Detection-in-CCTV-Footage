import os
import ast
import re

def analyze_python_file(file_path):
    """Extract imports, functions, and classes from a Python file without code logic."""
    imports = []
    functions = []
    classes = {}

    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    # Parse AST for functions and classes
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        print(f"Skipping {file_path} due to syntax error: {e}")
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # If inside a class, add under that class
            parent_class = next(
                (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and node in n.body),
                None
            )
            if parent_class:
                classes.setdefault(parent_class.name, []).append(node.name)
            else:
                functions.append(node.name)

        elif isinstance(node, ast.ClassDef):
            classes.setdefault(node.name, [])

    # Extract imports with regex (to keep formatting like "import x as y" or "from x import y")
    for line in source.splitlines():
        if re.match(r'^\s*(import|from)\s+', line):
            imports.append(line.strip())

    return {
        "file": os.path.basename(file_path),
        "imports": imports,
        "functions": functions,
        "classes": classes
    }


def analyze_folder(folder_path):
    """Analyze all Python files in a folder."""
    results = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".py"):
            file_path = os.path.join(folder_path, file_name)
            analysis = analyze_python_file(file_path)
            if analysis:
                results.append(analysis)
    return results


def pretty_print(results):
    for res in results:
        print(f"\n{res['file']}")
        for imp in res['imports']:
            print(f"   {imp}")
        for func in res['functions']:
            print(f"   def {func}():")
        for cls, methods in res['classes'].items():
            print(f"   class {cls}:")
            for m in methods:
                print(f"         def {m}(self):")


if __name__ == "__main__":
    folder = "."  # Change this to your project folder path
    results = analyze_folder(folder)
    pretty_print(results)
