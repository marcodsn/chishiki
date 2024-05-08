import React, { ReactNode, useState } from "react";

interface SidebarProps {
  children: ReactNode;
}

export const Sidebar: React.FC<SidebarProps> = ({ children }) => {
  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:block border-r bg-background p-4 min-w-60 min-h-screen">
        <div className="flex flex-col space-y-4">{children}</div>
      </aside>
    </>
  );
};
