"""Local, dependency-free viewer for the generated Skill Library JSON."""

import argparse
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def make_server(library_path, page_path, host="127.0.0.1", port=8765, builder_path=None):
    library_path = Path(library_path).resolve()
    page_path = Path(page_path).resolve()
    builder_path = Path(builder_path).resolve() if builder_path else None

    class Handler(BaseHTTPRequestHandler):
        def send_data(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_error_json(self, status, message):
            self.send_data(status, json.dumps({"error": message}).encode(), "application/json; charset=utf-8")

        def do_GET(self):
            route = urlsplit(self.path).path
            if route in ("/", "/index.html"):
                try:
                    self.send_data(200, page_path.read_bytes(), "text/html; charset=utf-8")
                except OSError:
                    self.send_error_json(404, "Viewer HTML file is missing.")
                return
            if route != "/api/library":
                self.send_error_json(404, "Unknown route.")
                return

            if builder_path:
                sources = [builder_path, builder_path.parent / "types.json"]
                contract_files = sorted((builder_path.parent / "skills").glob("skill_*.json"))
                sources.extend(contract_files)
                try:
                    needs_build = not library_path.exists() or any(
                        source.stat().st_mtime_ns > library_path.stat().st_mtime_ns for source in sources
                    )
                    if not needs_build:
                        saved = json.loads(library_path.read_text(encoding="utf-8"))
                        saved_ids = {skill["id"] for skill in saved["skills"]}
                        source_ids = {json.loads(path.read_text(encoding="utf-8"))["id"] for path in contract_files}
                        needs_build = saved_ids != source_ids
                except (ValueError, KeyError, TypeError):
                    needs_build = True
                except OSError:
                    self.send_error_json(422, "Skill source files could not be read.")
                    return
                if needs_build:
                    try:
                        build = subprocess.run([sys.executable, str(builder_path)], capture_output=True, text=True, timeout=10)
                    except (OSError, subprocess.TimeoutExpired):
                        self.send_error_json(422, "Skill Library could not be rebuilt. Check the local Python command.")
                        return
                    if build.returncode:
                        self.send_error_json(422, "Skill Library could not be rebuilt. Check the source Contracts.")
                        return

            if not library_path.exists():
                self.send_error_json(404, "Skill Library JSON file is missing.")
                return
            try:
                library = json.loads(library_path.read_text(encoding="utf-8"))
                if not isinstance(library, dict) or not isinstance(library.get("skills"), list):
                    self.send_error_json(422, "Skill Library JSON must contain a skills list.")
                    return
                self.send_data(200, json.dumps(library, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            except (OSError, json.JSONDecodeError):
                self.send_error_json(422, "Skill Library JSON could not be read.")

        def log_message(self, format_string, *args):
            return

    return ThreadingHTTPServer((host, port), Handler)


def main():
    parser = argparse.ArgumentParser(description="View the current ZenoBench Skill Library in a browser")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    server = make_server(
        root / "skill_library.json", Path(__file__).with_name("index.html"),
        port=args.port, builder_path=root / "build.py"
    )
    print(f"Skill Library viewer: http://127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
