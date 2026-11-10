"""Streaming reader for all.tsv: tab-separated, one edge per line, sorted by graph id.

Columns: source-id, source-type, dest-id, dest-type, edge-type, graph-id.
Time convention: t is the 1-based physical line number in the file (the reference code uses
the PostgreSQL insertion order, which is the same ordering; confirm the offset in Phase 2).
"""
from typing import Callable, Iterable, Iterator, List, NamedTuple, Optional, Tuple


class Row(NamedTuple):
    line: int
    src: str
    src_type: str
    dst: str
    dst_type: str
    edge_type: str


def parse_line(line: str) -> Optional[Tuple[str, str, str, str, str, int]]:
    """Return the six fields, or None for a blank or malformed line."""
    line = line.rstrip("\r\n")
    if not line.strip():
        return None
    parts = line.split("\t")
    if len(parts) != 6:
        parts = line.split()
    if len(parts) != 6:
        return None
    try:
        gid = int(parts[5])
    except ValueError:
        return None
    return parts[0], parts[1], parts[2], parts[3], parts[4], gid


def iter_graph_blocks(lines: Iterable[str],
                      on_malformed: Optional[Callable[[int, str], None]] = None
                      ) -> Iterator[Tuple[int, List[Row]]]:
    """Yield (graph_id, rows) one graph at a time. Raises if a graph id reappears after its
    block ended, because the whole pipeline assumes contiguous blocks."""
    current: Optional[int] = None
    block: List[Row] = []
    done = set()
    for n, line in enumerate(lines, start=1):
        parsed = parse_line(line)
        if parsed is None:
            if line.strip() and on_malformed:
                on_malformed(n, line)
            continue
        src, st, dst, dt, et, gid = parsed
        if gid != current:
            if current is not None:
                yield current, block
                done.add(current)
            if gid in done:
                raise ValueError("graph %d reappears at line %d: file is not sorted into blocks" % (gid, n))
            current, block = gid, []
        block.append(Row(n, src, st, dst, dt, et))
    if current is not None:
        yield current, block
