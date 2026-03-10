import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { TourProvider, useTourContext } from "../src/app/components/TourProvider";
import { act } from "react";

describe("TourProvider", () => {
  afterEach(cleanup);

  it("provides default values", () => {
    let contextValue: any;

    function TestComponent() {
      contextValue = useTourContext();
      return null;
    }

    render(
      <TourProvider>
        <TestComponent />
      </TourProvider>
    );

    expect(contextValue.activeTour).toBe(null);
    expect(typeof contextValue.startTour).toBe("function");
    expect(typeof contextValue.stopTour).toBe("function");
  });

  it("startTour sets activeTour", () => {
    let contextValue: any;

    function TestComponent() {
      contextValue = useTourContext();
      return <button onClick={() => contextValue.startTour("test-tour")}>Start</button>;
    }

    render(
      <TourProvider>
        <TestComponent />
      </TourProvider>
    );

    expect(contextValue.activeTour).toBe(null);

    act(() => {
      screen.getByText("Start").click();
    });

    expect(contextValue.activeTour).toBe("test-tour");
  });

  it("stopTour clears activeTour", () => {
    let contextValue: any;

    function TestComponent() {
      contextValue = useTourContext();
      return (
        <>
          <button onClick={() => contextValue.startTour("test-tour")}>Start</button>
          <button onClick={() => contextValue.stopTour()}>Stop</button>
        </>
      );
    }

    render(
      <TourProvider>
        <TestComponent />
      </TourProvider>
    );

    act(() => {
      screen.getByText("Start").click();
    });
    expect(contextValue.activeTour).toBe("test-tour");

    act(() => {
      screen.getByText("Stop").click();
    });
    expect(contextValue.activeTour).toBe(null);
  });

  it("useTourContext throws outside provider", () => {
    function TestComponent() {
      useTourContext();
      return null;
    }

    expect(() => {
      render(<TestComponent />);
    }).toThrow("useTourContext must be used within a TourProvider");
  });
});
