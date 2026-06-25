"""
analyzer.py — Code Analysis Engine
Performs AST-based analysis on Python code to detect:
  - Time & Space complexity
  - Errors (syntax, undefined vars, unused imports)
  - Optimality assessment
"""

import ast
import sys
import io
import re
import py_compile
import tempfile
import os


# ─────────────────────────────────────────────
#  ERROR DETECTION
# ─────────────────────────────────────────────

def detect_errors(code: str) -> list[dict]:
    """
    Detect syntax errors, undefined names, unused imports, and common issues.
    Returns a list of {"line": int, "column": int, "message": str}.
    """
    errors = []

    # 1) Syntax errors via compile()
    try:
        compile(code, "<user_code>", "exec")
    except SyntaxError as e:
        errors.append({
            "line": e.lineno or 1,
            "column": e.offset or 0,
            "message": f"SyntaxError: {e.msg}"
        })
        return errors  # Can't do further analysis on broken syntax

    # 2) AST-based analysis
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return errors

    # Collect defined names, imported names, used names
    defined_names = set()
    imported_names = {}       # name -> line
    used_names = set()
    assigned_names = set()
    function_defs = set()

    for node in ast.walk(tree):
        # Track imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names[name] = node.lineno
                defined_names.add(name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names[name] = node.lineno
                defined_names.add(name)

        # Track function/class definitions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_names.add(node.name)
            function_defs.add(node.name)
            for arg in node.args.args:
                defined_names.add(arg.arg)
        elif isinstance(node, ast.ClassDef):
            defined_names.add(node.name)

        # Track assignments
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)
                    assigned_names.add(target.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)

        # Track for-loop variables
        elif isinstance(node, ast.For):
            if isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)

        # Track name usage
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_names.add(node.id)

    # Built-in names that shouldn't be flagged
    builtins_set = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
    common_globals = {"__name__", "__file__", "__doc__", "True", "False", "None",
                      "print", "range", "len", "int", "str", "float", "list",
                      "dict", "set", "tuple", "type", "input", "open", "sum",
                      "min", "max", "abs", "sorted", "reversed", "enumerate",
                      "zip", "map", "filter", "any", "all", "isinstance",
                      "issubclass", "super", "property", "staticmethod",
                      "classmethod", "ValueError", "TypeError", "KeyError",
                      "IndexError", "AttributeError", "Exception", "RuntimeError",
                      "StopIteration", "NotImplementedError", "OSError",
                      "FileNotFoundError", "ZeroDivisionError", "ImportError",
                      "hasattr", "getattr", "setattr", "delattr", "callable",
                      "iter", "next", "id", "hash", "repr", "format", "vars",
                      "dir", "globals", "locals", "exec", "eval", "compile",
                      "breakpoint", "exit", "quit", "help", "object", "bool",
                      "bytes", "bytearray", "memoryview", "complex", "frozenset",
                      "chr", "ord", "hex", "oct", "bin", "pow", "round",
                      "divmod", "slice", "ascii"}
    safe_names = builtins_set | common_globals | {"self", "cls", "args", "kwargs"}

    # 3) Check for unused imports
    for name, line in imported_names.items():
        if name not in used_names and name not in function_defs:
            errors.append({
                "line": line,
                "column": 0,
                "message": f"Unused import: '{name}'"
            })

    # 4) Check for potentially undefined names (heuristic)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined_names and node.id not in safe_names:
                errors.append({
                    "line": node.lineno,
                    "column": node.col_offset,
                    "message": f"Possibly undefined name: '{node.id}'"
                })

    # De-duplicate
    seen = set()
    unique_errors = []
    for e in errors:
        key = (e["line"], e["message"])
        if key not in seen:
            seen.add(key)
            unique_errors.append(e)

    return sorted(unique_errors, key=lambda e: e["line"])


# ─────────────────────────────────────────────
#  COMPLEXITY ANALYSIS
# ─────────────────────────────────────────────

def _get_max_loop_depth(node, current_depth=0) -> int:
    """Recursively compute the max nesting depth of for/while loops."""
    max_depth = current_depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.For, ast.While)):
            d = _get_max_loop_depth(child, current_depth + 1)
            max_depth = max(max_depth, d)
        else:
            d = _get_max_loop_depth(child, current_depth)
            max_depth = max(max_depth, d)
    return max_depth


def _has_recursion(tree) -> bool:
    """Detect if any function calls itself (direct recursion)."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fname = node.name
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name) and child.func.id == fname:
                        return True
    return False


def _has_sorting(tree) -> bool:
    """Detect common sorting calls like sorted(), .sort()."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "sorted":
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr == "sort":
                return True
    return False


def _has_divide_and_conquer(tree) -> bool:
    """Heuristic: function with recursion + slicing or halving patterns."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_rec = False
            has_halving = False
            fname = node.name
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name) and child.func.id == fname:
                        has_rec = True
                if isinstance(child, ast.BinOp) and isinstance(child.op, ast.FloorDiv):
                    has_halving = True
                if isinstance(child, ast.Subscript) and isinstance(child.slice, ast.Slice):
                    has_halving = True
            if has_rec and has_halving:
                return True
    return False


def _uses_hashmap(tree) -> bool:
    """Detect dict/set usage which implies O(1) lookups."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Dict, ast.Set)):
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("dict", "set", "defaultdict", "Counter"):
                return True
    return False


def _count_collections(tree) -> int:
    """Count list/dict/set creations for space complexity."""
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Dict, ast.Set)):
            count += 1
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("list", "dict", "set", "defaultdict", "Counter", "deque"):
                count += 1
    return count


