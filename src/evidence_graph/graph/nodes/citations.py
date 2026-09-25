import re
import unicodedata

from evidence_graph.state import IncentiveRecord
from evidence_graph.tools import FetchedPage

# Digits separated only by thousands/decimal separators count as one number: "5,700", "5 700".
_CLAIM_NUMBER = re.compile(r"\d(?:[\d,.\u00a0\u202f]*\d)?")
_PAGE_SEPARATOR = r"[\s,.\u00a0\u202f']?"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u00ab", '"')
    text = text.replace("\u00bb", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


def number_in_text(digits: str, page_text: str) -> bool:
    pattern = _PAGE_SEPARATOR.join(re.escape(d) for d in digits)
    return re.search(rf"(?<!\d){pattern}(?!\d)", page_text) is not None


def _number_in_page(digits: str, page_text: str) -> bool:
    return number_in_text(digits, page_text)


def claim_numbers(text: str) -> list[str]:
    return [re.sub(r"\D", "", match) for match in _CLAIM_NUMBER.findall(text)]


def check_record(record: IncentiveRecord, page: FetchedPage) -> list[str]:
    """Return every reason the record is not supported by the page it cites. Empty means OK."""
    problems: list[str] = []
    page_norm = normalize(page.text)

    if any(str(c.url) != page.url for c in record.citations):
        problems.append(f"{record.name!r}: cites a URL other than the fetched page")

    quotes = [c.quote for c in record.citations if c.quote]
    if not quotes:
        problems.append(f"{record.name!r}: no verbatim quote from the page")
    for quote in quotes:
        if normalize(quote) not in page_norm:
            problems.append(f"{record.name!r}: quote not found in page: {quote[:80]!r}")

    for digits in claim_numbers(" ".join(record.eligibility)):
        if not _number_in_page(digits, page.text):
            problems.append(f"{record.name!r}: number {digits} does not appear in the page")

    # Benefit amounts must travel with their evidence, not just appear somewhere on the page.
    quoted = " ".join(quotes)
    for digits in claim_numbers(record.benefit):
        if not _number_in_page(digits, quoted):
            problems.append(f"{record.name!r}: benefit number {digits} is not in its quotes")

    return problems
