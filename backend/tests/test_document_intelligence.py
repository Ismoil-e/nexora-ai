import asyncio
import hashlib

from app.intelligence.contracts.types import ExtractedChunk
from app.intelligence.core.classifier import classifier
from app.intelligence.core.duplicate_detector import duplicate_detector
from app.intelligence.core.entity_relationship_extractor import EntityRelationshipExtractor
from app.intelligence.core.intelligent_chunker import IntelligentChunker
from app.intelligence.core.language import detect_language
from app.intelligence.pipeline import DocumentIntelligencePipeline


# ---- Language detection -------------------------------------------------------

def test_language_detect_uzbek():
    text = "Bu shartnoma tomonlar o'rtasida tuziladi va ish yuritish qoidalariga amal qilinadi."
    assert detect_language(text) == "uz"


def test_language_detect_russian():
    text = "Настоящий договор заключен между сторонами в соответствии с законодательством."
    assert detect_language(text) == "ru"


def test_language_detect_english():
    text = "This agreement is entered into by and between the parties in accordance with applicable law."
    assert detect_language(text) == "en"


# ---- Intelligent chunker --------------------------------------------------------

def test_chunker_keeps_short_chunk_intact():
    chunker = IntelligentChunker(target_chunk_size=800, overlap=150)
    raw = [
        ExtractedChunk(
            chunk_index=0,
            content="Qisqa matn. Ikkinchi jumla.",
            page_number=1,
            section_title="Kirish",
            chunk_type="text",
            metadata={"source": "test.txt"},
        )
    ]
    processed = chunker.process_chunks(raw)
    assert len(processed) == 1
    assert processed[0].content == "Qisqa matn. Ikkinchi jumla."
    assert processed[0].page_number == 1
    assert processed[0].section_title == "Kirish"
    assert processed[0].chunk_index == 0
    assert processed[0].metadata.get("source") == "test.txt"


def test_chunker_splits_long_text():
    chunker = IntelligentChunker(target_chunk_size=100, overlap=10)
    long_paragraph = "A. " * 200
    raw = [
        ExtractedChunk(
            chunk_index=0,
            content=f"Birinchi blok\n\n{long_paragraph}\n\nYakuniy xulosa paragrafi bu yerda.",
            chunk_type="text",
            page_number=2,
        )
    ]
    processed = chunker.process_chunks(raw)
    assert len(processed) >= 2
    assert all(c.page_number == 2 for c in processed)
    assert [c.chunk_index for c in processed] == list(range(len(processed)))


def test_chunker_keeps_table_chunk_intact():
    chunker = IntelligentChunker(target_chunk_size=800, overlap=150)
    big_table = ExtractedChunk(
        chunk_index=0,
        content=("|Col A|Col B|\n|1|2|\n|3|4|\n" * 50),
        chunk_type="table",
        page_number=1,
    )
    processed = chunker.process_chunks([big_table])
    assert len(processed) == 1
    assert processed[0].chunk_type == "table"


# ---- Document classification ----------------------------------------------------

def test_classifier_invoice():
    text = "HISOB-FAKTURA (Invoice)\nJami summa: 12 500 000 UZS\nTo'lov usuli: bank o'tkazmasi\nQSHs 12%"
    assert classifier.classify(text) == "Invoice"


def test_classifier_contract():
    text = "SHARTNOMA (Agreement)\nBuyurtmachi va Ijrochi tomonlar o'rtasida...\nShartlar va nizolarni hal qilish."
    assert classifier.classify(text) == "Contract"


def test_classifier_unknown():
    assert classifier.classify("qqq rrr sss ttt uuu") == "Other"


# ---- Duplicate detection ---------------------------------------------------------

def test_duplicate_hash_identical_bytes():
    a = b"same binary content"
    b = b"same binary content"
    assert duplicate_detector.compute_content_hash(a) == duplicate_detector.compute_content_hash(b)
    assert duplicate_detector.compute_content_hash(a) == hashlib.sha256(a).hexdigest()


def test_duplicate_hash_differs():
    a = duplicate_detector.compute_content_hash(b"content one")
    b = duplicate_detector.compute_content_hash(b"content two")
    assert a != b


# ---- Entity / relationship extractor (regex layer) --------------------------------

def test_entity_extractor_regex_email_and_company():
    async def _run():
        chunk = ExtractedChunk(
            chunk_index=0,
            content="Aloqa: ismoil@example.com va ismoil@example.com. Kompaniya: Nexora OK va Nexora OK.",
            chunk_type="text",
        )
        extractor = EntityRelationshipExtractor(db=None)
        return await extractor.extract_from_chunks([chunk], document_title="test")

    entities, relationships = asyncio.run(_run())
    names = [(e.entity_name, e.entity_type) for e in entities]
    assert ("ismoil@example.com", "Person") in names
    assert any(t == "Company" for _n, t in names)


# ---- Pipeline extraction path (no DB needed) ----------------------------------------

def test_pipeline_text_like_extract_returns_extracted_chunks():
    async def _run():
        pipeline = DocumentIntelligencePipeline(db=None)
        return await pipeline._extract(b"hello world\ntest line", "txt", "notes.txt")

    result = asyncio.run(_run())
    assert result["full_text"] == "hello world\ntest line"
    assert len(result["chunks"]) == 1
    chunk = result["chunks"][0]
    assert isinstance(chunk, ExtractedChunk)
    assert chunk.content == "hello world\ntest line"
    assert chunk.chunk_type == "text"
    assert chunk.page_number == 1


def test_pipeline_unknown_format_graceful_notice():
    async def _run():
        pipeline = DocumentIntelligencePipeline(db=None)
        return await pipeline._extract(b"\x00\x01binary", "xyz", "file.xyz")

    result = asyncio.run(_run())
    assert result["chunks"] == []
    assert "UNSUPPORTED FORMAT" in result["full_text"]
    assert "file.xyz" in result["full_text"]


def test_pipeline_empty_text_file_no_chunks():
    async def _run():
        pipeline = DocumentIntelligencePipeline(db=None)
        return await pipeline._extract(b"", "txt", "empty.txt")

    result = asyncio.run(_run())
    assert result["full_text"] == ""
    assert result["chunks"] == []


# ---- ExtractedChunk model defaults ------------------------------------------------

def test_extracted_chunk_defaults():
    chunk = ExtractedChunk(chunk_index=0, content="content")
    assert chunk.chunk_type == "text"
    assert chunk.metadata == {}
    assert chunk.token_count == 0
