from __future__ import annotations
from fastapi import APIRouter, File, Query, Request, Response, UploadFile

from app.schemas.api import ChatRequest, SearchRequest

router = APIRouter(prefix="/api")


def svc(request: Request):
    return request.app.state.service


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request):
    s = svc(request).system_status()["components"]
    return {"ready": s["database"]["ok"], "components": {k: v["ok"] for k, v in s.items()}}


@router.post("/documents", status_code=202)
async def upload(request: Request, response: Response, file: UploadFile = File(...)):
    s = svc(request)
    data = await file.read(s.settings.max_upload_mb * 1024 * 1024 + 1)  # bounded read
    doc, dup = s.upload(file.filename or "upload", file.content_type, data)
    if dup:
        response.status_code = 200
        return {"document": doc, "duplicate": True}
    return {"document": s.process(doc["id"]), "duplicate": False}


@router.get("/documents")
def list_documents(request: Request, q: str | None = None, status: str | None = None, kind: str | None = None,
                   doc_type: str | None = None, sort: str = "created_at", order: str = "desc",
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    rows, total = svc(request).store.list_documents(q, status, kind, doc_type, sort, order, page, page_size)
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/documents/{doc_id}")
def get_document(request: Request, doc_id: str):
    return svc(request).get_document(doc_id)


@router.get("/documents/{doc_id}/status")
def status(request: Request, doc_id: str):
    d = svc(request).get_document(doc_id)
    return {"id": doc_id, "status": d["status"], "error": d["error"], "stage": (d["job"] or {}).get("stage")}


@router.get("/documents/{doc_id}/text")
def text(request: Request, doc_id: str):
    return {"document_id": doc_id, "pages": svc(request).pages(doc_id)}


@router.get("/documents/{doc_id}/insights")
def insights(request: Request, doc_id: str):
    return svc(request).insights(doc_id)


@router.delete("/documents/{doc_id}", status_code=204)
def delete(request: Request, doc_id: str):
    svc(request).delete_document(doc_id)
    return Response(status_code=204)


@router.post("/documents/{doc_id}/reprocess", status_code=202)
def reprocess(request: Request, doc_id: str):
    return svc(request).reprocess(doc_id)


@router.post("/demo/load", status_code=202)
def demo(request: Request):
    return {"documents": svc(request).load_demo(), "label": "Synthetic demo documents"}


@router.post("/chat")
def chat(request: Request, body: ChatRequest):
    return svc(request).ask(body.question, body.conversation_id, body.document_ids)


@router.get("/conversations/{cid}")
def conversation(request: Request, cid: str):
    return svc(request).conversation(cid)


@router.post("/search")
def search(request: Request, body: SearchRequest):
    return svc(request).search(body.query, body.mode, body.document_ids, body.doc_type, body.date_from, body.date_to, body.k)


@router.get("/analytics")
def analytics(request: Request):
    return svc(request).analytics()


@router.post("/evaluation/run")
def run_eval(request: Request):
    return svc(request).run_eval()


@router.get("/evaluation/latest")
def latest_eval(request: Request):
    return svc(request).store.latest_eval_run() or {"metrics": None, "results": []}


@router.get("/system/status")
def system(request: Request):
    return svc(request).system_status()
