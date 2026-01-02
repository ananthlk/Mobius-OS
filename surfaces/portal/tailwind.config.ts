import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "var(--background)",
                foreground: "var(--foreground)",
            },
            keyframes: {
                dots: {
                    '0%, 20%': { opacity: '0' },
                    '50%': { opacity: '1' },
                    '100%': { opacity: '0' },
                },
            },
            animation: {
                'dots': 'dots 1.4s infinite',
            },
        },
    },
    plugins: [],
};
export default config;
