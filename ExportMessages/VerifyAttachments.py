#!/usr/bin/env python3

import csv
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime, timedelta, timezone


# ============================================================
# SETTINGS
# ============================================================

DB = (
    Path.home()
    / "Library"
    / "Messages"
    / "chat.db"
)

OUTPUT_DIR = (
    Path.home()
    / "Desktop"
    / "Message Exports"
)

REPORT_FILE = (
    OUTPUT_DIR
    / "attachment_verify.txt"
)

CSV_FILE = (
    OUTPUT_DIR
    / "attachment_verify.csv"
)

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
# SAFE VALUE
# ============================================================

def get_value(row, key):

    try:
        value = row[key]

    except (KeyError, IndexError):

        return ""

    if value is None:

        return ""

    return str(value)


# ============================================================
# DATABASE
# ============================================================

if not DB.exists():

    print()
    print("Messages database not found:")
    print(DB)
    print()

    sys.exit(1)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


print()
print("Opening Messages database...")
print(DB)
print()


try:

    conn = sqlite3.connect(
        f"file:{DB}?mode=ro",
        uri=True
    )

except Exception as e:

    print("Could not open database:")
    print(e)
    print()

    sys.exit(1)


conn.row_factory = sqlite3.Row


# ============================================================
# DISCOVER ATTACHMENT SCHEMA
# ============================================================

print("Inspecting attachment table schema...")
print()


attachment_columns = {
    row["name"]
    for row in conn.execute(
        "PRAGMA table_info(attachment)"
    ).fetchall()
}


print(
    f"Attachment table columns found: "
    f"{len(attachment_columns)}"
)

print()


# These are optional columns that have existed on various
# macOS versions. We only select them when they actually exist.

optional_attachment_columns = [
    "guid",
    "filename",
    "transfer_name",
    "uti",
    "mime_type",
    "total_bytes",
    "is_sticker",
    "is_outgoing",
    "created_date",
    "start_date",
    "user_info",
    "hide_attachment",
    "ck_sync_state",
    "encryption_key",
    "is_compressed",
    "is_expirable",
    "expire_state",
    "is_auto_downloaded",
    "is_missing",
    "is_transparent",
    "original_rowid",
]


# ============================================================
# BUILD SAFE SELECT
# ============================================================

attachment_select = [
    "a.ROWID AS attachment_rowid"
]


for column in optional_attachment_columns:

    if column in attachment_columns:

        attachment_select.append(
            f"a.{column}"
        )


# ============================================================
# MESSAGE COLUMNS
# ============================================================

message_columns = {
    row["name"]
    for row in conn.execute(
        "PRAGMA table_info(message)"
    ).fetchall()
}


message_select = [
    "m.ROWID AS message_rowid"
]


for column in (
    "date",
    "text",
    "is_from_me",
):

    if column in message_columns:

        message_select.append(
            f"m.{column} AS message_{column}"
        )


# ============================================================
# HANDLE COLUMNS
# ============================================================

handle_columns = {
    row["name"]
    for row in conn.execute(
        "PRAGMA table_info(handle)"
    ).fetchall()
}


handle_select = []

if "id" in handle_columns:

    handle_select.append(
        "h.id AS sender_address"
    )

if "service" in handle_columns:

    handle_select.append(
        "h.service AS sender_service"
    )


# ============================================================
# CHAT COLUMNS
# ============================================================

chat_columns = {
    row["name"]
    for row in conn.execute(
        "PRAGMA table_info(chat)"
    ).fetchall()
}


chat_select = [
    "c.ROWID AS chat_rowid"
]


for column in (
    "chat_identifier",
    "display_name",
    "room_name",
):

    if column in chat_columns:

        chat_select.append(
            f"c.{column}"
        )


# ============================================================
# SHOW MISSING OPTIONAL COLUMNS
# ============================================================

