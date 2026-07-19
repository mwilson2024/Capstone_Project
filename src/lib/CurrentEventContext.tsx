import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useAuth } from "./AuthContext";

type CurrentEventValue = {
  eventId: number | null;
  eventName: string | null;
  setCurrentEvent: (id: number, name?: string | null) => void;
  clearCurrentEvent: () => void;
};

const CurrentEventContext = createContext<CurrentEventValue | null>(null);

export function CurrentEventProvider({ children }: { children: React.ReactNode }) {
  const { loggedIn } = useAuth();
  const [eventId, setEventId] = useState<number | null>(null);
  const [eventName, setEventName] = useState<string | null>(null);

  useEffect(() => {
    setEventId(null);
    setEventName(null);
  }, [loggedIn]);

  const value = useMemo<CurrentEventValue>(
    () => ({
      eventId,
      eventName,
      setCurrentEvent: (id, name = null) => {
        setEventId(id);
        setEventName(name);
      },
      clearCurrentEvent: () => {
        setEventId(null);
        setEventName(null);
      },
    }),
    [eventId, eventName]
  );

  return (
    <CurrentEventContext.Provider value={value}>
      {children}
    </CurrentEventContext.Provider>
  );
}

export function useCurrentEvent() {
  const ctx = useContext(CurrentEventContext);
  if (!ctx) throw new Error("useCurrentEvent must be used within a CurrentEventProvider");
  return ctx;
}
