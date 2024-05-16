import React, { createContext, useReducer, useContext, ReactNode } from 'react';

interface SettingsState {
  windowSize: number;
  k: number;
  denseWeight: number;
  highlightQuery: boolean;
}

interface SettingsContextProps {
  state: SettingsState;
  dispatch: React.Dispatch<any>;
}

const initialState: SettingsState = {
  windowSize: 128,
  k: 30,
  denseWeight: 0.7,
  highlightQuery: false,
};

const SettingsContext = createContext<SettingsContextProps | undefined>(undefined);

function settingsReducer(state: SettingsState, action: any): SettingsState {
  switch (action.type) {
    case 'SET_FIELD':
      return { ...state, [action.field]: action.value };
    default:
      return state;
  }
}

export const SettingsProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(settingsReducer, initialState);

  return (
    <SettingsContext.Provider value={{ state, dispatch }}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};