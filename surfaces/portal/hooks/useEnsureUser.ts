import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";

/**
 * Hook to ensure user exists in backend database after login.
 * Calls the ensure API route to create user if needed.
 */
export function useEnsureUser() {
    const { data: session, status } = useSession();
    const [ensuring, setEnsuring] = useState(false);
    const [user, setUser] = useState<any>(null);

    useEffect(() => {
        if (status === "authenticated" && session?.user && !ensuring && !user) {
            const ensureUser = async () => {
                try {
                    setEnsuring(true);
                    const response = await fetch("/api/users/ensure", {
                        method: "POST"
                    });

                    if (response.ok) {
                        const data = await response.json();
                        setUser(data.user);
                    } else {
                        const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
                        console.error("Failed to ensure user exists:", errorData.error || response.status);
                        // Don't throw - allow the app to continue even if user creation fails
                        // User can still use the app, just won't be in the users table yet
                    }
                } catch (error) {
                    console.error("Error ensuring user:", error);
                } finally {
                    setEnsuring(false);
                }
            };

            ensureUser();
        }
    }, [status, session, ensuring, user]);

    return { user, ensuring };
}

