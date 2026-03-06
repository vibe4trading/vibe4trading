"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { NewRunProvider } from "./NewRunProvider";
import { SiteHeader } from "./SiteHeader";

export function RouteWrapper({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isHome = pathname === "/";

    useEffect(() => {
        if (isHome) {
            document.body.classList.add("home-body");
        } else {
            document.body.classList.remove("home-body");
        }
    }, [isHome]);

    return (
        <NewRunProvider>
            <div className={isHome ? "home-canvas" : "canvas"}>
                <SiteHeader isHome={isHome} />
                {children}
            </div>
        </NewRunProvider>
    );
}
