"""Plain source text in body order, including tables; not a Word layout renderer."""
from docx.table import Table
from docx.text.paragraph import Paragraph

MAX_TEXT_CHARACTERS = 2_000_000
MAX_TABLE_DEPTH = 8
MAX_GRID_CELLS = 20_000


def extract_docx_body(document) -> str:
    characters = 0
    grid_cells = 0

    def body(container, depth):
        nonlocal characters, grid_cells
        blocks = []
        for block in container.iter_inner_content():
            if isinstance(block, Paragraph):
                value = block.text
                if value.strip():
                    characters += len(value) + 1
                    if characters > MAX_TEXT_CHARACTERS:
                        raise ValueError('DOCX extracted text exceeds processing limits')
                    blocks.append(value)
            elif isinstance(block, Table):
                if depth >= MAX_TABLE_DEPTH:
                    raise ValueError('DOCX tables exceed nesting limits')
                # Inspect spans before row.cells expands merged layout positions.
                for cell_xml in block._tbl.iter_tcs():
                    span = cell_xml.grid_span
                    if not 1 <= span <= MAX_GRID_CELLS:
                        raise ValueError('Invalid or excessive DOCX table span')
                    grid_cells += span
                    if grid_cells > MAX_GRID_CELLS:
                        raise ValueError('DOCX tables exceed cell limits')
                seen = set()
                rows = []
                for row in block.rows:
                    cells = []
                    for cell in row.cells:
                        # Merged cells are exposed repeatedly in the layout grid.
                        # Keep their source once and preserve empty tab positions.
                        if cell._tc in seen:
                            cells.append('')
                        else:
                            seen.add(cell._tc)
                            cells.append(body(cell, depth + 1))
                    rows.append('\t'.join(cells))
                blocks.append('\n'.join(rows))
        return '\n'.join(blocks)

    text = body(document, 0)
    if len(text) > MAX_TEXT_CHARACTERS:
        raise ValueError('DOCX extracted text exceeds processing limits')
    return text
