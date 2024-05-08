// contexts/CurrentPathContext.tsx
import React, { createContext, useContext, useState, ReactNode } from 'react';

interface CurrentPathContextType {
  currentPath: string;
  setCurrentPath: (path: string) => void;
}

const CurrentPathContext = createContext<CurrentPathContextType | undefined>(undefined);

export const CurrentPathProvider: React.FC<{children: ReactNode}> = ({ children }) => {
  const [currentPath, setCurrentPath] = useState('/data');

  return (
    <CurrentPathContext.Provider value={{ currentPath, setCurrentPath }}>
      {children}
    </CurrentPathContext.Provider>
  );
};

export const useCurrentPath = () => {
  const context = useContext(CurrentPathContext);
  if (!context) {
    throw new Error('useCurrentPath must be used within a CurrentPathProvider');
  }
  return context;
};

export default CurrentPathContext;
