import { signIn } from "@/auth";
import MobiusIcon from "@/components/MobiusIcon";
import BrandName from "@/components/BrandName";

export default function SignIn() {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--bg-primary)] p-4">

            <div className="w-full max-w-[400px] p-8 md:p-12 border border-gray-200 rounded-[28px] shadow-sm bg-white flex flex-col items-center">

                {/* Logo */}
                <div className="mb-4">
                    <MobiusIcon size={48} />
                </div>

                <h1 className="text-2xl font-normal text-[var(--text-primary)] mb-2">Sign in</h1>
                <p className="text-base text-[var(--text-secondary)] mb-10">
                    to continue to <BrandName variant="withOS" />
                </p>

                <form
                    className="w-full mb-8"
                    action={async () => {
                        "use server"
                        await signIn("google", { redirectTo: "/dashboard" })
                    }}
                >
                    {/* Custom Google Button to match guidelines */}
                    <button type="submit" className="w-full flex items-center justify-between px-1 py-1 rounded-full border border-gray-300 hover:bg-[var(--bg-secondary)] hover:border-gray-400 transition-all group">
                        <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center">
                            <svg className="w-5 h-5" viewBox="0 0 24 24">
                                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                            </svg>
                        </div>
                        <span className="flex-1 text-center font-medium text-[var(--text-primary)]">Continue with Google</span>
                        <div className="w-10"></div> {/* Spacer for centering */}
                    </button>
                </form>

                <div className="text-sm text-[#1a73e8] hover:underline cursor-pointer">
                    Create account
                </div>
            </div>

            <div className="mt-8 flex gap-6 text-xs text-[var(--text-secondary)]">
                <span className="cursor-pointer hover:text-[var(--text-primary)]">Help</span>
                <span className="cursor-pointer hover:text-[var(--text-primary)]">Privacy</span>
                <span className="cursor-pointer hover:text-[var(--text-primary)]">Terms</span>
            </div>
        </div>
    )
}
