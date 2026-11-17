import unittest
"""Test that all string annotations reference valid TYPE_CHECKING imports."""
import ast
import sys
from pathlib import Path


def check_undefined_names(filepath: Path) -> list[str]:
    """Check for undefined names in string annotations."""
    with open(filepath) as f:
        tree = ast.parse(f.read(), filename=str(filepath))
    
    # Collect TYPE_CHECKING imports
    type_checking_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check for if TYPE_CHECKING:
            if (isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING") or \
               (isinstance(node.test, ast.Attribute) and node.test.attr == "TYPE_CHECKING"):
                for stmt in node.body:
                    if isinstance(stmt, ast.ImportFrom):
                        for alias in stmt.names:
                            type_checking_names.add(alias.name)
                    elif isinstance(stmt, ast.Import):
                        for alias in stmt.names:
                            type_checking_names.add(alias.name)
    
    # Also check for from PIL import ... inside TYPE_CHECKING
    # The above handles ImportFrom
    
    # Now check string annotations
    errors = []
    for node in ast.walk(tree):
        # Function return annotation
        if isinstance(node, ast.FunctionDef):
            if node.returns and isinstance(node.returns, ast.Constant) and isinstance(node.returns.value, str):
                ann = node.returns.value
                # Check if it references a TYPE_CHECKING name
                for tc_name in type_checking_names:
                    if ann.startswith(tc_name + ".") or ann == tc_name:
                        break
                else:
                    # Check if it's a built-in or typing construct
                    if not any(ann.startswith(t) for t in ["list", "dict", "tuple", "set", "Optional", "Union", "Any", "Path", "int", "str", "float", "bool", "bytes", "None"]):
                        if "." in ann:
                            first = ann.split(".")[0]
                            if first not in type_checking_names and first not in ["Self", "typing", "collections", "datetime"]:
                                errors.append(f"{filepath}:{node.lineno}: undefined name '{ann}' in return annotation of '{node.name}'")
        
        # Argument annotations
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if arg.annotation and isinstance(arg.annotation, ast.Constant) and isinstance(arg.annotation.value, str):
                    ann = arg.annotation.value
                    for tc_name in type_checking_names:
                        if ann.startswith(tc_name + ".") or ann == tc_name:
                            break
                    else:
                        if not any(ann.startswith(t) for t in ["list", "dict", "tuple", "set", "Optional", "Union", "Any", "Path", "int", "str", "float", "bool", "bytes", "None"]):
                            if "." in ann:
                                first = ann.split(".")[0]
                                if first not in type_checking_names and first not in ["Self", "typing", "collections", "datetime"]:
                                    errors.append(f"{filepath}:{node.lineno}: undefined name '{ann}' in arg '{arg.arg}' of '{node.name}'")
    
    return errors


class TestNoUndefinedAnnotations(unittest.TestCase):
    """Test that string annotations don't reference undefined names."""
    
    def test_thumbnail_engine(self):
        errors = check_undefined_names(Path("geofactory/media/thumbnail_engine.py"))
        self.assertEqual(errors, [], f"Undefined annotations in thumbnail_engine.py:\n" + "\n".join(errors))
    
    def test_map_animation_engine(self):
        errors = check_undefined_names(Path("geofactory/media/map_animation_engine.py"))
        self.assertEqual(errors, [], f"Undefined annotations in map_animation_engine.py:\n" + "\n".join(errors))
    
    def test_all_geofactory(self):
        """Check all geofactory modules."""
        all_errors = []
        for py_file in Path("geofactory").rglob("*.py"):
            if "__pycache__" not in str(py_file):
                errors = check_undefined_names(py_file)
                all_errors.extend(errors)
        self.assertEqual(all_errors, [], f"Undefined annotations found:\n" + "\n".join(all_errors))


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)
