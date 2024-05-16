import { useState } from "react";
import { ChevronsUpDown, Download, FileText, SearchSlashIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { openFile, downloadFile, openFileText } from "@/lib/utils";

interface SearchResult {
  text: string;
  doc_path: string;
  scores: number[];
}

interface GroupedResults {
  [key: string]: SearchResult[];
}

interface SearchResultsProps {
  results: SearchResult[];
  timeTaken: number | null;
  query: string;
  highlightQuery: boolean;
  className?: string;
}

interface SimilarDocs {
  doc_path: string;
  score: number;
}

export const SearchResults: React.FC<SearchResultsProps> = ({ results, timeTaken, query, highlightQuery, className }) => {
  const [significantDigits, setSignificantDigits] = useState(4);
  const [loadingFiles, setLoadingFiles] = useState<{ [key: string]: boolean }>({});
  const [similarDocs, setSimilarDocs] = useState<{ [key: string]: SimilarDocs[] }>({});

  // Group search results by doc_path
  const groupedResults = results.reduce((acc, result) => {
    const { text, doc_path, scores } = result;
    if (!acc[doc_path]) {
      acc[doc_path] = [];
    }
    acc[doc_path].push({ text, doc_path, scores });
    return acc;
  }, {} as GroupedResults);

  // Sort search results within each group by hybrid score (scores[2])
  Object.values(groupedResults).forEach((group) => {
    group.sort((a, b) => b.scores[2] - a.scores[2]);
  });

  const highlightText = (text: string) => {
    if (!highlightQuery) return text;

    const queryWords = query.split(" ");
    const regex = new RegExp(`(${queryWords.join("|")})`, "gi");
    return text.replace(regex, "<mark class='text-background bg-foreground'>$1</mark>");
  };

  const findSimilarDocs = async (docPath: string, k: number = 10, threshold: number = 0.3) => {
    try {
      const response = await fetch('/api/proxy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'search_similar_docs',
          doc_path: docPath,
          k,
          threshold,
        }),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = await response.json();
      // console.log('Similar documents:', data.similar_docs[0].doc_path);
      // console.log('Similar documents:', data.similar_docs[0].similarity_score);
      setSimilarDocs((prevState) => ({
        ...prevState,
        [docPath]: data.similar_docs.map(({ doc_path, similarity_score }: any) => ({
          doc_path,
          score: similarity_score,
        })),
      }));
    } catch (error) {
      console.error('Error finding similar documents:', error);
    }
  };

  return (
    <TooltipProvider>
      <div className={`${className ? className : ''} space-y-4 max-w-full py-6`}>
        {timeTaken !== null && (
          <div className="text-sm text-muted-foreground px-4">
            Took: {timeTaken.toFixed(2)} ms
          </div>
        )}
        {results.length === 0 ? (
          <div className="text-sm text-muted-foreground px-4">
            No results found.
          </div>
        ) : (
          Object.entries(groupedResults).map(([doc_path, results]) => (
            <Collapsible key={doc_path} className="space-y-2 border rounded-lg shadow-sm p-4 bg-background">
              <div className="flex items-center justify-between space-x-4">
                <div className="flex items-center space-x-2">
                  <h4
                    className="text-sm font-semibold cursor-pointer hover:underline"
                    onClick={() => openFile(doc_path, (loading) => setLoadingFiles((prevState) => ({ ...prevState, [doc_path]: loading })))}
                  >
                    {doc_path}
                  </h4>
                  {loadingFiles[doc_path] && (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-foreground border-t-transparent"></div>
                  )}
                </div>
                <div className="flex space-x-2">
                  <Tooltip delayDuration={50}>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-9 p-0"
                        onClick={() => findSimilarDocs(doc_path)}
                      >
                        <SearchSlashIcon className="h-4 w-4" />
                        <span className="sr-only">Search similar docs</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" sideOffset={5}>
                      <p>Find Similar Docs</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip delayDuration={50}>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-9 p-0"
                        onClick={() => downloadFile(doc_path)}
                      >
                        <Download className="h-4 w-4" />
                        <span className="sr-only">Download</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" sideOffset={5}>
                      <p>Download</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip delayDuration={50}>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-9 p-0"
                        onClick={() => openFileText(doc_path)}
                      >
                        <FileText className="h-4 w-4" />
                        <span className="sr-only">Open Text</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" sideOffset={5}>
                      <p>Open Text</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip delayDuration={50}>
                    <TooltipTrigger asChild>
                    <CollapsibleTrigger asChild>
                      <Button variant="ghost" size="sm" className="w-9 p-0">
                        <ChevronsUpDown className="h-4 w-4" />
                        <span className="sr-only">More Results</span>
                      </Button>
                    </CollapsibleTrigger>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" sideOffset={5}>
                      <p>More Results</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              </div>
              {results.length > 0 && (
                <div className="px-4 py-3 bg-muted/50 rounded-md">
                  <p className="text-sm" dangerouslySetInnerHTML={{ __html: highlightText(results[0].text) }}></p>
                  <div className="text-xs text-muted-foreground mt-2">
                    <p>
                      Dense Score: {results[0].scores[0].toFixed(significantDigits)}, Lexical Score:{" "}
                      {results[0].scores[1].toFixed(significantDigits)}, Hybrid Score:{" "}
                      {results[0].scores[2].toFixed(significantDigits)}
                    </p>
                  </div>
                </div>
              )}
              <CollapsibleContent className="space-y-2">
                {results.slice(1).map((result, index) => (
                  <div key={index} className="px-4 py-3 bg-muted/50 rounded-md">
                    <p className="text-sm" dangerouslySetInnerHTML={{ __html: highlightText(result.text) }}></p>
                    <div className="text-xs text-muted-foreground mt-2">
                      <p>
                        Dense Score: {result.scores[0].toFixed(significantDigits)}, Lexical Score:{" "}
                        {result.scores[1].toFixed(significantDigits)}, Hybrid Score:{" "}
                        {result.scores[2].toFixed(significantDigits)}
                      </p>
                    </div>
                  </div>
                ))}
              </CollapsibleContent>
              {similarDocs[doc_path] && (
                <div className="mt-4">
                  <h4 className="text-sm font-semibold mb-2">Similar Documents:</h4>
                  <div className="flex flex-wrap space-x-2">
                    {similarDocs[doc_path].map((similarDoc, index) => (
                      <Tooltip delayDuration={50}>
                        <TooltipTrigger asChild>
                          <div key={index} className="px-2 py-1.5 bg-muted/50 w-fit rounded-md mb-2">
                            <div className="flex items-center space-x-2 text-muted-foreground">
                              <p
                                className="text-sm font-medium cursor-pointer hover:underline"
                                onClick={() => openFile(similarDoc.doc_path, (loading) => setLoadingFiles((prevState) => ({ ...prevState, [similarDoc.doc_path]: loading })))}
                              >
                                {similarDoc.doc_path.split('/').pop()}
                              </p>
                              {loadingFiles[similarDoc.doc_path] && (
                                <div className="animate-spin rounded-full h-4 w-4 border-2 border-foreground border-t-transparent"></div>
                              )}
                            </div>
                            {/* <p>Score: {similarDoc.score.toFixed(significantDigits)}</p> */}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent sideOffset={5}>
                          <p>{similarDoc.doc_path}</p>
                          <p>Distance: {similarDoc.score.toFixed(significantDigits)}</p>
                        </TooltipContent>
                      </Tooltip>
                    ))}
                  </div>
                </div>
              )}
            </Collapsible>
          ))
        )}
      </div>
    </TooltipProvider>
  );
};
