import { useCallback } from "react";

const STORAGE_KEY = "v4t_tour_completed";

function getCompletedTours(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as string[];
  } catch {
    return [];
  }
}

function setCompletedTours(tours: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tours));
  } catch {
    // Safari private mode or quota exceeded — fail silently
  }
}

export function useTourPersistence(tourId: string) {
  const hasCompleted = useCallback(() => {
    return getCompletedTours().includes(tourId);
  }, [tourId]);

  const markCompleted = useCallback(() => {
    const tours = getCompletedTours();
    if (!tours.includes(tourId)) {
      setCompletedTours([...tours, tourId]);
    }
  }, [tourId]);

  const reset = useCallback(() => {
    const tours = getCompletedTours();
    setCompletedTours(tours.filter((id) => id !== tourId));
  }, [tourId]);

  return { hasCompleted, markCompleted, reset };
}
