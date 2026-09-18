#!/usr/bin/env python3

"""
MIT License

Copyright (c) 2026 asc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import csv
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime, timedelta, timezone


# ============================================================
# pytypedstream
# ============================================================

try:
    from typedstream import unarchive_from_data
    from typedstream.archiving import TypedValue
    from typedstream.types.foundation import (
        NSString,
        NSMutableString,
    )
except ImportError:
    print("ERROR: pytypedstream is not installed.")
    print()
    print("Install it with:")
    print("pip install pytypedstream")
    print()
    sys.exit(1)


# ============================================================
# SETTINGS
# ============================================================

DB = Path.home() / "Library" / "Messages" / "chat.db"

MESSAGES_DIR = (
    Path.home()
    / "Library"
    / "Messages"
    / "Attachments"
)

OUTPUT_DIR = (
    Path.home()
    / "Desktop"
    / "Message Exports"
)

CONTACT_SEPARATOR = "\x1f"

APPLE_EPOCH = datetime(
    2001,
    1,
    1,
    tzinfo=timezone.utc,
)


# ============================================================
# DATE
# ============================================================

def apple_date(value):

    if value is None:
        return ""

    try:

        value = int(value)

        if value > 10**17:
            seconds = value / 1_000_000_000

        elif value > 10**14:
            seconds = value / 1_000_000

        elif value > 10**11:
            seconds = value / 1_000

        else:
            seconds = value

        dt = APPLE_EPOCH + timedelta(
            seconds=seconds
        )

        return dt.astimezone().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    except Exception:

        return ""


# ============================================================
# NORMALIZE ADDRESS
# ============================================================

def normalize_address(value):

    if not value:
        return ""

    value = str(value).strip().lower()

    if "@" in value:
        return value

    digits = re.sub(
        r"\D",
        "",
        value
    )

    if len(digits) >= 10:
        return digits[-10:]

    return digits


# ============================================================
# SAFE FILENAME
# ============================================================

def safe_filename(name):

    name = re.sub(
        r"[^A-Za-z0-9._ -]+",
        "_",
        str(name)
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    name = name.rstrip(".")

    if not name:
        name = "Unknown"

    return name[:150]


# ============================================================
# HUMAN SIZE
# ============================================================

def human_size(value):

    if value is None or value == "":
        return ""

    try:
        value = int(value)
    except Exception:
        return ""

    if value < 1024:
        return f"{value} B"

    if value < 1024**2:
        return f"{value / 1024:.1f} KB"

    if value < 1024**3:
        return f"{value / 1024**2:.1f} MB"

    if value < 1024**4:
        return f"{value / 1024**3:.2f} GB"

    return f"{value / 1024**4:.2f} TB"


# ============================================================
# CONTACTS
# ============================================================

def load_contacts():

    print("Checking Contacts...")

    script = r'''
tell application "Contacts"

    set outputText to ""

    repeat with p in people

        try
            set personName to name of p

            if personName is not missing value then

                repeat with ph in phones of p

                    try
                        set phoneValue to value of ph

                        if phoneValue is not missing value then
                            set outputText to outputText & personName & (ASCII character 31) & phoneValue & linefeed
                        end if

                    end try

                end repeat


                repeat with em in emails of p

                    try
                        set emailValue to value of em

                        if emailValue is not missing value then
                            set outputText to outputText & personName & (ASCII character 31) & emailValue & linefeed
                        end if

                    end try

                end repeat

            end if

        end try

    end repeat

    return outputText

end tell
'''

    try:

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:

            print(
                "Contacts lookup returned an error."
            )

            print(
                "Continuing without Contacts names."
            )

            return {}


        contacts = {}

        for line in result.stdout.splitlines():

            if CONTACT_SEPARATOR not in line:
                continue

            name, address = line.split(
                CONTACT_SEPARATOR,
                1
            )

            name = name.strip()
            address = address.strip()

            if not name or not address:
                continue

            key = normalize_address(
                address
            )

            if key:
                contacts[key] = name


        print(
            f"Contacts entries loaded: "
            f"{len(contacts):,}"
        )

        return contacts


    except subprocess.TimeoutExpired:

        print(
            "Contacts lookup timed out after "
            "30 seconds."
        )

        print(
            "Continuing without Contacts names."
        )

        return {}


    except Exception as e:

        print(
            f"Contacts lookup failed: {e}"
        )

        print(
            "Continuing without Contacts names."
        )

        return {}


# ============================================================
# ATTRIBUTED BODY
# ============================================================

def decode_attributed_body(blob):

    if not blob:
        return None

    if isinstance(blob, memoryview):
        blob = blob.tobytes()

    try:

        attributed = unarchive_from_data(
            blob
        )

        contents = getattr(
            attributed,
            "contents",
            None
        )

        if not contents:
            return None


        for item in contents:

            value = (
                item.value
                if isinstance(
                    item,
                    TypedValue
                )
                else item
            )

            if isinstance(
                value,
                (
                    NSString,
                    NSMutableString,
                )
            ):

                if value.value is not None:
                    return str(
                        value.value
                    )


        return None


    except Exception:

        return None


# ============================================================
# ATTACHMENT CLASSIFICATION
# ============================================================

INTERNAL_SUFFIXES = (
    ".pluginPayloadAttachment",
)


def classify_attachment(row):

    filename = str(
        row["filename"] or ""
    ).strip()

    transfer_name = str(
        row["transfer_name"] or ""
    ).strip()

    uti = str(
        row["uti"] or ""
    ).lower()

    lower_filename = filename.lower()


    # --------------------------------------------------------
    # Messages plugin payload.
    # --------------------------------------------------------

    for suffix in INTERNAL_SUFFIXES:

        if lower_filename.endswith(
            suffix.lower()
        ):

            return "internal"


    # --------------------------------------------------------
    # Other plugin-like UTIs.
    # --------------------------------------------------------

    if (
        "plugin" in uti
        or "messageplugin" in uti
    ):

        return "internal"


    # --------------------------------------------------------
    # Sticker payloads.
    # --------------------------------------------------------

    if (
        "sticker" in lower_filename
        or "sticker" in transfer_name.lower()
        or "sticker" in uti
    ):

        return "internal"


    if not filename:

        return "unknown"


    return "file"


# ============================================================
# ATTACHMENT PATH
# ============================================================

def attachment_path(filename):

    if not filename:
        return None

    filename = str(
        filename
    ).strip()

    if not filename:
        return None

    path = Path(
        os.path.expanduser(
            filename
        )
    )

    if path.is_absolute():
        return path

    return MESSAGES_DIR / path


# ============================================================
# UNIQUE DESTINATION
# ============================================================

def unique_path(path):

    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix

    counter = 2

    while True:

        candidate = path.with_name(
            f"{stem}_{counter}{suffix}"
        )

        if not candidate.exists():
            return candidate

        counter += 1


# ============================================================
# COPY ATTACHMENT
# ============================================================

def copy_attachment(
    attachment,
    message_date,
    attachments_dir
):

    classification = classify_attachment(
        attachment
    )


    filename = (
        attachment["transfer_name"]
        or attachment["filename"]
        or attachment["guid"]
        or "attachment"
    )

    filename = Path(
        str(filename)
    ).name


    # --------------------------------------------------------
    # Internal Messages artifact.
    # --------------------------------------------------------

    if classification == "internal":

        return {
            "status": "INTERNAL",
            "classification": "internal",
            "filename": filename,
            "source": str(
                attachment_path(
                    attachment["filename"]
                ) or ""
            ),
            "destination": "",
            "error": "",
        }


    # --------------------------------------------------------
    # No filename/path.
    # --------------------------------------------------------

    source = attachment_path(
        attachment["filename"]
    )

    if source is None:

        return {
            "status": "NO_PATH",
            "classification": classification,
            "filename": filename,
            "source": "",
            "destination": "",
            "error": (
                "attachment.filename is empty"
            ),
        }


    # --------------------------------------------------------
    # File isn't present locally.
    # --------------------------------------------------------

    if not source.exists():

        return {
            "status": "NOT_LOCAL",
            "classification": classification,
            "filename": filename,
            "source": str(source),
            "destination": "",
            "error": (
                "source file does not exist"
            ),
        }


    # --------------------------------------------------------
    # Exists but isn't a normal file.
    # --------------------------------------------------------

    if not source.is_file():

        return {
            "status": "NOT_A_FILE",
            "classification": classification,
            "filename": filename,
            "source": str(source),
            "destination": "",
            "error": (
                "source path exists but is not "
                "a regular file"
            ),
        }


    # --------------------------------------------------------
    # Create Attachments directory only when we're actually
    # copying a real file.
    # --------------------------------------------------------

    attachments_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    timestamp = (
        message_date
        .replace(" ", "_")
        .replace(":", "-")
    )


    destination_name = (
        f"{timestamp}_"
        f"{safe_filename(filename)}"
    )


    destination = unique_path(
        attachments_dir
        / destination_name
    )


    # --------------------------------------------------------
    # Copy.
    # --------------------------------------------------------

    try:

        shutil.copy2(
            source,
            destination
        )

        return {
            "status": "COPIED",
            "classification": classification,
            "filename": filename,
            "source": str(source),
            "destination": str(destination),
            "error": "",
        }


    except PermissionError as e:

        return {
            "status": "PERMISSION_DENIED",
            "classification": classification,
            "filename": filename,
            "source": str(source),
            "destination": "",
            "error": str(e),
        }


    except OSError as e:

        return {
            "status": "OS_ERROR",
            "classification": classification,
            "filename": filename,
            "source": str(source),
            "destination": "",
            "error": str(e),
        }


    except Exception as e:

        return {
            "status": "COPY_ERROR",
            "classification": classification,
            "filename": filename,
            "source": str(source),
            "destination": "",
            "error": str(e),
        }


# ============================================================
# DATABASE
# ============================================================

if not DB.exists():

    print("Messages database not found:")
    print(DB)

    sys.exit(1)


# ============================================================
# COMMAND LINE
# ============================================================

all_mode = (
    len(sys.argv) > 1
    and sys.argv[1].lower() == "--all"
)


if all_mode:

    search_term = None

else:

    if len(sys.argv) > 1:

        search_term = " ".join(
            sys.argv[1:]
        ).strip()

    else:

        search_term = input(
            "Contact name / phone / email: "
        ).strip()

    if not search_term:

        print("Nothing entered.")
        sys.exit(1)


# ============================================================
# CONTACTS
# ============================================================

contacts = load_contacts()

print()


# ============================================================
# OPEN DATABASE
# ============================================================

print(
    "Opening Messages database..."
)

conn = sqlite3.connect(
    f"file:{DB}?mode=ro",
    uri=True
)

conn.row_factory = sqlite3.Row


# ============================================================
# HANDLES
# ============================================================

handles = conn.execute("""
    SELECT
        ROWID AS handle_id,
        id,
        service
    FROM handle
    WHERE id IS NOT NULL
