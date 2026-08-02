"""The HTTP surface — every route, and nothing else.

`create_app` builds the FastAPI app around an assembled Assistant: the load-
shedding middleware at the door, the optional Bearer-JWT dependency on every
mutating route, and the four endpoints (/health, /ingest, /ask + /ask/stream,
/approve). No business logic lives here — the routes translate HTTP in and out
of `Assistant` calls, which is why the whole surface is testable with a
TestClient and no network.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from assistant import auth
from assistant.resilience import ConcurrencyCap, TokenBucket
from assistant.service import build_assistant
from assistant.settings import Settings


class AskBody(BaseModel):
    question: str


class IngestBody(BaseModel):
    docs: list[str]


class ApproveBody(BaseModel):
    tool: str


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="GenAI assistant capstone")
    assistant = build_assistant(settings)
    app.state.assistant = assistant
    s = assistant.settings

    # --- load shedding: refuse politely at the door, don't fall over inside ------
    bucket = (
        TokenBucket(rate=s.rate_limit_rps, burst=s.rate_limit_burst)
        if s.rate_limit_rps
        else None
    )
    cap = ConcurrencyCap(s.max_concurrency) if s.max_concurrency else None
    app.state.bucket, app.state.cap = bucket, cap

    @app.middleware("http")
    async def throttle(request: Request, call_next):
        if request.url.path != "/health":  # probes must never be shed
            if bucket is not None and not bucket.take():
                return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
            if cap is not None and not cap.enter():
                return JSONResponse({"detail": "server at capacity"}, status_code=503)
            try:
                return await call_next(request)
            finally:
                if cap is not None:
                    cap.leave()
        return await call_next(request)

    def require(scope: str) -> Callable[..., str]:
        """A FastAPI dependency enforcing the optional Bearer-JWT gate for one
        scope. With auth off (no ASSISTANT_JWT_SECRET) it resolves to the
        anonymous identity and never rejects — the zero-key demo path."""

        def dependency(request: Request) -> str:
            ok, reason, subject = auth.identity_from(
                request.headers.get("authorization", ""),
                secret=s.jwt_secret, audience=s.jwt_audience, required_scope=scope,
            )
            if not ok:
                raise HTTPException(status_code=401, detail=reason)
            return subject

        return dependency

    @app.get("/health")
    def health() -> dict:
        # spans_recorded lets an end-to-end verifier confirm observability is live
        # from outside the process — the in-memory exporter is always attached.
        return {
            "status": "degraded" if assistant.degraded else "ok",
            "tier": assistant.tier(),
            "degraded": assistant.degraded,
            "spans_recorded": len(assistant.rec.spans()),
        }

    @app.post("/ingest")
    def ingest(
        body: IngestBody, subject: str = Depends(require("assistant:ingest"))
    ) -> dict:
        # documents land in the CALLER's tenant — retrieval is scoped the same way
        return {"ingested": assistant.rag.add(body.docs, tenant=subject)}

    @app.post("/ask")
    def ask(body: AskBody, subject: str = Depends(require("assistant:ask"))) -> dict:
        return assistant.ask(body.question, subject)

    @app.post("/ask/stream")
    def ask_stream(
        body: AskBody, subject: str = Depends(require("assistant:ask"))
    ) -> StreamingResponse:
        return StreamingResponse(
            assistant.ask_stream(body.question, subject),
            media_type="text/event-stream",
        )

    @app.post("/approve")
    def approve(
        body: ApproveBody,
        request: Request,
        subject: str = Depends(require("assistant:approve")),
    ) -> dict:
        # a retried request (same Idempotency-Key) is acknowledged, not re-applied
        key = request.headers.get("idempotency-key")
        if key and assistant.idempotency.seen(key):
            assistant.audit_log.record("approval.replayed", subject, body.tool)
            return {"approved": body.tool, "replayed": True}
        assistant.grants[body.tool] = assistant.grants.get(body.tool, 0) + 1
        assistant.audit_log.record("approval.granted", subject, body.tool)
        return {"approved": body.tool}

    return app
