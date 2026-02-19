#!/usr/bin/env python3
"""Export archived messages to a beautiful HTML file."""

import argparse
import asyncio
import html
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg

from src.config import settings


async def get_groups(conn: asyncpg.Connection) -> list[dict]:
    """Get all groups with archived messages."""
    rows = await conn.fetch("""
        SELECT DISTINCT g.id, g.title, COUNT(m.id) as message_count,
               MIN(m.message_date) as first_message,
               MAX(m.message_date) as last_message
        FROM archived_messages m
        LEFT JOIN groups g ON g.id = m.group_id
        GROUP BY g.id, g.title
        ORDER BY last_message DESC
    """)
    return [dict(r) for r in rows]


async def get_messages(conn: asyncpg.Connection, group_id: int | None = None) -> list[dict]:
    """Get archived messages, optionally filtered by group."""
    query = """
        SELECT m.*, g.title as group_title
        FROM archived_messages m
        LEFT JOIN groups g ON g.id = m.group_id
    """
    if group_id:
        query += " WHERE m.group_id = $1"
        query += " ORDER BY m.message_date ASC"
        rows = await conn.fetch(query, group_id)
    else:
        query += " ORDER BY m.group_id, m.message_date ASC"
        rows = await conn.fetch(query)

    return [dict(r) for r in rows]


def escape_html(text: str | None) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return html.escape(text).replace("\n", "<br>")


def format_datetime(dt: datetime | None) -> str:
    """Format datetime for display."""
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_user_display_name(msg: dict) -> str:
    """Get display name for message sender."""
    parts = []
    if msg.get("first_name"):
        parts.append(msg["first_name"])
    if msg.get("last_name"):
        parts.append(msg["last_name"])

    name = " ".join(parts) if parts else "Unknown"

    if msg.get("username"):
        name += f" (@{msg['username']})"

    return name


def render_media(msg: dict, media_folder: str) -> str:
    """Render media content as HTML."""
    if not msg.get("media_type"):
        return ""

    media_type = msg["media_type"]
    file_path = msg.get("media_file_path")
    file_name = msg.get("media_file_name") or f"{media_type} file"

    if not file_path:
        return f'<div class="media-placeholder">[{media_type}: file not downloaded]</div>'

    # Use relative path: media_folder/filename
    original_path = Path(file_path)
    rel_path = f"{media_folder}/{original_path.name}"

    if media_type == "photo":
        return f'<div class="media"><img src="{rel_path}" alt="Photo" loading="lazy" onclick="openModal(this.src)"></div>'
    elif media_type in ("video", "animation"):
        return f'<div class="media"><video src="{rel_path}" controls preload="metadata"></video></div>'
    elif media_type in ("audio", "voice"):
        return f'<div class="media"><audio src="{rel_path}" controls></audio></div>'
    elif media_type == "sticker":
        return f'<div class="media sticker"><img src="{rel_path}" alt="Sticker" loading="lazy"></div>'
    else:
        return f'<div class="media"><a href="{rel_path}" target="_blank">📎 {escape_html(file_name)}</a></div>'