""").fetchall()


handle_names = {}

for handle in handles:

    name = contacts.get(
        normalize_address(
            handle["id"]
        )
    )

    if name:

        handle_names[
            handle["handle_id"]
        ] = name


# ============================================================
# CHATS
# ============================================================

chats = conn.execute("""
    SELECT
        ROWID AS chat_id,
        chat_identifier,
        display_name,
        room_name,
        group_id
    FROM chat
    ORDER BY ROWID
""").fetchall()


# ============================================================
# SELECT CHATS
# ============================================================

if all_mode:

    selected_chats = chats

else:

    selected_chats = []

    contact_keys = set()


    # --------------------------------------------------------
    # Contact name search.
    # --------------------------------------------------------

    for key, name in contacts.items():

        if (
            search_term.lower()
            in name.lower()
        ):

            contact_keys.add(key)


    # Direct phone/email.
    search_key = normalize_address(
        search_term
    )

    if search_key:
        contact_keys.add(search_key)


    # --------------------------------------------------------
    # Find handles.
    # --------------------------------------------------------

    matching_handle_ids = set()

    for handle in handles:

        if (
            normalize_address(
                handle["id"]
            )
            in contact_keys
        ):

            matching_handle_ids.add(
                handle["handle_id"]
            )


    # --------------------------------------------------------
    # Fallback partial handle.
    # --------------------------------------------------------

    if not matching_handle_ids:

        needle = search_term.lower()

        for handle in handles:

            if needle in (
                handle["id"] or ""
            ).lower():

                matching_handle_ids.add(
                    handle["handle_id"]
                )


    # --------------------------------------------------------
    # Find chats through handles.
    # --------------------------------------------------------

    if matching_handle_ids:

        placeholders = ",".join(
            "?"
            for _ in matching_handle_ids
        )

        rows = conn.execute(
            f"""
            SELECT DISTINCT chat_id
            FROM chat_handle_join
            WHERE handle_id IN ({placeholders})
            """,
            tuple(matching_handle_ids)
        ).fetchall()


        selected_ids = {
            row["chat_id"]
            for row in rows
        }


        selected_chats = [
            chat
            for chat in chats
            if chat["chat_id"]
            in selected_ids
        ]


    # --------------------------------------------------------
    # Fallback chat name / identifier.
    # --------------------------------------------------------

    if not selected_chats:

        needle = search_term.lower()

        selected_chats = [
            chat
            for chat in chats

            if needle in (
                chat["display_name"]
                or ""
            ).lower()

            or needle in (
                chat["chat_identifier"]
                or ""
            ).lower()
        ]


    if not selected_chats:

        print(
            f"No conversation found for "
            f"'{search_term}'."
        )

        conn.close()
        sys.exit(1)


# ============================================================
# OUTPUT ROOT
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MANIFEST
# ============================================================

manifest_path = (
    OUTPUT_DIR
    / "attachments_manifest.csv"
)

manifest_file = open(
    manifest_path,
    "w",
    newline="",
    encoding="utf-8"
)

manifest = csv.writer(
    manifest_file
)

manifest.writerow([
    "conversation",
    "message_date",
    "sender",
    "message",
    "attachment_filename",
    "mime_type",
    "uti",
    "size_bytes",
    "size",
    "classification",
    "status",
    "source_path",
    "exported_path",
])


# ============================================================
# ERROR MANIFEST
# ============================================================

error_manifest_path = (
    OUTPUT_DIR
    / "attachment_errors.csv"
)

error_file = open(
    error_manifest_path,
    "w",
    newline="",
    encoding="utf-8"
)

error_manifest = csv.writer(
    error_file
)

error_manifest.writerow([
    "conversation",
    "message_date",
    "sender",
    "message",
    "attachment_filename",
    "mime_type",
    "uti",
    "size_bytes",
    "classification",
    "status",
    "source_path",
    "error",
])


# ============================================================
# STATUS COUNTER
# ============================================================

attachment_statuses = Counter()


# ============================================================
# EXPORT ONE CHAT
# ============================================================

def export_chat(chat):

    chat_id = chat["chat_id"]


    # --------------------------------------------------------
    # PARTICIPANTS
    # --------------------------------------------------------

    participant_rows = conn.execute(
        """
        SELECT
            h.ROWID AS handle_id,
            h.id,
            h.service
        FROM chat_handle_join chj
        JOIN handle h
            ON h.ROWID = chj.handle_id
        WHERE chj.chat_id = ?
        ORDER BY h.id
        """,
        (chat_id,)
    ).fetchall()


    participants = []

    for participant in participant_rows:

        name = handle_names.get(
            participant["handle_id"]
        )

        participants.append({
            "handle_id": participant[
                "handle_id"
            ],
            "address": participant["id"],
            "name": (
                name
                or participant["id"]
            ),
        })


    # --------------------------------------------------------
    # CONVERSATION NAME
    # --------------------------------------------------------

    if chat["display_name"]:

        conversation_name = (
            chat["display_name"]
        )

    elif len(participants) == 1:

        conversation_name = (
            participants[0]["name"]
        )

    elif participants:

        conversation_name = ", ".join(
            p["name"]
            for p in participants
        )

    elif chat["chat_identifier"]:

        conversation_name = (
            chat["chat_identifier"]
        )

    else:

        conversation_name = (
            f"Chat_{chat_id}"
        )


    conversation_dir = (
        OUTPUT_DIR
        / safe_filename(
            conversation_name
        )
    )

    attachments_dir = (
        conversation_dir
        / "Attachments"
    )


    # --------------------------------------------------------
    # MESSAGES
    # --------------------------------------------------------

    rows = conn.execute(
        """
        SELECT
            m.ROWID AS message_id,
            m.text,
            m.attributedBody,
            m.date,
            m.is_from_me,
            m.handle_id,
            h.id AS sender_address
        FROM message m

        JOIN chat_message_join cmj
            ON cmj.message_id = m.ROWID

        LEFT JOIN handle h
            ON h.ROWID = m.handle_id

        WHERE cmj.chat_id = ?

        ORDER BY
            m.date ASC,
            m.ROWID ASC
        """,
        (chat_id,)
    ).fetchall()


    transcript = []

    messages_exported = 0

    attachments_found = 0
    attachments_copied = 0
    attachments_missing = 0
    attachments_internal = 0

    attributed_decoded = 0


    # --------------------------------------------------------
    # PROCESS MESSAGES
    # --------------------------------------------------------

    for row in rows:

        # ----------------------------------------------------
        # MESSAGE TEXT
        # ----------------------------------------------------

        text = row["text"]


        if text:

            text = str(text)


        elif row["attributedBody"]:

            text = decode_attributed_body(
                row["attributedBody"]
            )

            if text:
                attributed_decoded += 1


        else:

            text = None


        if text:

            text = re.sub(
                r"\s*\r?\n\s*",
                " ",
                str(text)
            )

            text = re.sub(
                r"\s+",
                " ",
                text
            ).strip()


        # ----------------------------------------------------
        # SENDER
        # ----------------------------------------------------

        if row["is_from_me"]:

            sender = "Me"

        else:

            sender = None

            if row["handle_id"]:

                sender = handle_names.get(
                    row["handle_id"]
                )

            if not sender:

                sender = (
                    row["sender_address"]
                    or conversation_name
                )


        date_string = apple_date(
            row["date"]
        )


        # ----------------------------------------------------
        # ATTACHMENTS
        # ----------------------------------------------------

        attachments = conn.execute(
            """
            SELECT
                a.ROWID AS attachment_id,
                a.guid,
                a.filename,
                a.uti,
                a.mime_type,
                a.total_bytes,
                a.transfer_name,
                a.is_outgoing,
                a.is_sticker
            FROM message_attachment_join maj
            JOIN attachment a
                ON a.ROWID = maj.attachment_id
            WHERE maj.message_id = ?
            ORDER BY a.ROWID ASC
            """,
            (row["message_id"],)
        ).fetchall()


        # ----------------------------------------------------
        # Skip completely empty records.
        # ----------------------------------------------------

        if not text and not attachments:
            continue


        # ----------------------------------------------------
        # MESSAGE LINE
        # ----------------------------------------------------

        if text:

            transcript.append(
                f"{sender} | "
                f"{date_string} | "
                f"{text}\n"
            )

        else:

            transcript.append(
                f"{sender} | "
                f"{date_string} | "
                f"[Attachment]\n"
            )


        messages_exported += 1


        # ----------------------------------------------------
        # PROCESS ATTACHMENTS
        # ----------------------------------------------------

        for attachment in attachments:

            attachments_found += 1


            result = copy_attachment(
                attachment,
                date_string,
                attachments_dir
            )


            status = result[
                "status"
            ]

            attachment_statuses[
                status
            ] += 1


            if status == "COPIED":

                attachments_copied += 1

            elif status == "NOT_LOCAL":

                attachments_missing += 1

            elif status == "INTERNAL":

                attachments_internal += 1


            filename = result[
                "filename"
            ]

            mime_type = (
                attachment["mime_type"]
                or ""
            )

            size_bytes = (
                attachment["total_bytes"]
                or ""
            )

            size = human_size(
                size_bytes
            )


            # ------------------------------------------------
            # Transcript.
            # ------------------------------------------------

            if status == "COPIED":

                transcript.append(
                    f"    [Attachment: "
                    f"{filename} | "
                    f"{mime_type} | "
                    f"{size} | copied]\n"
                )

            elif status == "INTERNAL":

                transcript.append(
                    f"    [Messages internal "
                    f"attachment: "
                    f"{filename}]\n"
                )

            elif status == "NOT_LOCAL":

                transcript.append(
                    f"    [Attachment: "
                    f"{filename} | "
                    f"{mime_type} | "
                    f"{size} | "
                    f"NOT LOCAL]\n"
                )

            else:

                transcript.append(
                    f"    [Attachment: "
                    f"{filename} | "
                    f"{mime_type} | "
                    f"{size} | "
                    f"{status}]\n"
                )


            # ------------------------------------------------
            # Main manifest.
            # ------------------------------------------------

            manifest.writerow([
                conversation_name,
                date_string,
                sender,
                text or "",
                filename,
                mime_type,
                attachment["uti"] or "",
                size_bytes,
                size,
                result["classification"],
                status,
                result["source"],
                result["destination"],
            ])


            # ------------------------------------------------
            # Error manifest.
            #
            # Only actual problems are written here.
            # Internal payloads are intentionally excluded
            # because they are not errors.
            # ------------------------------------------------

            if status not in (
                "COPIED",
                "INTERNAL",
            ):

                error_manifest.writerow([
                    conversation_name,
                    date_string,
                    sender,
                    text or "",
                    filename,
                    mime_type,
                    attachment["uti"] or "",
                    size_bytes,
                    result["classification"],
                    status,
                    result["source"],
                    result["error"],
                ])


        transcript.append("\n")


    # --------------------------------------------------------
    # Nothing useful in this conversation.
    # --------------------------------------------------------

    if not transcript:

        return {
            "name": conversation_name,
            "path": None,
            "messages": 0,
            "records": len(rows),
            "attachments": 0,
            "copied": 0,
            "missing": 0,
            "internal": 0,
            "attributed": attributed_decoded,
        }


    # --------------------------------------------------------
    # Create conversation directory now, not before.
    # --------------------------------------------------------

    conversation_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    transcript_path = (
        conversation_dir
        / (
            safe_filename(
                conversation_name
            )
            + "_messages.txt"
        )
    )


    with open(
        transcript_path,
        "w",
        encoding="utf-8"
    ) as output:

        output.write(
            f"Conversation with "
            f"{conversation_name}\n"
        )

        output.write(
            "=" * 80
            + "\n\n"
        )

        output.writelines(
            transcript
        )


    return {
        "name": conversation_name,
        "path": transcript_path,
        "messages": messages_exported,
        "records": len(rows),
        "attachments": attachments_found,
        "copied": attachments_copied,
        "missing": attachments_missing,
        "internal": attachments_internal,
        "attributed": attributed_decoded,
    }


# ============================================================
# EXPORT
# ============================================================

print(
    f"Conversations to export: "
    f"{len(selected_chats):,}"
)

print()


results = []

for index, chat in enumerate(
    selected_chats,
    start=1
):

    try:

        result = export_chat(
            chat
        )

        results.append(
            result
        )

        print(
            f"[{index}/{len(selected_chats)}] "
            f"{result['name']}: "
            f"{result['messages']:,} messages, "
            f"{result['attachments']:,} attachments, "
            f"{result['copied']:,} copied"
        )

    except Exception as e:

        print(
            f"[{index}/{len(selected_chats)}] "
            f"ERROR: "
            f"{chat['display_name'] or chat['chat_identifier']}"
        )

        print(
            f"    {e}"
        )


# ============================================================
# CLOSE MANIFESTS
# ============================================================

manifest_file.close()
error_file.close()


# ============================================================
# MASTER TRANSCRIPT
# ============================================================

master_path = (
    OUTPUT_DIR
    / "All_Messages.txt"
)


results.sort(
    key=lambda result:
    result["name"].lower()
)


with open(
    master_path,
    "w",
    encoding="utf-8"
) as master:

    master.write(
        "All Messages\n"
    )

    master.write(
        "=" * 80
        + "\n\n"
    )


    for result in results:

        if not result["path"]:
            continue


        master.write(
            "\n"
            + "#" * 80
            + "\n"
        )

        master.write(
            f"# {result['name']}\n"
        )

        master.write(
            "#" * 80
            + "\n\n"
        )


        try:

            with open(
                result["path"],
                "r",
                encoding="utf-8"
            ) as individual:

                content = individual.read()

                separator = (
                    "=" * 80
                )

                if separator in content:

                    content = content.split(
                        separator,
                        1
                    )[1].lstrip()

                master.write(
                    content
                )

        except Exception:

            master.write(
                "[Unable to read individual export]\n"
            )


        master.write("\n")


# ============================================================
# CLOSE DATABASE
# ============================================================

conn.close()


# ============================================================
# SUMMARY
# ============================================================

exported_conversations = sum(
    1
    for result in results
    if result["path"]
)

total_messages = sum(
    result["messages"]
    for result in results
)

total_records = sum(
    result["records"]
    for result in results
)

total_attachments = sum(
    result["attachments"]
    for result in results
)

total_copied = sum(
    result["copied"]
    for result in results
)

total_missing = sum(
    result["missing"]
    for result in results
)

total_internal = sum(
    result["internal"]
    for result in results
)

total_attributed = sum(
    result["attributed"]
    for result in results
)


print()
print("=" * 80)
print("EXPORT COMPLETE")
print("=" * 80)
print()

print(
    f"Conversations exported: "
    f"{exported_conversations:,}"
)

print(
    f"Database records:        "
    f"{total_records:,}"
)

print(
    f"Messages exported:       "
    f"{total_messages:,}"
)

print(
    f"Attachments found:       "
    f"{total_attachments:,}"
)

print(
    f"Attachments copied:      "
    f"{total_copied:,}"
)

print(
    f"Attachments NOT local:   "
    f"{total_missing:,}"
)

print(
    f"Internal Messages files: "
    f"{total_internal:,}"
)

print(
    f"attributedBody decoded:  "
    f"{total_attributed:,}"
)

print()
print("Attachment status breakdown:")
print()

for status, count in sorted(
    attachment_statuses.items(),
    key=lambda item: (-item[1], item[0])
):

    print(
        f"  {status:<22} {count:,}"
    )

print()
print("Export folder:")
print(
    f"  {OUTPUT_DIR}"
)

print()
print("Master transcript:")
print(
    f"  {master_path}"
)

print()
print("Attachment manifest:")
print(
    f"  {manifest_path}"
)

print()
print("Attachment errors:")
print(
    f"  {error_manifest_path}"
)

print()

