from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.core.security import require_admin
from app.db.models import Document, EmbeddingRecord
from app.db.session import get_db
from app.services.rag import chunk_text, generate_embeddings
from sqlalchemy.orm import Session

router = APIRouter()


def _extract_text(filename: str, content: bytes) -> str:
    lowered = filename.lower()
    if lowered.endswith((".txt", ".md", ".csv")):
        return content.decode("utf-8", errors="ignore")
    if lowered.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            from io import BytesIO

            reader = PdfReader(BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Unable to parse PDF file") from exc
    raise HTTPException(status_code=400, detail="Unsupported file type. Upload .txt, .md, or .pdf")


@router.get("/")
def list_documents(store_id: int = 1, _: None = Depends(require_admin), db: Session = Depends(get_db)) -> Any:
    documents = (
        db.query(Document)
        .filter(Document.store_id == store_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": document.id,
                "filename": document.filename,
                "content_type": document.content_type,
                "status": document.status,
                "created_at": document.created_at.isoformat(),
            }
            for document in documents
        ]
    }


@router.post("/upload")
async def upload_document(
    store_id: int = Form(...),
    file: UploadFile = File(...),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    raw_bytes = await file.read()
    if len(raw_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 5MB limit")

    raw_text = _extract_text(file.filename, raw_bytes).strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="No readable text found in uploaded file")

    document = Document(
        store_id=store_id,
        filename=file.filename,
        content_type=file.content_type or "text/plain",
        status="processing",
        raw_text=raw_text,
    )
    db.add(document)
    db.flush()

    chunks = chunk_text(raw_text)
    embeddings = generate_embeddings(chunks)
    for index, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        db.add(
            EmbeddingRecord(
                store_id=store_id,
                document_id=document.id,
                chunk_text=chunk,
                vector=vector,
                meta={"source": file.filename, "chunk_index": index, "type": "document"},
            )
        )

    document.status = "processed"
    db.commit()
    db.refresh(document)

    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "chunks_indexed": len(chunks),
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    store_id: int,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.store_id == store_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.query(EmbeddingRecord).filter(EmbeddingRecord.document_id == document.id).delete()
    db.delete(document)
    db.commit()
    return {"deleted": True, "document_id": document_id}
