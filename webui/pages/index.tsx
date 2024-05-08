// pages/index.tsx
import React, { useReducer, useCallback } from 'react';
import DefaultLayout from '@/components/layout/default-layout';
import { ModeToggle } from '@/components/mode-toggle';
import { SearchBar } from '@/components/search-bar';
import { ModernSearchBar } from '@/components/modern-search-bar';
import { SearchResults } from '@/components/search-results';
import AdvancedSettings from '@/components/advanced-settings';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from "@/components/ui/separator";
import { FileManagerProvider } from '@/contexts/FileManagerContext';
import { FileManager } from '@/components/file-manager';

interface SearchResult {
  text: string;
  doc_path: string;
  scores: number[];
}

interface State {
  query: string;
  results: SearchResult[];
  windowSize: number;
  k: number;
  denseWeight: number;
  timeTaken: number | null;
  highlightQuery: boolean;
  activeTab: string;
}

const initialState: State = {
  query: '',
  results: [],
  windowSize: 128,
  k: 30,
  denseWeight: 0.7,
  timeTaken: null,
  highlightQuery: false,
  activeTab: 'files',
};

function reducer(state: State, action: any): State {
  switch (action.type) {
    case 'SET_FIELD':
      return { ...state, [action.field]: action.value };
    case 'SET_RESULTS':
      return { ...state, results: action.results, timeTaken: action.timeTaken };
    case 'SWITCH_TAB':
      return { ...state, activeTab: action.tab };
    default:
      return state;
  }
}

export default function Home() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const currentPath = "/data/p_gutenberg/";

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    dispatch({ type: 'SWITCH_TAB', tab: 'search' });

    try {
      const startTime = performance.now();

      const response = await fetch('/api/proxy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'search',
          query: state.query,
          window_size: state.windowSize,
          k: state.k,
          dense_weight: state.denseWeight,
          sparse_weight: 1 - state.denseWeight,
          path: currentPath,
        }),
      });

      const endTime = performance.now();
      const timeTaken = endTime - startTime;

      if (response.ok) {
        console.log('Search results fetched successfully');
        const data = await response.json();

        if (Array.isArray(data.passages)) {
          dispatch({
            type: 'SET_RESULTS',
            results: data.passages.map(({ text, doc_path, scores }: any) => ({
              text,
              doc_path,
              scores,
            })),
            timeTaken,
          });
        } else {
          console.error('Invalid response format: data.results is not an array');
          dispatch({ type: 'SET_RESULTS', results: [], timeTaken: null });
        }
      } else {
        throw new Error('Error fetching search results');
      }
    } catch (error) {
      console.error('Error fetching search results:', error);
    }
  }, [state.query, state.windowSize, state.k, state.denseWeight]);

  const handleChange = useCallback((field: string, value: any) => {
    dispatch({ type: 'SET_FIELD', field, value });
  }, []);

  // max-w-4xl
  return (
    <FileManagerProvider>
      <DefaultLayout>
        <main className="flex flex-col w-full items-center">
          <div className="flex w-full justify-between items-center max-w-4xl py-2">
            <div className="flex items-center p-2 px-4">
              <h1 className="text-xl font-semibold">chishiki</h1>
            </div>
            <div className="flex justify-end p-2 px-4">
              <ModeToggle />
            </div>
          </div>
          <Separator />
          <div className="flex flex-col w-full max-w-4xl mt-6 px-4">
            <ModernSearchBar
              query={state.query}
              setQuery={(query) => handleChange('query', query)}
              onSearch={handleSearch}
              className="w-full"
            />
            <Tabs defaultValue={state.activeTab} className="flex-grow mt-6">
              <TabsList className="w-full">
                <TabsTrigger value="search" className="w-full">ML Search</TabsTrigger>
                <TabsTrigger value="files" className="w-full">File Manager</TabsTrigger>
              </TabsList>
              <TabsContent value="search" className="py-4">
                <AdvancedSettings
                  windowSize={state.windowSize}
                  setWindowSize={(value) => handleChange('windowSize', value)}
                  k={state.k}
                  setK={(value) => handleChange('k', value)}
                  denseWeight={state.denseWeight}
                  setDenseWeight={(value) => handleChange('denseWeight', value)}
                  highlightQuery={state.highlightQuery}
                  setHighlightQuery={(value) => handleChange('highlightQuery', value)}
                />
                <Separator className="my-4" />
                <SearchResults
                  results={state.results}
                  timeTaken={state.timeTaken}
                  query={state.query}
                  highlightQuery={state.highlightQuery}
                />
              </TabsContent>
              <TabsContent value="files" className="py-4">
                <FileManager />
              </TabsContent>
            </Tabs>
          </div>
        </main>
      </DefaultLayout>
    </FileManagerProvider>
  );
}