important_columns = [
    "guid",
    "filename",
    "transfer_name",
    "uti",
    "mime_type",
    "total_bytes",
    "is_sticker",
    "is_outgoing",
    "created_date",
    "start_date",
    "user_info",
    "hide_attachment",
    "ck_sync_state",
]


missing_columns = [
    column
    for column in important_columns
    if column not in attachment_columns
]


if missing_columns:

    print(
        "Optional attachment columns not present:"
    )

    for column in missing_columns:

        print(
            f"  - {column}"
        )

    print()


# ============================================================
# BUILD QUERY
# ============================================================

select_clause = ",\n        ".join(
    attachment_select
    + message_select
    + handle_select
    + chat_select
)


# ============================================================
# IMPORTANT:
#
# We need to identify "NO_PATH" using filename, but some
# versions may not even have a filename column.
# ============================================================

if "filename" not in attachment_columns:

    print(
        "ERROR: Your attachment table does not contain "
        "a 'filename' column."
    )

    print()
    print(
        "The diagnostic cannot determine NO_PATH records "
        "on this database schema."
    )

    print()
    print("All attachment columns are:")
    print()

    for column in sorted(
        attachment_columns
    ):

        print(
            f"  {column}"
        )

    print()

    conn.close()

    sys.exit(1)


query = f"""
SELECT
        {select_clause}

FROM attachment a

JOIN message_attachment_join maj
    ON maj.attachment_id = a.ROWID

JOIN message m
    ON m.ROWID = maj.message_id

LEFT JOIN handle h
    ON h.ROWID = m.handle_id

LEFT JOIN chat_message_join cmj
    ON cmj.message_id = m.ROWID

LEFT JOIN chat c
    ON c.ROWID = cmj.chat_id

WHERE
    a.filename IS NULL
    OR
    TRIM(a.filename) = ''

ORDER BY
    m.date ASC,
    a.ROWID ASC
"""


# ============================================================
# EXECUTE
# ============================================================

print(
    "Finding attachments with no usable filename..."
)

print()


try:

    rows = conn.execute(
        query
    ).fetchall()

except sqlite3.OperationalError as e:

    print("Database query failed:")
    print(e)
    print()

    print(
        "SQL used:"
    )

    print(
        query
    )

    print()

    conn.close()

    sys.exit(1)


print(
    f"NO_PATH attachment/message records found: "
    f"{len(rows):,}"
)

print()


# ============================================================
# CSV
# ============================================================

csv_file = open(
    CSV_FILE,
    "w",
    newline="",
    encoding="utf-8"
)

csv_writer = csv.writer(
    csv_file
)


csv_columns = []


for column in optional_attachment_columns:

    if column in attachment_columns:

        csv_columns.append(
            column
        )


csv_header = [
    "attachment_rowid"
]

csv_header += csv_columns

csv_header += [
    "message_rowid",
    "message_date",
    "message_text",
    "message_is_from_me",
    "sender_address",
    "sender_service",
    "chat_rowid",
    "chat_identifier",
    "display_name",
    "room_name",
]


csv_writer.writerow(
    csv_header
)


# ============================================================
# TEXT REPORT
# ============================================================

report = open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
)


report.write(
    "Messages Attachment Verification Report\n"
)

report.write(
    "=" * 80
    + "\n\n"
)

report.write(
    "This report contains attachment records where\n"
    "attachment.filename is NULL or empty.\n\n"
)

report.write(
    f"Records found: {len(rows):,}\n\n"
)


# ============================================================
# SUMMARY COUNTERS
# ============================================================

uti_counts = Counter()
mime_counts = Counter()
sticker_counts = Counter()
outgoing_counts = Counter()
transfer_counts = Counter()
chat_counts = Counter()


# ============================================================
# PROCESS RECORDS
# ============================================================

