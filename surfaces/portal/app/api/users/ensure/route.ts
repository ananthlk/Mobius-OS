import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";

/**
 * API route to ensure user exists in backend database.
 * Called after login to create user record if it doesn't exist.
 */
export async function POST(request: NextRequest) {
    try {
        const session = await auth();
        
        if (!session?.user) {
            return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
        }

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        
        // Get user's Google auth ID (subject ID from Google OAuth)
        // NextAuth stores this in user.id (set from JWT token)
        // Fallback to email if id is not available (for backward compatibility)
        const authId = session.user.id || session.user.email;
        const email = session.user.email;
        const name = session.user.name || null;

        if (!authId || !email) {
            console.error("Missing user information:", { 
                hasId: !!session.user.id, 
                hasEmail: !!session.user.email,
                userId: session.user.id,
                userEmail: session.user.email 
            });
            return NextResponse.json({ error: "Missing user information" }, { status: 400 });
        }

        try {
            // Check if user exists in backend
            const checkResponse = await fetch(`${apiUrl}/api/users/auth/${encodeURIComponent(authId)}`, {
                headers: {
                    "X-User-ID": authId
                }
            });

            if (checkResponse.ok) {
                // User exists, return it
                const user = await checkResponse.json();
                return NextResponse.json({ user, created: false });
            }

            // User doesn't exist (404 is expected), create it
            if (checkResponse.status === 404) {
                const createResponse = await fetch(`${apiUrl}/api/users`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-User-ID": "system" // System creates the user on first login
                    },
                    body: JSON.stringify({
                        auth_id: authId,
                        email: email,
                        name: name,
                        role: "user" // Default role
                    })
                });

                if (!createResponse.ok) {
                    const errorText = await createResponse.text();
                    let errorDetail = "Failed to create user";
                    try {
                        const errorJson = JSON.parse(errorText);
                        errorDetail = errorJson.detail || errorDetail;
                    } catch {
                        errorDetail = errorText || errorDetail;
                    }
                    console.error("Failed to create user:", errorDetail);
                    return NextResponse.json({ error: errorDetail }, { status: createResponse.status });
                }

                const user = await createResponse.json();
                return NextResponse.json({ user, created: true });
            }

            // Other error from check
            console.error("Unexpected error checking user:", checkResponse.status);
            return NextResponse.json({ error: "Failed to check user" }, { status: checkResponse.status });
        } catch (fetchError) {
            console.error("Network error ensuring user:", fetchError);
            // If backend is not available, return a specific error
            if (fetchError instanceof TypeError && fetchError.message.includes("fetch")) {
                return NextResponse.json(
                    { error: "Backend API unavailable. Please ensure the backend server is running." },
                    { status: 503 }
                );
            }
            throw fetchError;
        }
    } catch (error) {
        console.error("Error ensuring user exists:", error);
        return NextResponse.json(
            { error: error instanceof Error ? error.message : "Internal server error" },
            { status: 500 }
        );
    }
}

