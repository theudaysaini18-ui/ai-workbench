import subprocess
import tempfile
import os


def run_python_code(code: str, timeout: int = 10) -> dict:
    """Executes Python code inside an isolated, network-disabled Docker container.

    Args:
        code: The Python source code to execute.
        timeout: Max wall-clock seconds before the process is killed.

    Returns:
        dict with keys: stdout, stderr, exit_code.
    """
    with tempfile.TemporaryDirectory() as tmp:
        script_path = os.path.join(tmp, "script.py")
        with open(script_path, "w") as f:
            f.write(code)
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "--network", "none",
                    "--memory", "512m",
                    "--cpus", "1",
                    "--pids-limit", "64",
                    "--cap-drop", "ALL",
                    "-v", f"{tmp}:/workspace:rw",
                    "-w", "/workspace",
                    "sih-sandbox:latest",
                    "python", "script.py",
                ],
                capture_output=True, text=True, timeout=timeout,
            )
            return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Execution timed out", "exit_code": -1}
        except FileNotFoundError:
            return {"stdout": "", "stderr": "Docker not found on this machine", "exit_code": -1}


if __name__ == "__main__":
    test_result = run_python_code("print(sum(range(10)))")
    print(test_result)