import os
import subprocess

input_dir = "Data_git/"       # Folder with your LaTeX repos
output_dir = "out_git/"  # Folder to save summaries
script = "code/latex_convention_tool.py"  # Your analyzer script

os.makedirs(output_dir, exist_ok=True)

for repo in os.listdir(input_dir):
    repo_path = os.path.join(input_dir, repo)
    if os.path.isdir(repo_path):
        output_path = os.path.join(output_dir, f"{repo}.json")
        subprocess.run([
            "python3", script,
            repo_path,
            "--output", output_path
        ])