def generate_html(groups: list[dict], messages: list[dict], media_base_path: str) -> str:
    """Generate the complete HTML document."""

    # Group messages by group_id for easier rendering
    messages_by_group: dict[int, list[dict]] = {}
    for msg in messages:
        gid = msg["group_id"]
        if gid not in messages_by_group:
            messages_by_group[gid] = []
        messages_by_group[gid].append(msg)

    # Generate group list HTML
    groups_html = ""
    for g in groups:
        gid = g["id"]
        title = escape_html(g["title"] or f"Group {gid}")
        count = g["message_count"]
        groups_html += f'''
        <div class="group-item" data-group-id="{gid}" onclick="filterGroup({gid})">
            <div class="group-title">{title}</div>
            <div class="group-meta">{count} messages</div>
        </div>
        '''

    # Generate messages HTML
    messages_html = ""
    current_date = None

    for gid, group_messages in messages_by_group.items():
        group_title = next((g["title"] for g in groups if g["id"] == gid), f"Group {gid}")

        messages_html += f'<div class="message-group" data-group-id="{gid}">'
        messages_html += f'<h2 class="group-header">{escape_html(group_title)}</h2>'

        for msg in group_messages:
            msg_date = msg["message_date"].date() if msg["message_date"] else None

            # Add date separator
            if msg_date != current_date:
                current_date = msg_date
                date_str = msg_date.strftime("%B %d, %Y") if msg_date else "Unknown date"
                messages_html += f'<div class="date-separator">{date_str}</div>'

            user_name = get_user_display_name(msg)
            time_str = msg["message_date"].strftime("%H:%M") if msg["message_date"] else ""

            text_content = escape_html(msg.get("text") or msg.get("caption") or "")
            media_content = render_media(msg, media_base_path)

            # Reply indicator
            reply_html = ""
            if msg.get("reply_to_message_id"):
                reply_html = f'<div class="reply-indicator">↩ Reply to message #{msg["reply_to_message_id"]}</div>'

            # Forward indicator
            forward_html = ""
            if msg.get("forward_from_user_id") or msg.get("forward_from_chat_id"):
                forward_html = '<div class="forward-indicator">↪ Forwarded message</div>'

            messages_html += f'''
            <div class="message" data-message-id="{msg['message_id']}" data-user-id="{msg.get('user_id', '')}">
                <div class="message-header">
                    <span class="user-name">{escape_html(user_name)}</span>
                    <span class="message-time">{time_str}</span>
                </div>
                {reply_html}
                {forward_html}
                {media_content}
                <div class="message-text">{text_content}</div>
            </div>
            '''

        messages_html += '</div>'
        current_date = None  # Reset for next group

    # Complete HTML template
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Archive</title>
    <style>
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f5f5f5;
            --bg-message: #e3f2fd;
            --text-primary: #212121;
            --text-secondary: #757575;
            --border-color: #e0e0e0;
            --accent-color: #1976d2;
            --sidebar-width: 280px;
        }

        [data-theme="dark"] {
            --bg-primary: #1a1a1a;
            --bg-secondary: #2d2d2d;
            --bg-message: #2d3748;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --border-color: #404040;
            --accent-color: #64b5f6;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.5;
        }

        .container {
            display: flex;
            height: 100vh;
        }

        /* Sidebar */
        .sidebar {
            width: var(--sidebar-width);
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }

        .sidebar-header {
            padding: 16px;
            border-bottom: 1px solid var(--border-color);
        }

        .sidebar-header h1 {
            font-size: 18px;
            margin-bottom: 12px;
        }

        .search-box {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 20px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 14px;
        }

        .controls {
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }

        .btn {
            padding: 6px 12px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--bg-primary);
            color: var(--text-primary);
            cursor: pointer;
            font-size: 12px;
        }

        .btn:hover { background: var(--bg-message); }
        .btn.active { background: var(--accent-color); color: white; border-color: var(--accent-color); }

        .group-list {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }

        .group-item {
            padding: 12px;
            border-radius: 8px;
            cursor: pointer;
            margin-bottom: 4px;
        }

        .group-item:hover { background: var(--bg-message); }
        .group-item.active { background: var(--accent-color); color: white; }

        .group-title { font-weight: 500; }
        .group-meta { font-size: 12px; color: var(--text-secondary); }
        .group-item.active .group-meta { color: rgba(255,255,255,0.8); }

        /* Main content */
        .main-content {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }

        .message-group { margin-bottom: 32px; }
        .message-group.hidden { display: none; }

        .group-header {
            font-size: 20px;
            padding: 16px 0;
            border-bottom: 2px solid var(--accent-color);
            margin-bottom: 16px;
            position: sticky;
            top: 0;
            background: var(--bg-primary);
            z-index: 10;
        }

        .date-separator {
            text-align: center;
            color: var(--text-secondary);
            font-size: 13px;
            margin: 20px 0;
            position: relative;
        }

        .date-separator::before,
        .date-separator::after {
            content: '';
            position: absolute;
            top: 50%;
            width: 30%;
            height: 1px;
            background: var(--border-color);
        }

        .date-separator::before { left: 0; }
        .date-separator::after { right: 0; }

        .message {
            background: var(--bg-message);
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 8px;
            max-width: 80%;
        }

        .message.hidden { display: none; }

        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }

        .user-name {
            font-weight: 600;
            color: var(--accent-color);
        }

        .message-time {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .reply-indicator, .forward-indicator {
            font-size: 12px;
            color: var(--text-secondary);
            font-style: italic;
            margin-bottom: 4px;
        }

        .message-text { word-wrap: break-word; }

        .media { margin: 8px 0; }
        .media img { max-width: 400px; max-height: 300px; border-radius: 8px; cursor: pointer; }
        .media video { max-width: 400px; border-radius: 8px; }
        .media audio { width: 100%; max-width: 300px; }
        .media.sticker img { max-width: 150px; }
        .media a { color: var(--accent-color); }
        .media-placeholder { color: var(--text-secondary); font-style: italic; }

        /* Modal for images */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }

        .modal.active { display: flex; }
        .modal img { max-width: 95%; max-height: 95%; object-fit: contain; }
        .modal-close {
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 40px;
            color: white;
            cursor: pointer;
        }

        /* Stats */
        .stats {
            padding: 12px;
            font-size: 12px;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="sidebar-header">
                <h1>📨 Telegram Archive</h1>
                <input type="text" class="search-box" placeholder="Search messages..." oninput="searchMessages(this.value)">
                <div class="controls">
                    <button class="btn" onclick="showAllGroups()">All Groups</button>
                    <button class="btn" id="themeToggle" onclick="toggleTheme()">🌙</button>
                </div>
            </div>
            <div class="group-list">
                ''' + groups_html + '''
            </div>
            <div class="stats">
                ''' + f'{len(groups)} groups, {len(messages)} messages' + '''
            </div>
        </div>
        <div class="main-content">
            ''' + messages_html + '''
        </div>
    </div>

    <div class="modal" id="imageModal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img id="modalImage" src="" alt="">
    </div>

    <script>
        let currentGroupId = null;

        function filterGroup(groupId) {
            currentGroupId = groupId;

            // Update sidebar
            document.querySelectorAll('.group-item').forEach(el => {
                el.classList.toggle('active', el.dataset.groupId == groupId);
            });

            // Show/hide message groups
            document.querySelectorAll('.message-group').forEach(el => {
                el.classList.toggle('hidden', el.dataset.groupId != groupId);
            });
        }

        function showAllGroups() {
            currentGroupId = null;
            document.querySelectorAll('.group-item').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.message-group').forEach(el => el.classList.remove('hidden'));
        }

        function searchMessages(query) {
            const q = query.toLowerCase();
            document.querySelectorAll('.message').forEach(el => {
                const text = el.textContent.toLowerCase();
                const matches = !q || text.includes(q);
                el.classList.toggle('hidden', !matches);
            });
        }

        function toggleTheme() {
            const html = document.documentElement;
            const isDark = html.dataset.theme === 'dark';
            html.dataset.theme = isDark ? '' : 'dark';
            document.getElementById('themeToggle').textContent = isDark ? '🌙' : '☀️';
            localStorage.setItem('theme', html.dataset.theme);
        }

        function openModal(src) {
            document.getElementById('modalImage').src = src;
            document.getElementById('imageModal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('imageModal').classList.remove('active');
        }

        // Load saved theme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.dataset.theme = savedTheme;
            document.getElementById('themeToggle').textContent = savedTheme === 'dark' ? '☀️' : '🌙';
        }

        // Escape key closes modal
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeModal();
        });
    </script>
