# Mobius OS - Design Stream

## Sprint 1: The First Thread

**Goal**: Establish the "First Thread" - a complete loop where a user can login, ask a question, and get a stored, intelligent response.

### Decisions Log
1.  **Auth**: Using Google Authentication (Gmail) for personalization.
2.  **Storage**: Interactions are stored in PostgreSQL for structured history.
3.  **Knowledge Base**: This file (`continuum/stream/design_log.md`) and others in `continuum/` serve as the RAG source.
4.  **Interfaces**: Both a Web Portal (Next.js) and Chrome Extension (Spectacles) will be built immediately to test the "Context Aware" capabilities.
6.  **Visual Theme**: "The Infinite Loop" selected.
    -   *Attributes*: Harmonic, Flow, Recovery.
    -   *Palette*: Soft white/grey glassmorphism, iridescent blue/purple gradients, floating cards.
    -   *Rationale*: Aligns with "Community Mental Health" - approachable, healing, yet modern.
-   *NextAuth vs Clerk/Supabase Auth?*
-   *Local vector store vs Pinecone/Weaviate?*
