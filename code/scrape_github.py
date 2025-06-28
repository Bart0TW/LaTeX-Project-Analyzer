import requests
import os
import subprocess

# === CONFIGURATION ===
TOKEN = "<TOKEN_HERE>" # Replace with your GitHub token
SEARCH_TERM = "=thesis+language%3ATeX++is%3Apublic+NOT+template+NOT+sample+NOT+example+NOT+class&type=repositories&"
MIN_SIZE_KB = 1024  # 1MB
PER_PAGE = 50       # GitHub API max per page is 100
OUTPUT_DIR = "out"
TO_SEARCH = 10
CLONED_FILE = "cloned_repos.txt"

# === SETUP ===
HEADERS = {"Authorization": f"token {TOKEN}"}
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Ensure output folder exists

if os.path.exists(CLONED_FILE):
    with open(CLONED_FILE, "r") as f:
        cloned_repos = set(line.strip() for line in f)
else:
    cloned_repos = set()


def search_repos(page=1):
    url = f"https://api.github.com/search/repositories?q={SEARCH_TERM}+language:TeX&per_page={PER_PAGE}&page={page}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print("GitHub API error:", response.status_code, response.text)
        return []
    return response.json().get('items', [])

def clone_repos():
    page = 1
    count = 0
    with open(CLONED_FILE, "a") as f:  # Open once for appending
        while True:
            repos = search_repos(page)
            if not repos:
                break

            for repo in repos:
                name = repo['full_name']
                if name in cloned_repos:
                    print(f"Skipping {name} — already in log.")
                    continue

                if repo['size'] >= MIN_SIZE_KB:
                    print(f"Cloning {name} ({repo['size']} KB)...")

                    # Build local path
                    local_repo_path = os.path.join(
                        OUTPUT_DIR, name.replace("/", "__"))
                    if os.path.exists(local_repo_path):
                        print(f"Skipping {name} — already exists in folder.")
                        cloned_repos.add(name)
                        f.write(name + "\n")
                        continue

                    # Clone into target directory
                    subprocess.run([
                        "git", "clone", "--depth=1", repo['clone_url'], local_repo_path
                    ])
                    f.write(name + "\n")
                    cloned_repos.add(name)
                    count += 1
                    if count >= TO_SEARCH:
                        return
            page += 1


clone_repos()