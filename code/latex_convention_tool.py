import os
import re
import json
from collections import defaultdict
from statistics import mean

# ---------- Folder Tree Builder ----------
def build_folder_tree(base_path):
    tree = defaultdict(dict)
    def add_path(current_dict, path_parts):
        if not path_parts: return
        head, *tail = path_parts
        if head not in current_dict:
            current_dict[head] = {}
        add_path(current_dict[head], tail)
    for root, dirs, files in os.walk(base_path):
        rel_path = os.path.relpath(root, base_path)
        if rel_path == ".": continue
        path_parts = rel_path.split(os.sep)
        add_path(tree, path_parts)
    return tree

# ---------- File Role Classifier ----------
def classify_file(file_path):
    path = file_path.lower()
    name = os.path.basename(path)
    if "abstract" in path: return "abstract"
    elif "intro" in path: return "introduction"
    elif "method" in path: return "methods"
    elif "result" in path or "eval" in path: return "results"
    elif "conclu" in path or "discuss" in path: return "conclusion"
    elif "appendix" in path or "appendice" in path: return "appendix"
    elif "chapter" in path or "section" in path: return "body"
    elif name in ["main.tex", "thesis.tex"]: return "main"
    else: return "other"

# ---------- Verna Feature Extractors ----------
def check_verna_comment_style(lines):
    return any(re.match(r"%\s*={2,}", line.strip()) for line in lines)

def extract_verna_style_features(lines):
    usepackage_lines = [line for line in lines if line.strip().startswith("\\usepackage")]
    alphabetized = usepackage_lines == sorted(usepackage_lines, key=lambda x: x.lower())
    return {
        "has_verna_comment_blocks": check_verna_comment_style(lines),
        "packages_alphabetized": alphabetized
    }

# ---------- Utility ----------
def is_comment(line):
    return line.strip().startswith("%")

def detect_indentation(lines):
    spaces = [len(line) - len(line.lstrip(' ')) for line in lines if line.startswith(' ')]
    tabs = [len(line) - len(line.lstrip('\t')) for line in lines if line.startswith('\t')]
    if spaces:
        return "spaces", min(set(spaces))
    elif tabs:
        return "tabs", min(set(tabs))
    return "unknown", 0