for index, row in enumerate(
    rows,
    start=1
):

    attachment_rowid = get_value(
        row,
        "attachment_rowid"
    )

    guid = get_value(
        row,
        "guid"
    )

    filename = get_value(
        row,
        "filename"
    )

    transfer_name = get_value(
        row,
        "transfer_name"
    )

    uti = get_value(
        row,
        "uti"
    )

    mime_type = get_value(
        row,
        "mime_type"
    )

    total_bytes = get_value(
        row,
        "total_bytes"
    )

    is_sticker = get_value(
        row,
        "is_sticker"
    )

    is_outgoing = get_value(
        row,
        "is_outgoing"
    )

    created_date = apple_date(
        row["created_date"]
        if "created_date" in row.keys()
        else None
    )

    start_date = apple_date(
        row["start_date"]
        if "start_date" in row.keys()
        else None
    )

    message_date = apple_date(
        row["message_date"]
        if "message_date" in row.keys()
        else None
    )

    message_text = get_value(
        row,
        "message_text"
    )

    sender_address = get_value(
        row,
        "sender_address"
    )

    sender_service = get_value(
        row,
        "sender_service"
    )

    chat_identifier = get_value(
        row,
        "chat_identifier"
    )

    display_name = get_value(
        row,
        "display_name"
    )

    room_name = get_value(
        row,
        "room_name"
    )


    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    uti_counts[
        uti or "(empty)"
    ] += 1

    mime_counts[
        mime_type or "(empty)"
    ] += 1

    sticker_counts[
        is_sticker or "(empty)"
    ] += 1

    outgoing_counts[
        is_outgoing or "(empty)"
    ] += 1

    transfer_counts[
        transfer_name or "(empty)"
    ] += 1

    chat_name = (
        display_name
        or chat_identifier
        or "(unknown)"
    )

    chat_counts[
        chat_name
    ] += 1


    # --------------------------------------------------------
    # CSV row
    # --------------------------------------------------------

    csv_row = [
        attachment_rowid
    ]


    for column in csv_columns:

        csv_row.append(
            get_value(
                row,
                column
            )
        )


    csv_row += [
        get_value(
            row,
            "message_rowid"
        ),
        message_date,
        message_text,
        get_value(
            row,
            "message_is_from_me"
        ),
        sender_address,
        sender_service,
        get_value(
            row,
            "chat_rowid"
        ),
        chat_identifier,
        display_name,
        room_name,
    ]


    csv_writer.writerow(
        csv_row
    )


    # --------------------------------------------------------
    # Human-readable report
    # --------------------------------------------------------

    report.write(
        "\n"
        + "#" * 80
        + "\n"
    )

    report.write(
        f"RECORD {index} OF {len(rows)}\n"
    )

    report.write(
        "#" * 80
        + "\n\n"
    )


    report.write(
        f"Attachment ROWID:   "
        f"{attachment_rowid}\n"
    )

    report.write(
        f"GUID:                "
        f"{guid or '(empty)'}\n"
    )

    report.write(
        f"filename:            "
        f"{filename or '(NULL / EMPTY)'}\n"
    )

    report.write(
        f"transfer_name:       "
        f"{transfer_name or '(empty)'}\n"
    )

    report.write(
        f"UTI:                 "
        f"{uti or '(empty)'}\n"
    )

    report.write(
        f"MIME type:           "
        f"{mime_type or '(empty)'}\n"
    )

    report.write(
        f"total_bytes:         "
        f"{total_bytes or '(empty)'}\n"
    )

    report.write(
        f"is_sticker:          "
        f"{is_sticker or '(empty)'}\n"
    )

    report.write(
        f"is_outgoing:         "
        f"{is_outgoing or '(empty)'}\n"
    )

    report.write(
        f"created_date:        "
        f"{created_date or '(empty)'}\n"
    )

    report.write(
        f"start_date:          "
        f"{start_date or '(empty)'}\n"
    )


    # --------------------------------------------------------
    # Print every optional column actually present.
    # --------------------------------------------------------

    for column in csv_columns:

        if column in (
            "guid",
            "filename",
            "transfer_name",
            "uti",
            "mime_type",
            "total_bytes",
            "is_sticker",
            "is_outgoing",
            "created_date",
            "start_date",
        ):

            continue


        report.write(
            f"{column}:"
            f"{' ' * max(1, 20 - len(column))}"
            f"{get_value(row, column) or '(empty)'}\n"
        )


    report.write("\n")

    report.write(
        f"Message ROWID:       "
        f"{get_value(row, 'message_rowid')}\n"
    )

    report.write(
        f"Message date:        "
        f"{message_date or '(empty)'}\n"
    )

    report.write(
        f"From me:             "
        f"{get_value(row, 'message_is_from_me') or '(empty)'}\n"
    )

    report.write(
        f"Sender:              "
        f"{sender_address or '(unknown)'}\n"
    )

    report.write(
        f"Service:             "
        f"{sender_service or '(unknown)'}\n"
    )

    report.write(
        f"Chat ROWID:          "
        f"{get_value(row, 'chat_rowid')}\n"
    )

    report.write(
        f"Chat identifier:     "
        f"{chat_identifier or '(empty)'}\n"
    )

    report.write(
        f"Display name:        "
        f"{display_name or '(empty)'}\n"
    )

    report.write(
        f"Room name:           "
        f"{room_name or '(empty)'}\n"
    )

    report.write("\n")

    report.write(
        "Message text:\n"
    )

    report.write(
        message_text
        if message_text
        else "(empty)"
    )

    report.write(
        "\n"
    )


