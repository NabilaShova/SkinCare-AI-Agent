# AI Customer Support Agent for Shopify Beauty & Skincare Stores

## Overview

A production-ready AI customer support SaaS platform for Shopify beauty and skincare merchants.
It offers intelligent product support, product recommendations, Shopify data sync, knowledge base search, order support, human escalation, and analytics.

## Architecture

- Frontend: Next.js 15, React, Tailwind CSS, shadcn/ui
- Backend: Python FastAPI
- Database: PostgreSQL + pgvector
- AI: OpenAI GPT + LangChain + LangGraph + RAG
- Auth: Shopify OAuth
- Deployment: Docker / docker-compose

## Workspace Structure

- `frontend/` — Next.js UI and admin dashboard
- `backend/` — FastAPI application, Shopify integration, RAG services
- `docker-compose.yml` — local container orchestration
- `README.md` — developer setup and architecture notes

## Local Setup

1. Copy `.env.example` to `.env` in both `backend/` and `frontend/`.
2. Configure Shopify OAuth, OpenAI key, and PostgreSQL connection.
3. Start services:

```bash
docker compose up --build
```

4. Visit:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/docs`

## Next Steps

- Implement Shopify store onboarding and OAuth flow
- Add full RAG embeddings pipeline and vector search
- Build admin dashboard pages for Conversations, Products, Knowledge Base, Analytics
- Enable secure multi-tenant data isolation for Shopify stores
"# SkinCare-AI-Agent" 
# SkinCare-AI-Agent
