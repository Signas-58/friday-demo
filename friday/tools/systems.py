"""
Systems tools — lets F.R.I.D.A.Y. control applications, find local files, and monitor systems performance / network diagnostics.
"""

import os
import subprocess
import csv
import io
import re

def register(mcp):

    @mcp.tool()
    async def open_application(app_name: str) -> str:
        """
        Launches a local Windows application asynchronously.
        Use this when the user asks to launch or open a desktop app (e.g. calculator, notepad).
        """
        app_lower = app_name.lower().strip()
        
        # Alias map for common Windows tools
        aliases = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "terminal": "cmd.exe",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "edge": "msedge.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe"
        }
        
        target = aliases.get(app_lower, app_lower)
        
        # Ensure it has an extension if not fully specified
        if not target.endswith(".exe") and not os.path.isabs(target):
            target += ".exe"
            
        try:
            # Popen spawns process asynchronously, avoiding blocking the server
            subprocess.Popen(target, shell=True)
            return f"Understood, boss. Launching {app_name} on your desktop now."
        except Exception as e:
            return f"I'm unable to initialize the request for '{app_name}': {str(e)}"

    @mcp.tool()
    async def search_local_files(query: str, search_path: str = None) -> str:
        """
        Searches the local filesystem case-insensitively for files containing the query string.
        Use this when the user asks you to locate, search for, or find a file on their PC.
        """
        # Default to project root directory
        if not search_path:
            search_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        if not os.path.exists(search_path):
            return f"The search path '{search_path}' does not exist, sir."
            
        query_lower = query.lower()
        matches = []
        max_results = 20
        max_depth = 3
        
        # Build normalized base path depth
        base_depth = len(os.path.normpath(search_path).split(os.sep))
        
        # Folders to exclude
        exclude_dirs = {".git", ".venv", "env", "venv", "__pycache__", "static", "node_modules", ".gemini", ".agents"}
        
        try:
            for root, dirs, files in os.walk(search_path, topdown=True):
                # Filter out heavy/ignored directories in-place to prevent walking them
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                # Check depth
                current_depth = len(os.path.normpath(root).split(os.sep)) - base_depth
                if current_depth > max_depth:
                    dirs.clear()  # Stop descending
                    continue
                    
                for file in files:
                    if query_lower in file.lower():
                        matches.append(os.path.join(root, file))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
                    
            if not matches:
                return f"No matching files found for query '{query}' in path '{search_path}', sir."
                
            lines = [f"### Match Logs for '{query}' (Max Depth {max_depth}):"]
            for path in matches:
                # Format to forward slashes for link compatibility
                normalized_path = path.replace("\\", "/")
                lines.append(f"- [{os.path.basename(path)}](file:///{normalized_path})")
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error executing local filesystem search: {str(e)}"

    @mcp.tool()
    async def get_active_processes(limit: int = 15) -> str:
        """
        Lists running processes on the host Windows machine sorted by memory footprint.
        Use this when the user asks about system performance, CPU/memory hogs, or active tasks.
        """
        try:
            # Run tasklist CSV output command
            result = subprocess.run(["tasklist", "/fo", "csv"], capture_output=True, text=True, check=True)
            
            # Parse CSV
            reader = csv.reader(io.StringIO(result.stdout.strip()))
            header = next(reader)
            
            rows = []
            for row in reader:
                if len(row) < 5:
                    continue
                name, pid, session, session_num, mem_str = row[:5]
                # Mem footprint is formatted like '10,480 K' or '10.480 K' -> parse into numeric KB
                mem_clean = re.sub(r"[^\d]", "", mem_str)
                mem_kb = int(mem_clean) if mem_clean.isdigit() else 0
                rows.append({
                    "name": name,
                    "pid": pid,
                    "mem_kb": mem_kb,
                    "mem_display": mem_str
                })
                
            # Sort by memory usage descending
            rows.sort(key=lambda x: x["mem_kb"], reverse=True)
            
            # Format output table
            lines = [
                "### Systems Tasks (Heaviest Active Processes)",
                "",
                "| PID | Image Name | Memory Usage |",
                "| --- | --- | --- |"
            ]
            for row in rows[:limit]:
                lines.append(f"| {row['pid']} | {row['name']} | {row['mem_display']} |")
                
            return "\n".join(lines)
            
        except Exception as e:
            return f"Unable to list active processes: {str(e)}"

    @mcp.tool()
    async def get_network_connections() -> str:
        """
        Inspects active system network sockets and TCP/UDP ports.
        Use this when the user requests a scan of local open ports, listening services, or connection logs.
        """
        try:
            # netstat -ano provides Proto, Local IP:Port, Foreign IP:Port, Connection State, PID
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, check=True)
            
            # Process lines
            lines = result.stdout.split("\n")
            connections = []
            
            # Match pattern: Proto, Local Addr, Foreign Addr, State (optional), PID
            # States are typical for TCP, UDP doesn't have connection state
            for line in lines:
                parts = line.strip().split()
                if not parts or parts[0] == "Active" or parts[0] == "Proto":
                    continue
                
                # Check for TCP/UDP records
                proto = parts[0]
                if proto not in ("TCP", "UDP"):
                    continue
                    
                if len(parts) >= 4:
                    local_addr = parts[1]
                    foreign_addr = parts[2]
                    
                    if proto == "TCP":
                        state = parts[3]
                        pid = parts[4] if len(parts) > 4 else "N/A"
                    else:  # UDP
                        state = "N/A"
                        pid = parts[3] if len(parts) > 3 else "N/A"
                        
                    # Filter for active connections only (LISTENING, ESTABLISHED)
                    if state in ("LISTENING", "ESTABLISHED", "N/A"):
                        connections.append({
                            "proto": proto,
                            "local": local_addr,
                            "foreign": foreign_addr,
                            "state": state,
                            "pid": pid
                        })
                        
            if not connections:
                return "No active ports in LISTENING or ESTABLISHED states detected, sir."
                
            # Render connection table
            table = [
                "### Active System Connections (Sockets)",
                "",
                "| Proto | Local Address | Foreign Address | State | PID |",
                "| --- | --- | --- | --- | --- |"
            ]
            
            # Limit list to top 40 connections to keep formatting tidy
            for conn in connections[:40]:
                table.append(f"| {conn['proto']} | {conn['local']} | {conn['foreign']} | {conn['state']} | {conn['pid']} |")
                
            return "\n".join(table)
            
        except Exception as e:
            return f"Unable to fetch active sockets diagnostic: {str(e)}"
