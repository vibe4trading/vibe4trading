import { useEffect, useRef, useCallback } from "react";
import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import "@/app/tours/tour.css";
import type { DriveStep, Config } from "driver.js";
import { isPrerendering } from "@/app/lib/prerender";

export function useProductTour(
  steps: DriveStep[],
  config?: Partial<Config>
) {
  const driverRef = useRef<ReturnType<typeof driver> | null>(null);

  const start = useCallback(() => {
    if (isPrerendering()) return;

    driverRef.current?.destroy();

    const driverObj = driver({
      ...config,
      steps,
    });

    driverRef.current = driverObj;
    driverObj.drive();
  }, [steps, config]);

  const stop = useCallback(() => {
    driverRef.current?.destroy();
    driverRef.current = null;
  }, []);

  const destroy = useCallback(() => {
    driverRef.current?.destroy();
    driverRef.current = null;
  }, []);

  useEffect(() => {
    return () => {
      driverRef.current?.destroy();
    };
  }, []);

  return { start, stop, destroy };
}
