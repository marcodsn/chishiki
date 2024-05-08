import React, { useState } from 'react';
import { Search, X } from 'lucide-react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface ModernSearchBarProps {
  query?: string;
  setQuery: (query: string) => void;
  onSearch: (e: React.FormEvent) => void;
  className?: string;
}

export const ModernSearchBar: React.FC<ModernSearchBarProps> = ({
  query,
  setQuery,
  onSearch,
  className,
}) => {
  const clearQuery = () => setQuery('');

  return (
    <form onSubmit={onSearch} className={`${className ? className : ''} flex items-center w-full relative`}>
      <Button type="button" onClick={onSearch} className="absolute left-0 hover:bg-transparent" variant="ghost" size="icon">
        <Search className="h-[1rem] w-[1rem]" />
      </Button>
      <Input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
        className="pl-10 pr-10 flex-grow focus-visible:ring-2"
      />
      {query && (
        <Button type="button" onClick={clearQuery} className="absolute right-0 hover:bg-transparent" variant="ghost" size="icon">
          <X className="h-[1rem] w-[1rem]" />
        </Button>
      )}
    </form>
  );
};