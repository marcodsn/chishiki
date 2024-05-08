// components/search-results.tsx
import { ChevronsUpDown, Download, Copy, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useState } from "react";

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

export const SearchResults: React.FC<SearchResultsProps> = ({ results, timeTaken, query, highlightQuery, className }) => {
  const [significantDigits, setSignificantDigits] = useState(4);
  const [loadingFiles, setLoadingFiles] = useState<{ [key: string]: boolean }>({});

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
    // return text.replace(regex, "<mark style='background-color: white'>$1</mark>");
    // return text.replace(regex, "<mark>$1</mark>");
    // use tailwind classes for highlighting
    return text.replace(regex, "<mark class='text-background bg-foreground'>$1</mark>");
  };

  const openFile = (docPath: string) => {
    setLoadingFiles((prevState) => ({ ...prevState, [docPath]: true }));

    fetch(`/api/proxy?doc_path=${encodeURIComponent(docPath)}&action=download_file`, {
      method: 'GET',
    })
      .then((response) => {
        if (response.ok) {
          return response.blob();
        }
        throw new Error('Network response was not ok.');
      })
      .then((blob) => {
        const fileExtension = docPath.split('.').pop()?.toLowerCase();
        let mimeType = 'application/octet-stream';

        if (fileExtension === 'pdf') {
          mimeType = 'application/pdf';
        } else if (fileExtension === 'txt') {
          mimeType = 'text/plain';
        } else if (fileExtension === 'jpg' || fileExtension === 'jpeg') {
          mimeType = 'image/jpeg';
        } else if (fileExtension === 'png') {
          mimeType = 'image/png';
        }

        const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }));
        const fileName = docPath.split('/').pop() || '';
        window.open(url, fileName);
      })
      .catch((error) => {
        console.error('There has been a problem with your fetch operation:', error);
      })
      .finally(() => {
        setLoadingFiles((prevState) => ({ ...prevState, [docPath]: false }));
      });
  };

  const downloadFile = (docPath: string) => {
    fetch(`/api/proxy?action=download_file&doc_path=${encodeURIComponent(docPath)}`, {
      method: 'GET',
    })
      .then((response) => {
        if (response.ok) {
          return response.blob();
        }
        throw new Error('Network response was not ok.');
      })
      .then((blob) => {
        const fileExtension = docPath.split('.').pop()?.toLowerCase();
        let mimeType = 'application/octet-stream';

        if (fileExtension === 'pdf') {
          mimeType = 'application/pdf';
        } else if (fileExtension === 'txt') {
          mimeType = 'text/plain';
        } else if (fileExtension === 'jpg' || fileExtension === 'jpeg') {
          mimeType = 'image/jpeg';
        } else if (fileExtension === 'png') {
          mimeType = 'image/png';
        }

        const fileName = docPath.split('/').pop() || '';
        const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }));
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        link.click();
        window.URL.revokeObjectURL(url);
      })
      .catch((error) => {
        console.error('There has been a problem with your fetch operation:', error);
      });
  };

  // const copyFileText = (docPath: string) => {
  //   fetch(`/api/proxy?action=get_doc_text&doc_path=${encodeURIComponent(docPath)}`, {
  //     method: 'GET',
  //   })
  //     .then((response) => response.json())
  //     .then((data) => {
  //       console.log(data);
  //       if (data.doc_text) {
  //         navigator.clipboard.writeText(data.doc_text)
  //           .then(() => {
  //             console.log('Text copied to clipboard');
  //             // Optionally, show a notification to the user that the text has been copied.
  //           })
  //           .catch((err) => console.error('Failed to copy text: ', err));
  //       } else {
  //         throw new Error('Document text not found');
  //       }
  //     })
  //     .catch((error) => {
  //       console.error('There has been a problem with your fetch operation:', error);
  //     });
  // };

  const openFileText = (docPath: string) => {
    fetch(`/api/proxy?action=get_doc_text&doc_path=${encodeURIComponent(docPath)}`, {
      method: 'GET',
    })
    .then((response) => response.json())
    .then((data) => {
      if (data.doc_text) {
        const blob = new Blob([data.doc_text], { type: 'text/plain;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        window.open(url, '_blank'); // Open the text in a new tab
        window.URL.revokeObjectURL(url); // Clean up the blob URL
      } else {
        throw new Error('Document text not found');
      }
    })
    .catch((error) => {
      console.error('There has been a problem with your fetch operation:', error);
    });
  };

  return (
    <div className={`${className ? className : ''} space-y-4 max-w-full`}>
      {timeTaken !== null && (
        <div className="text-sm text-muted-foreground px-4">
          Took: {timeTaken.toFixed(2)} ms
        </div>
      )}
      {Object.entries(groupedResults).map(([doc_path, results]) => (
        <Collapsible key={doc_path} className="space-y-2">
          <div className="flex items-center justify-between space-x-4 px-4">
            <div className="flex items-center space-x-2">
              <h4
                className="text-sm font-semibold cursor-pointer hover:underline"
                onClick={() => openFile(doc_path)}
              >
                {doc_path}
              </h4>
              {loadingFiles[doc_path] && (
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-foreground border-t-transparent"></div>
              )}
            </div>
            <div className="flex space-x-2">
              <Button
                variant="ghost"
                size="sm"
                className="w-9 p-0"
                onClick={() => downloadFile(doc_path)}
              >
                <Download className="h-4 w-4" />
                <span className="sr-only">Download</span>
              </Button>
              {/* <Button
                variant="ghost"
                size="sm"
                className="w-9 p-0"
                onClick={() => copyFileText(doc_path)}
              > */}
              <Button
                variant="ghost"
                size="sm"
                className="w-9 p-0"
                onClick={() => openFileText(doc_path)}
              >
                <FileText className="h-4 w-4" />
                <span className="sr-only">Copy</span>
              </Button>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="w-9 p-0">
                  <ChevronsUpDown className="h-4 w-4" />
                  <span className="sr-only">Toggle</span>
                </Button>
              </CollapsibleTrigger>
            </div>
          </div>
          {results.length > 0 && (
            <div className="px-4 py-3">
              <p className="text-sm" dangerouslySetInnerHTML={{ __html: highlightText(results[0].text) }}></p>
              <div className="text-xs text-muted-foreground">
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
              <div key={index} className="px-4 py-3">
                <p className="text-sm" dangerouslySetInnerHTML={{ __html: highlightText(result.text) }}></p>
                <div className="text-xs text-muted-foreground">
                  <p>
                    Dense Score: {result.scores[0].toFixed(significantDigits)}, Lexical Score:{" "}
                    {result.scores[1].toFixed(significantDigits)}, Hybrid Score:{" "}
                    {result.scores[2].toFixed(significantDigits)}
                  </p>
                </div>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      ))}
    </div>
  );
};