def analyze_complexity(code: str) -> dict:
    """
    Analyze time and space complexity of Python code.
    Returns {"time_complexity": str, "space_complexity": str, "details": str}.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {
            "time_complexity": "N/A (syntax error)",
            "space_complexity": "N/A (syntax error)",
            "details": "Cannot analyze complexity due to syntax errors."
        }

    max_depth = _get_max_loop_depth(tree)
    has_rec = _has_recursion(tree)
    has_sort = _has_sorting(tree)
    has_dac = _has_divide_and_conquer(tree)
    uses_hash = _uses_hashmap(tree)
    collection_count = _count_collections(tree)

    details_parts = []

    # ── Time Complexity ──
    if has_dac:
        time_complexity = "O(n log n)"
        details_parts.append("Divide-and-conquer pattern detected (recursion + halving)")
    elif has_sort and max_depth <= 1:
        time_complexity = "O(n log n)"
        details_parts.append("Sorting operation detected")
    elif has_rec and max_depth == 0:
        time_complexity = "O(2^n)"
        details_parts.append("Recursion detected without memoization — possibly exponential")
    elif has_rec and uses_hash:
        time_complexity = "O(n)"
        details_parts.append("Recursion with memoization/hashmap detected")
    elif max_depth == 0:
        time_complexity = "O(1)" if not has_rec else "O(n)"
        if not has_rec:
            details_parts.append("No loops or recursion — constant time")
        else:
            details_parts.append("Simple recursion detected — likely linear")
    elif max_depth == 1:
        time_complexity = "O(n)"
        details_parts.append(f"Single loop detected (depth {max_depth})")
    elif max_depth == 2:
        time_complexity = "O(n²)"
        details_parts.append(f"Nested loops detected (depth {max_depth})")
    elif max_depth == 3:
        time_complexity = "O(n³)"
        details_parts.append(f"Triple-nested loops detected (depth {max_depth})")
    else:
        time_complexity = f"O(n^{max_depth})"
        details_parts.append(f"Deeply nested loops detected (depth {max_depth})")

    if has_sort and max_depth >= 1 and not has_dac:
        time_complexity = f"O(n^{max_depth} · log n)"
        details_parts.append("Sorting inside loops adds a log n factor")

    # ── Space Complexity ──
    if collection_count == 0 and not has_rec:
        space_complexity = "O(1)"
        details_parts.append("No significant extra data structures allocated")
    elif has_rec:
        space_complexity = "O(n)"
        details_parts.append("Recursion uses call stack space proportional to input")
    elif collection_count >= 1:
        space_complexity = "O(n)"
        details_parts.append(f"{collection_count} data structure(s) detected — likely scales with input")
    else:
        space_complexity = "O(1)"

    return {
        "time_complexity": time_complexity,
        "space_complexity": space_complexity,
        "details": "; ".join(details_parts)
    }


# ─────────────────────────────────────────────
#  OPTIMALITY ASSESSMENT
# ─────────────────────────────────────────────

COMPLEXITY_ORDER = {
    "O(1)": 0, "O(log n)": 1, "O(n)": 2, "O(n log n)": 3,
    "O(n²)": 4, "O(n³)": 5, "O(2^n)": 6, "O(n!)": 7
}

def assess_optimality(time_complexity: str) -> dict:
    """
    Classify code as Optimal / Near-Optimal / Moderate / Brute Force.
    """
    # Normalise
    tc = time_complexity.strip()

    rank = COMPLEXITY_ORDER.get(tc, None)

    # Try to match pattern like O(n^4)
    if rank is None:
        m = re.match(r"O\(n\^(\d+)\)", tc)
        if m:
            exp = int(m.group(1))
            rank = 3 + exp  # n^2 → 5, n^3 → 6, ...

    if rank is None:
        if "log" in tc:
            rank = 3
        elif "2^n" in tc or "!" in tc:
            rank = 6
        else:
            rank = 4  # default mid

    if rank <= 1:
        label = "[OPTIMAL]"
        desc = "Excellent! This is the most efficient approach."
    elif rank <= 3:
        label = "[NEAR-OPTIMAL]"
        desc = "Very good. This is close to the best possible solution."
    elif rank <= 4:
        label = "[MODERATE]"
        desc = "Acceptable, but there may be a more efficient approach."
    elif rank <= 5:
        label = "[COULD BE IMPROVED]"
        desc = "This is expensive. Consider optimizing with better data structures or algorithms."
    else:
        label = "[BRUTE FORCE]"
        desc = "Very expensive. This approach is likely brute-force and will not scale well."

    return {
        "label": label,
        "description": desc,
        "rank": rank
    }


# ─────────────────────────────────────────────
#  MAIN ORCHESTRATOR
# ─────────────────────────────────────────────

def analyze_code(code: str, language: str = "python") -> dict:
    """
    Full analysis pipeline. Returns a JSON-serialisable dict.
    """
    if language.lower() != "python":
        return {
            "language": language,
            "supported": False,
            "message": f"Analysis for '{language}' is not yet supported. Currently only Python is supported.",
            "time_complexity": "N/A",
            "space_complexity": "N/A",
            "optimality": {"label": "N/A", "description": "Language not supported", "rank": -1},
            "errors": [],
            "error_count": 0
        }

    errors = detect_errors(code)
    complexity = analyze_complexity(code)
    optimality = assess_optimality(complexity["time_complexity"])

    lines = code.strip().split("\n")

    return {
        "language": language,
        "supported": True,
        "total_lines": len(lines),
        "time_complexity": complexity["time_complexity"],
        "space_complexity": complexity["space_complexity"],
        "complexity_details": complexity["details"],
        "optimality": optimality,
        "errors": errors,
        "error_count": len(errors)
    }
