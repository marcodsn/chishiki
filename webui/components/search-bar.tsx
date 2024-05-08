import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface SearchBarProps {
  query: string;
  setQuery: (query: string) => void;
  onSearch: (e: React.FormEvent) => void;
  className?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  query,
  setQuery,
  onSearch,
  className,
}) => {
  return (
    <form onSubmit={onSearch} className={`${className ? className : ''} flex items-center w-full`}>
      <Input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
        className="flex-grow"
      />
      <Button type="submit" className="ml-4">
        Search
      </Button>
    </form>
  );
};

// import { Input } from "@/components/ui/input";
// import { Button } from "@/components/ui/button";
// import {
//   Command,
//   CommandEmpty,
//   CommandGroup,
//   CommandInput,
//   CommandItem,
//   CommandList,
// } from "@/components/ui/command";
// import { useEffect, useState } from "react";
// import { File, Folder, Download } from "lucide-react";

// interface SearchBarProps {
//   query: string;
//   setQuery: (query: string) => void;
//   onSearch: (e: React.FormEvent) => void;
//   onSuggestionClick: (path: string) => void;
//   className?: string;
// }

// export const SearchBar: React.FC<SearchBarProps> = ({
//   query,
//   setQuery,
//   onSearch,
//   onSuggestionClick,
//   className,
// }) => {
//   const [suggestions, setSuggestions] = useState<any[]>([]);
//   const [open, setOpen] = useState(false);

//   useEffect(() => {
//     const fetchSuggestions = async () => {
//       try {
//         const response = await fetch("/api/proxy", {
//           method: "POST",
//           body: JSON.stringify({ action: "metadata_search", tags: [], path: "/", filename: query }),
//           headers: {
//             "Content-Type": "application/json",
//           },
//         });

//         if (response.ok) {
//           const data = await response.json();
//           setSuggestions(data.results);
//         }
//       } catch (error) {
//         console.error("Error fetching suggestions:", error);
//       }
//     };

//     if (open && query) {
//       fetchSuggestions();
//     }
//   }, [open, query]);

//   return (
//     <Command className={`${className ? className : ""} rounded-lg border shadow-md`}>
//       <CommandInput
//         value={query}
//         onValueChange={setQuery}
//         placeholder="Search..."
//         onKeyDown={(e) => {
//           if (e.key === "Enter") {
//             onSearch(e as any);
//           }
//         }}
//         onFocus={() => setOpen(true)}
//         onBlur={() => setOpen(false)}
//       />
//       {/* <CommandList className="absolute z-10" open={open}> */}
//       <CommandList className="absolute z-10 hidden">
//         <CommandEmpty>No results found.</CommandEmpty>
//         <CommandGroup heading="Suggestions">
//           {suggestions.map((suggestion) => (
//             <CommandItem
//               key={suggestion.filename || suggestion.dirname}
//               onSelect={() => {
//                 onSuggestionClick(suggestion.path);
//               }}
//             >
//               {suggestion.filename ? (
//                 <File className="mr-2 h-4 w-4" />
//               ) : (
//                 <Folder className="mr-2 h-4 w-4" />
//               )}
//               <span>{suggestion.filename || suggestion.dirname}</span>
//               {suggestion.filename && (
//                 <Button
//                   variant="ghost"
//                   size="sm"
//                   className="ml-auto"
//                   onClick={(e) => {
//                     e.stopPropagation();
//                     // Implement download logic here
//                   }}
//                 >
//                   <Download className="h-4 w-4" />
//                 </Button>
//               )}
//             </CommandItem>
//           ))}
//         </CommandGroup>
//       </CommandList>
//     </Command>
//   );
// };
