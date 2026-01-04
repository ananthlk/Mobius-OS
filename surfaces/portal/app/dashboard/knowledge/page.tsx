import MobiusIcon from "@/components/MobiusIcon";

export default function KnowledgePage() {
    return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="w-16 h-16 bg-[var(--brand-yellow-light)] text-[var(--brand-yellow-dark)] rounded-2xl flex items-center justify-center mb-6">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                </svg>
            </div>
            <h1 className="text-2xl font-semibold text-[var(--text-primary)] mb-2">Knowledge Base</h1>
            <p className="text-[var(--text-secondary)] max-w-md">
                RAG Ingestion and Knowledge Graph management coming soon.
            </p>
        </div>
    );
}
