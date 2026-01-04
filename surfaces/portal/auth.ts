import NextAuth, { type DefaultSession } from "next-auth"
import Google from "next-auth/providers/google"

declare module "next-auth" {
    interface Session {
        user: {
            /** The user's postal address. */
            id: string
        } & DefaultSession["user"]
    }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
    providers: [
        Google({
            clientId: process.env.AUTH_GOOGLE_ID,
            clientSecret: process.env.AUTH_GOOGLE_SECRET,
        }),
    ],
    callbacks: {
        authorized({ request, auth }) {
            const { pathname } = request.nextUrl
            if (pathname === "/dashboard") return !!auth
            return true
        },
        jwt({ token, user, account }) {
            if (user) {
                // Store Google OAuth subject ID (unique user identifier)
                // account.providerAccountId contains the Google subject ID
                token.id = account?.providerAccountId || user.id || user.email
            }
            return token
        },
        session({ session, token }) {
            if (session.user) {
                session.user.id = token.id as string
            }
            return session
        }
    },
    pages: {
        signIn: "/auth/signin",
    },
})
