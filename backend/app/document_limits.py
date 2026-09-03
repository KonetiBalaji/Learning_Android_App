"""Admission limits before handing a DOCX archive to the document parser."""
from io import BytesIO
from pathlib import PurePosixPath
import zipfile

MAX_ARCHIVE_MEMBERS = 2048
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1000


def validate_docx_archive(content: bytes) -> None:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        members = archive.infolist()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise ValueError('Too many archive members')
        names = set()
        total = 0
        for member in members:
            path = PurePosixPath(member.filename)
            if (member.filename in names or path.is_absolute() or '..' in path.parts
                    or '\\' in member.orig_filename or ':' in member.filename or '\x00' in member.orig_filename):
                raise ValueError('Invalid or duplicate archive path')
            names.add(member.filename)
            if member.flag_bits & 1:
                raise ValueError('Encrypted archives are not supported')
            if member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError('Unsupported archive compression')
            total += member.file_size
            if member.file_size > MAX_MEMBER_BYTES or total > MAX_ARCHIVE_BYTES:
                raise ValueError('Expanded archive exceeds processing limits')
            if member.file_size > max(member.compress_size, 1) * MAX_COMPRESSION_RATIO:
                raise ValueError('Archive compression ratio exceeds processing limits')
        if not {'[Content_Types].xml', 'word/document.xml'}.issubset(names):
            raise ValueError('Required DOCX parts are missing')
        # Verify actual readable contents and CRC before the XML parser sees them.
        # Bounded chunks avoid building another full decompressed archive in memory.
        actual_total = 0
        for member in members:
            if member.is_dir():
                continue
            actual_member = 0
            with archive.open(member) as source:
                while chunk := source.read(64 * 1024):
                    actual_member += len(chunk)
                    actual_total += len(chunk)
                    if actual_member > MAX_MEMBER_BYTES or actual_total > MAX_ARCHIVE_BYTES:
                        raise ValueError('Expanded archive exceeds processing limits')
            if actual_member != member.file_size:
                raise ValueError('Archive size mismatch')
