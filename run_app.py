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
    time.sleep(2)
    
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
