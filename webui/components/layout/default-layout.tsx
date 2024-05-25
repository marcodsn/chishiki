import type { Metadata } from "next";
import { Inter as FontSans } from "next/font/google";
// import { Montserrat as FontSans } from "next/font/google";
import "@/app/globals.css";
import { ThemeProvider } from "@/components/theme-provider"

import { cn } from "@/lib/utils"

const fontSans = FontSans({
    subsets: ["latin"],
    variable: "--font-sans",
})

export const metadata: Metadata = {
    title: "Chishiki",
    description: "A document search engine",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <div lang="en" suppressHydrationWarning>
            <div className={cn(
                "h-screen max-h-screen min-w-screen bg-background font-sans antialiased",
                fontSans.variable
            )}>
                <ThemeProvider
                    attribute="class"
                    defaultTheme="system"
                    enableSystem
                    disableTransitionOnChange
                >
                    {children}
                </ThemeProvider>
            </div>
        </div>
    );
}
