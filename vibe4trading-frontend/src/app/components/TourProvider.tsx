import * as React from "react";

type TourContextValue = {
  activeTour: string | null;
  startTour: (tourId: string) => void;
  stopTour: () => void;
};

const TourContext = React.createContext<TourContextValue | null>(null);

export function TourProvider({ children }: { children: React.ReactNode }) {
  const [activeTour, setActiveTour] = React.useState<string | null>(null);

  const startTour = React.useCallback((tourId: string) => {
    setActiveTour(tourId);
  }, []);

  const stopTour = React.useCallback(() => {
    setActiveTour(null);
  }, []);

  const contextValue = React.useMemo(
    () => ({ activeTour, startTour, stopTour }),
    [activeTour, startTour, stopTour],
  );

  return (
    <TourContext.Provider value={contextValue}>{children}</TourContext.Provider>
  );
}

export function useTourContext() {
  const context = React.useContext(TourContext);
  if (!context) {
    throw new Error("useTourContext must be used within a TourProvider");
  }
  return context;
}