# ============================================================
# SUMMARY
# ============================================================

report.write(
    "\n\n"
    + "=" * 80
    + "\n"
)

report.write(
    "SUMMARY\n"
)

report.write(
    "=" * 80
    + "\n\n"
)

report.write(
    f"NO_PATH records: {len(rows):,}\n\n"
)


report.write(
    "UTI breakdown:\n"
)

for key, count in uti_counts.most_common():

    report.write(
        f"  {count:8,}  {key}\n"
    )


report.write(
    "\nMIME type breakdown:\n"
)

for key, count in mime_counts.most_common():

    report.write(
        f"  {count:8,}  {key}\n"
    )


report.write(
    "\nis_sticker breakdown:\n"
)

for key, count in sticker_counts.most_common():

    report.write(
        f"  {count:8,}  {key}\n"
    )


report.write(
    "\nis_outgoing breakdown:\n"
)

for key, count in outgoing_counts.most_common():

    report.write(
        f"  {count:8,}  {key}\n"
    )


report.write(
    "\ntransfer_name breakdown:\n"
)

for key, count in transfer_counts.most_common():

    report.write(
        f"  {count:8,}  {key}\n"
    )


report.write(
    "\nConversations containing NO_PATH records:\n"
)

for key, count in chat_counts.most_common():

    report.write(
        f"  {count:8,}  {key}\n"
    )


# ============================================================
# CLOSE
# ============================================================

report.close()
csv_file.close()
conn.close()


# ============================================================
# TERMINAL SUMMARY
# ============================================================

print("=" * 80)
print("ATTACHMENT VERIFICATION COMPLETE")
print("=" * 80)
print()

print(
    f"NO_PATH records: {len(rows):,}"
)

print()

print("UTI breakdown:")

for key, count in uti_counts.most_common():

    print(
        f"  {count:8,}  {key}"
    )

print()

print("MIME type breakdown:")

for key, count in mime_counts.most_common():

    print(
        f"  {count:8,}  {key}"
    )

print()

print("is_sticker breakdown:")

for key, count in sticker_counts.most_common():

    print(
        f"  {count:8,}  {key}"
    )

print()

print("transfer_name breakdown:")

for key, count in transfer_counts.most_common():

    print(
        f"  {count:8,}  {key}"
    )

print()
print("Reports:")
print()
print(f"  {REPORT_FILE}")
print(f"  {CSV_FILE}")
print()

