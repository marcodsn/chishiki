import React, { useState } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { SettingsIcon, X, FolderIcon, BrainCogIcon, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { useSettings } from '@/contexts/SettingsContext';
import { Inter as FontSans } from "next/font/google";

import { cn } from "@/lib/utils"

const fontSans = FontSans({
  subsets: ["latin"],
  variable: "--font-sans",
})

interface SidebarProps {
  onScreenChange: (screen: string) => void;
  activeScreen: string;
  handleSearch: (e: React.FormEvent) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onScreenChange, activeScreen, handleSearch }) => {
  const { state, dispatch } = useSettings();
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [newTag, setNewTag] = useState<string>('');

  const blur = (event: React.MouseEvent<HTMLButtonElement>) => event.currentTarget.blur();

  const handleIconClick = (section: string, event: React.MouseEvent<HTMLButtonElement>) => {
    if (section === 'settings') {
      setExpandedSection(section === expandedSection ? null : section);
    } else {
      onScreenChange(section);
    }
    blur(event);
  };

  const isActiveScreen = (section: string) => activeScreen === section;

  const handleAddTag = () => {
    if (newTag.trim() !== '') {
      dispatch({ type: 'ADD_TAG', tag: newTag.trim() });
      setNewTag('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    dispatch({ type: 'REMOVE_TAG', tag });
  };

  const handleFormSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    handleAddTag();
  };

  const handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleAddTag();
    }
  };

  const handleInputKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleSearch(event as unknown as React.FormEvent); // Call handleSearch on Enter key press
    }
  };

  return (
    <TooltipProvider>
      <div className="flex md:flex-row justify-center bg-background h-full">
        <div className="flex flex-col justify-between items-center h-full py-3 w-16 border-r">
          <div className="flex flex-col items-center w-fit p-1 border rounded-xl bg-muted/50">
            <Tooltip delayDuration={50}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={`text-muted-foreground rounded-lg mb-2 bg-muted/50 hover:bg-muted ${isActiveScreen('ml_search') ? 'bg-background hover:bg-background text-foreground' : ''}`}
                  onClick={(e) => handleIconClick('ml_search', e)}
                >
                  <BrainCogIcon className="size-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={5}>
                <p>ML Search</p>
              </TooltipContent>
            </Tooltip>
            <Tooltip delayDuration={50}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={`text-muted-foreground rounded-lg bg-muted/50 hover:bg-muted ${isActiveScreen('file_manager') ? 'bg-background hover:bg-background text-foreground' : ''}`}
                  onClick={(e) => handleIconClick('file_manager', e)}
                >
                  <FolderIcon className="size-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={5}>
                <p>File Manager</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <Tooltip delayDuration={50}>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className={`rounded-lg`}
                onClick={(e) => handleIconClick('settings', e)}
              >
                <SettingsIcon className="size-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={5}>
              <p>Settings</p>
            </TooltipContent>
          </Tooltip>
        </div>
        {expandedSection && (
          <div className="flex-1 bg-background w-96 border-r h-full">
            <ScrollArea className="h-full">
              <div className="p-4 pt-6">
                <div className="flex justify-between items-center pb-4 pl-2">
                  <h2 className="text-lg font-semibold capitalize">{expandedSection.replace('_', ' ')}</h2>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="rounded-lg"
                    onClick={() => setExpandedSection(null)}
                  >
                    <X className="size-5" />
                  </Button>
                </div>
                {expandedSection === 'settings' && (
                  <form className="grid w-full items-start gap-6 overflow-auto" onSubmit={handleFormSubmit}>
                    <fieldset className="grid gap-6 rounded-lg border p-4 bg-muted/40">
                      <legend className="-ml-1 px-1 text-sm font-medium">
                        ML Search
                      </legend>
                      <div className="grid gap-3">
                        <Label htmlFor="windowSize">Window Size</Label>
                        <Select onValueChange={(value) => dispatch({ type: 'SET_FIELD', field: 'windowSize', value: Number(value) })}>
                          <SelectTrigger>
                            <SelectValue placeholder={state.windowSize}></SelectValue>
                          </SelectTrigger>
                          <SelectContent className={cn("font-sans", fontSans.variable)}>
                            <SelectItem value="128">128</SelectItem>
                            <SelectItem value="256">256</SelectItem>
                            <SelectItem value="512">512</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="grid gap-3">
                        <Label htmlFor="k">Number of results (K)</Label>
                        <Input
                          id="k"
                          type="number"
                          value={state.k}
                          onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'k', value: Number(e.target.value) })}
                          onKeyDown={handleInputKeyPress}
                        />
                      </div>
                      <div className="grid gap-3">
                        <Label htmlFor="denseWeight">Dense Weight</Label>
                        <Input
                          id="denseWeight"
                          type="number"
                          step="0.1"
                          value={state.denseWeight}
                          onChange={(e) => dispatch({ type: 'SET_FIELD', field: 'denseWeight', value: Number(e.target.value) })}
                          onKeyDown={handleInputKeyPress}
                        />
                      </div>
                      <div className="flex gap-3">
                        <Label htmlFor="highlightQuery">Highlight Query</Label>
                        <Checkbox id="highlightQuery"
                          checked={state.highlightQuery}
                          onCheckedChange={(e) => dispatch({ type: 'SET_FIELD', field: 'highlightQuery', value: e })}
                        />
                      </div>
                    </fieldset>
                    <fieldset className="grid gap-0 rounded-lg border p-4 bg-muted/40">
                      <legend className="-ml-1 px-1 text-sm font-medium">
                        Metadata Filters
                      </legend>
                      <div className="flex gap-3 mb-3">
                        <Input
                          id="newTag"
                          type="text"
                          value={newTag}
                          onChange={(e) => setNewTag(e.target.value)}
                          onKeyDown={handleKeyPress}
                          placeholder="Add a tag"
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-lg"
                          onClick={handleAddTag}
                          type="button" // Ensure this button does not submit the form
                        >
                          <Plus className="h-[1.2rem] w-[1.2rem]" />
                        </Button>
                      </div>
                      <div className="grid gap-3">
                        {state.tags && state.tags.map((tag, index) => (
                          <div key={index} className="flex justify-between items-center p-2 py-1 border rounded-lg bg-muted/20">
                            <span className='text-sm'>{tag}</span>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="rounded-lg hover:bg-transparent"
                              onClick={() => handleRemoveTag(tag)}
                            >
                              <X className="h-[1rem] w-[1rem]" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </fieldset>
                  </form>
                )}
              </div>
            </ScrollArea>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
};

export default Sidebar;
