// components/MobileDrawerButton.tsx
import React from "react";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";

interface MobileDrawerButtonProps {
  children: React.ReactNode;
}

export const MobileDrawerButton: React.FC<MobileDrawerButtonProps> = ({ children }) => {
  return (
    <Drawer>
      <DrawerTrigger asChild>
        <Button variant="outline" size="icon" className="md:hidden">
          <Settings className="w-4 h-4" />
          <span className="sr-only">Open sidebar</span>
        </Button>
      </DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>Settings</DrawerTitle>
          <DrawerDescription>Configure advanced search settings</DrawerDescription>
        </DrawerHeader>
        <div className="flex flex-col space-y-4 p-4 pb-8">{children}</div>
      </DrawerContent>
    </Drawer>
  );
};