# ---------- Main Analysis Function ----------
def analyze_latex_project(path):
    summary = {
        "project_id": os.path.basename(path),
        "files_and_structure": {
            "num_tex_files": 0,
            "tex_files": [],
            "folders": set(),
            "file_roles": defaultdict(int),
            "uses_input_include": False,
            "has_makefile": os.path.exists(os.path.join(path, "Makefile")),
            "has_readme": os.path.exists(os.path.join(path, "README.md"))
        },
        "macros": {
            "num_custom_macros": 0,
            "macro_prefixes": set(),
            "uses_parameters_in_macros": False,
            "redefines_builtin_commands": False
        },
        "preamble": {
            "num_packages": 0,
            "used_packages": set(),
            "preamble_line_count": 0,
            "has_comment_sections": False
        },
        "code_style": {
            "avg_line_length": 0,
            "longest_line_length": 0,
            "indentation_style": "unknown",
            "indentation_width": 0,
            "comment_ratio": 0.0
        },
        "structure_elements": {
            "sectioning_depth": {"section": 0, "subsection": 0, "subsubsection": 0},
            "environments_used": set(),
            "uses_labels_and_refs": False,
            "citation_commands": set()
        },
        "verna_features": {
            "has_verna_comment_blocks": False,
            "packages_alphabetized": False
        },
        "folder_tree": build_folder_tree(path)
    }

    line_lengths = []
    total_lines = 0
    comment_lines = 0
    all_lines = []
    preamble_lines = []

    # Patterns
    macro_pattern = re.compile(r"\\(?:newcommand|renewcommand)\{\\(\w+)")
    param_macro_pattern = re.compile(r"\\(?:newcommand|renewcommand)\{\\\w+\}\[(\d)\]")
    package_pattern = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^\}]*)\}")
    section_pattern = re.compile(r"\\(subsubsection|subsection|section)\{")
    env_pattern = re.compile(r"\\begin\{(\w+)\}")
    label_pattern = re.compile(r"\\(label|ref|autoref)\{")
    cite_pattern = re.compile(r"\\(cite\w*)\{")
    redefine_pattern = re.compile(r"\\renewcommand\{\\(?:thesection|thefigure|thetable)")

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".tex"):
                summary["files_and_structure"]["num_tex_files"] += 1
                tex_path = os.path.join(root, file)
                rel_tex_path = os.path.relpath(tex_path, path)
                summary["files_and_structure"]["tex_files"].append(rel_tex_path)
                summary["files_and_structure"]["folders"].add(os.path.relpath(root, path))
                role = classify_file(rel_tex_path)
                summary["files_and_structure"]["file_roles"][role] += 1

                with open(tex_path, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                    if summary["preamble"]["preamble_line_count"] == 0:
                        for i, line in enumerate(lines):
                            if r"\begin{document}" in line:
                                summary["preamble"]["preamble_line_count"] = i
                                break

                    all_lines.extend(lines)
                    total_lines += len(lines)
                    comment_lines += sum(1 for line in lines if is_comment(line))
                    line_lengths.extend([len(line) for line in lines])

                    for line in lines:
                        if "\\input{" in line or "\\include{" in line:
                            summary["files_and_structure"]["uses_input_include"] = True
                        if line.strip().startswith("\\usepackage"):
                            preamble_lines.append(line)
                        for match in macro_pattern.findall(line):
                            summary["macros"]["num_custom_macros"] += 1
                            summary["macros"]["macro_prefixes"].add(match)
                        if param_macro_pattern.search(line):
                            summary["macros"]["uses_parameters_in_macros"] = True
                        if redefine_pattern.search(line):
                            summary["macros"]["redefines_builtin_commands"] = True
                        if package_match := package_pattern.search(line):
                            packages = [pkg.strip() for pkg in package_match.group(1).split(",")]
                            summary["preamble"]["used_packages"].update(packages)
                        for sec in section_pattern.findall(line):
                            summary["structure_elements"]["sectioning_depth"][sec] += 1
                        for env in env_pattern.findall(line):
                            summary["structure_elements"]["environments_used"].add(env)
                        if label_pattern.search(line):
                            summary["structure_elements"]["uses_labels_and_refs"] = True
                        if cite_match := cite_pattern.search(line):
                            summary["structure_elements"]["citation_commands"].add(cite_match.group(1))

    # Final calculations
    if total_lines:
        summary["code_style"]["comment_ratio"] = round(comment_lines / total_lines, 2)
    if line_lengths:
        summary["code_style"]["avg_line_length"] = round(mean(line_lengths), 2)
        summary["code_style"]["longest_line_length"] = max(line_lengths)
    style, width = detect_indentation(all_lines)
    summary["code_style"]["indentation_style"] = style
    summary["code_style"]["indentation_width"] = width
    summary["preamble"]["num_packages"] = len(summary["preamble"]["used_packages"])
    summary["preamble"]["has_comment_sections"] = any("%" in line for line in all_lines[:50])
    summary["files_and_structure"]["folders"] = sorted(summary["files_and_structure"]["folders"])
    summary["macros"]["macro_prefixes"] = sorted(summary["macros"]["macro_prefixes"])
    summary["preamble"]["used_packages"] = sorted(summary["preamble"]["used_packages"])
    summary["structure_elements"]["environments_used"] = sorted(summary["structure_elements"]["environments_used"])
    summary["structure_elements"]["citation_commands"] = sorted(summary["structure_elements"]["citation_commands"])
    summary["files_and_structure"]["file_roles"] = dict(summary["files_and_structure"]["file_roles"])
    summary["files_and_structure"]["total_line_count"] = total_lines
    summary["files_and_structure"]["total_character_count"] = sum(line_lengths)
    summary["files_and_structure"]["num_folders"] = len(summary["files_and_structure"]["folders"])
    summary["files_and_structure"]["modularity_score"] = (
    summary["files_and_structure"]["num_tex_files"]
    + summary["files_and_structure"]["num_folders"]
    + (2 if summary["files_and_structure"]["uses_input_include"] else 0)
)

    # Verna feature extraction
    summary["verna_features"] = extract_verna_style_features(all_lines)

    return summary

# ---------- Entry Point ----------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze a LaTeX project for structural and stylistic patterns.")
    parser.add_argument("path", help="Path to LaTeX project")
    parser.add_argument("--output", help="Path to save summary JSON", default="latex_project_summary.json")
    args = parser.parse_args()

    summary = analyze_latex_project(args.path)
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary saved to {args.output}")