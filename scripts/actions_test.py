import os
import sys
import time


if __name__ == "__main__":
    ghwk_path = os.environ.get("GITHUB_WORKSPACE", "unkown")
    bno = os.environ.get("GITHUB_RUN_NUMBER", "1122334455")
    code_path = ghwk_path
    build_path = os.path.dirname(code_path) + f"/build_{bno}"
    print(build_path)
    if not os.path.exists(build_path):
        os.makedirs(build_path)
    
    with open(os.path.join(build_path, "report.html"), "w") as f:
        f.write("<h1>Hello Report</h1><p>This is a test.</p>")
    
    with open(os.environ.get("GITHUB_OUTPUT"), "a") as f:
        f.write(f"build_path={build_path}\n")
     
    sys.exit(0)