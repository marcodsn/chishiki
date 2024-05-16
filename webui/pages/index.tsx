import React, { useReducer, useCallback } from 'react';
import DefaultLayout from '@/components/layout/default-layout';
import { ModeToggle } from '@/components/mode-toggle';
import { ModernSearchBar } from '@/components/modern-search-bar';
import { SearchResults } from '@/components/search-results';
import { FileManagerProvider, useFileManager } from '@/contexts/FileManagerContext';
import { FileManager } from '@/components/file-manager';
import Sidebar from '@/components/sidebar';
import { Separator } from '@/components/ui/separator';
import Logo from '@/components/logo';
import { ScrollArea } from "@/components/ui/scroll-area";
import { SettingsProvider, useSettings } from '@/contexts/SettingsContext';

interface SearchResult {
  text: string;
  doc_path: string;
  scores: number[];
}

interface State {
  query: string;
  results: SearchResult[];
  timeTaken: number | null;
  activeScreen: string;
}

const initialState: State = {
  query: '',
  results: [],
  timeTaken: null,
  activeScreen: 'file_manager',
};

function reducer(state: State, action: any): State {
  switch (action.type) {
    case 'SET_FIELD':
      return { ...state, [action.field]: action.value };
    case 'SET_RESULTS':
      return { ...state, results: action.results, timeTaken: action.timeTaken };
    case 'SWITCH_SCREEN':
      return { ...state, activeScreen: action.screen };
    default:
      return state;
  }
}

function HomeContent() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { state: settingsState } = useSettings();
  const { currentPath } = useFileManager();

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const startTime = performance.now();

      // Automatically switch to the 'ml_search' screen when search is initiated
      dispatch({ type: 'SWITCH_SCREEN', screen: 'ml_search' });

      const response = await fetch('/api/proxy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          // action: state.activeScreen === 'ml_search' ? 'ml_search' : 'search_by_metadata',
          action: 'ml_search',
          query: state.query,
          window_size: settingsState.windowSize,
          k: settingsState.k,
          dense_weight: settingsState.denseWeight,
          sparse_weight: 1 - settingsState.denseWeight,
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
  }, [state.query, state.activeScreen, settingsState]);

  const handleChange = useCallback((field: string, value: any) => {
    dispatch({ type: 'SET_FIELD', field, value });
  }, []);

  const handleScreenChange = useCallback((screen: string) => {
    dispatch({ type: 'SWITCH_SCREEN', screen });
  }, []);

  return (
    <DefaultLayout>
      <main className="flex flex-col w-full h-full">
        <div className="flex justify-between items-center p-4 md:p-0">
          <div className="md:hidden">
            {/* <Logo className='size-5 ml-0.5' /> */}
            <p className="text-lg font-semibold p-1">chishiki</p>
          </div>
          <div className="md:hidden">
            <ModeToggle />
          </div>
        </div>
        <div className="h-fit w-full">
          <div className="h-16 flex flex-row w-full justify-between items-center">
            <div className='min-w-16 h-full flex justify-center items-center hidden md:flex border-r'>
              <Logo className="size-5" />
            </div>
            {/* <div className="flex justify-center items-center p-4 md:py-2 w-full"> */}
            <div className="flex justify-between items-center p-4 md:py-2 w-full">
              <p className="hidden md:block text-lg font-semibold p-1">chishiki</p>
              <div className="flex items-center md:w-1/2 w-full">
                <ModernSearchBar
                  query={state.query}
                  setQuery={(query) => handleChange('query', query)}
                  onSearch={handleSearch}
                  className="w-full"
                />
                <div className="hidden md:block pl-4">
                  <ModeToggle />
                </div>
              </div>
            </div>
          </div>
          <Separator />
        </div>
        <div className="flex w-full h-full overflow-hidden">
          <div className="hidden md:block">
            <Sidebar onScreenChange={handleScreenChange} activeScreen={state.activeScreen} />
          </div>
          <div className="flex flex-col w-full">
            {state.activeScreen === 'ml_search' && (
              // <div className="flex flex-col w-full py-6 px-4">
              <ScrollArea className="max-h-full px-6">
                <SearchResults
                  results={state.results}
                  timeTaken={state.timeTaken}
                  query={state.query}
                  highlightQuery={settingsState.highlightQuery}
                />
              </ScrollArea>
              // </div>
            )}
            {state.activeScreen === 'file_manager' && (
              <ScrollArea className="max-h-full px-6">
                <FileManager />
              </ScrollArea>
            )}
          </div>
        </div>
      </main>
    </DefaultLayout>
  );
}

export default function Home() {
  return (
    <FileManagerProvider>
      <SettingsProvider>
        <HomeContent />
      </SettingsProvider>
    </FileManagerProvider>
  );
}