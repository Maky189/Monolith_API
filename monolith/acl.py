import asyncio
from enum import Enum

from database import Role


class Access(str, Enum):
    none = "none"
    read = "read"
    write = "write"


def clean_path(path):
    parts = []
    for part in path.replace("\\", "/").split("/"):
        if part == "..":
            raise ValueError("path traversal not allowed")
        if part and part != ".":
            parts.append(part)
    return "/".join(parts)


def is_child_of(child_path, parent_path):
    if parent_path == "":
        return True
    return child_path == parent_path or child_path.startswith(parent_path + "/")


def access_for(rules, path):
    normalized = clean_path(path)
    longest_match = -1
    result = Access.none
    for prefix, access in rules:
        clean_prefix = clean_path(prefix)
        if is_child_of(normalized, clean_prefix) and len(clean_prefix) > longest_match:
            longest_match = len(clean_prefix)
            result = access
    return result


def has_visible_child(rules, folder_path):
    normalized = clean_path(folder_path)
    for prefix, access in rules:
        if access == Access.none:
            continue
        clean_prefix = clean_path(prefix)
        if is_child_of(clean_prefix, normalized) and clean_prefix != normalized:
            return True
    return False


def list_permitted_children(rules, folder_path, children):
    normalized_folder = clean_path(folder_path)
    result = []
    for name, is_dir in children:
        child_path = (normalized_folder + "/" + name) if normalized_folder else name
        access = access_for(rules, child_path)
        child_has_content = is_dir and has_visible_child(rules, child_path)
        if access != Access.none or child_has_content:
            result.append((name, is_dir, access, child_has_content))
    return result


def rules_for(user, assigned_game_folders):
    common_rules = [
        ("External", Access.read),
        ("Makefile", Access.write),
        ("Outland.slnx", Access.write),
        ("Outland.vcxproj", Access.write),
        ("Outland.vcxproj.filters", Access.write),
        ("code_convention.md", Access.read),
    ]

    if user.role == Role.admin:
        return [("", Access.write)]

    if user.role == Role.engine_backend_dev:
        return [("src/RHI", Access.write)] + common_rules

    if user.role == Role.engine_dev:
        return [
            ("src", Access.write),
            ("src/RHI", Access.none),
            ("src/RHI/README.md", Access.read),
            ("shaders", Access.write),
        ] + common_rules

    if user.role == Role.game_dev:
        game_rules = [
            ("assets", Access.write),
            ("maps", Access.write),
            ("games/README.md", Access.read),
        ]
        for folder in assigned_game_folders:
            game_rules.append(("games/" + folder, Access.write))
        return game_rules

    return []


class Connection:
    def __init__(self, websocket, user_id, rules):
        self.websocket = websocket
        self.user_id = user_id
        self.rules = rules


class WsHub:
    def __init__(self):
        self.connections = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket, user_id, rules):
        conn = Connection(websocket, user_id, rules)
        async with self.lock:
            self.connections.add(conn)
        return conn

    async def disconnect(self, conn):
        async with self.lock:
            self.connections.discard(conn)

    async def publish(self, path, sender_id, size, mtime):
        message = {"type": "file.changed", "path": path, "by": sender_id, "size": size, "mtime": mtime}
        async with self.lock:
            all_connections = list(self.connections)
        for conn in all_connections:
            if conn.user_id == sender_id:
                continue
            if access_for(conn.rules, path) == Access.none:
                continue
            try:
                await conn.websocket.send_json(message)
            except Exception:
                await self.disconnect(conn)


hub = WsHub()
