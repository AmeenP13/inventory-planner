import subprocess
import sys
import time
import threading
import os

def main():
    # Set the working directory to the folder containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print("====================================================")
    print("         STARTING STOCKMIND FULL STACK              ")
    print("====================================================")
    
    # 0. Free ports 8000 and 8501 if already occupied
    import socket as _sock
    def _kill_port(port):
        """Kill any process listening on the given port (Windows)."""
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    pid = parts[-1]
                    if pid.isdigit():
                        subprocess.run(["taskkill", "/PID", pid, "/F"],
                                       capture_output=True)
                        print(f"[*] Freed port {port} (killed PID {pid})")
        except Exception:
            pass

    _kill_port(8000)
    _kill_port(8501)
    time.sleep(1)  # Brief pause so OS releases the ports

    # 1. Start Backend (FastAPI)
    print("[*] Starting FastAPI Backend on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Wait for the backend port to start up
    print("[*] Waiting for FastAPI backend to bind to port 8000...")
    import socket
    backend_ready = False
    for _ in range(15):
        try:
            with socket.create_connection(("127.0.0.1", 8000), timeout=1):
                backend_ready = True
                break
        except OSError:
            time.sleep(1)
    if backend_ready:
        print("[+] FastAPI backend is ready!")
    else:
        print("[!] Warning: FastAPI backend did not start within 15 seconds. Proceeding anyway...")
    
    # 2. Start Frontend (Streamlit)
    print("[*] Starting Streamlit Frontend on http://localhost:8501 ...")
    frontend_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/frontend/app.py", "--server.port", "8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Thread logic to forward subprocess logs in real-time
    def forward_output(process, name):
        try:
            for line in iter(process.stdout.readline, ''):
                sys.stdout.write(f"[{name}] {line}")
                sys.stdout.flush()
        except Exception:
            pass
            
    t1 = threading.Thread(target=forward_output, args=(backend_proc, "BACKEND"), daemon=True)
    t2 = threading.Thread(target=forward_output, args=(frontend_proc, "FRONTEND"), daemon=True)
    t1.start()
    t2.start()
    
    print("\n[+] Full stack is running! Press CTRL+C to terminate both servers.")
    try:
        while True:
            # If backend or frontend crashes, terminate the stack
            if backend_proc.poll() is not None:
                print(f"\n[!] Backend process exited with code {backend_proc.poll()}")
                break
            if frontend_proc.poll() is not None:
                print(f"\n[!] Frontend process exited with code {frontend_proc.poll()}")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Terminating processes...")
    finally:
        backend_proc.terminate()
        frontend_proc.terminate()
        try:
            backend_proc.wait(timeout=3)
            frontend_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            backend_proc.kill()
            frontend_proc.kill()
        print("[+] StockMind shut down successfully.")

if __name__ == "__main__":
    main()