</body>
</html>'''

    return html_template


def copy_media_files(messages: list[dict], dest_folder: Path) -> int:
    """Copy media files to destination folder. Returns count of copied files."""
    dest_folder.mkdir(parents=True, exist_ok=True)
    copied = 0

    for msg in messages:
        if not msg.get("media_file_path"):
            continue

        # Path in DB is relative like "archive/media/group_id/file.jpg"
        # In container it's at "/app/archive/media/group_id/file.jpg"
        db_path = msg["media_file_path"]

        # Try multiple possible locations
        candidates = [
            Path(db_path),  # As stored
            Path("/app") / db_path,  # With /app prefix
            Path("/app/archive/media") / Path(db_path).name,  # Just filename in media dir
        ]

        # Also check with group subfolder
        parts = Path(db_path).parts
        if len(parts) >= 2:
            # Extract group_id folder and filename
            group_folder = parts[-2] if len(parts) >= 2 else ""
            filename = parts[-1]
            candidates.append(Path("/app/archive/media") / group_folder / filename)

        src_path = None
        for candidate in candidates:
            if candidate.exists():
                src_path = candidate
                break

        if src_path and src_path.exists():
            dest_path = dest_folder / src_path.name
            if not dest_path.exists():
                shutil.copy2(src_path, dest_path)
                copied += 1

    return copied


async def main():
    parser = argparse.ArgumentParser(description="Export archived messages to HTML")
    parser.add_argument("-o", "--output", default="archive.html", help="Output HTML file path")
    parser.add_argument("-g", "--group", type=int, help="Filter by group ID")
    parser.add_argument("--no-media", action="store_true", help="Don't copy media files")
    args = parser.parse_args()

    print("Connecting to database...")
    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )

    try:
        print("Fetching groups...")
        groups = await get_groups(conn)
        print(f"Found {len(groups)} groups with archived messages")

        print("Fetching messages...")
        messages = await get_messages(conn, args.group)
        print(f"Found {len(messages)} messages")

        if not messages:
            print("No messages to export.")
            return

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        media_folder_name = output_path.stem + "_media"
        media_folder_path = output_path.parent / media_folder_name

        # Copy media files
        if not args.no_media:
            print("Copying media files...")
            copied = copy_media_files(messages, media_folder_path)
            print(f"Copied {copied} media files to {media_folder_path}")

        print("Generating HTML...")
        html_content = generate_html(groups, messages, media_folder_name)

        output_path.write_text(html_content, encoding="utf-8")
        print(f"✓ Exported to {output_path.absolute()}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
