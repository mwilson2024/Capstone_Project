import { createContext, useContext, useMemo, useState } from "react";
import { palettes, ThemeColors, ThemeName } from "./colors";

type ThemeContextValue = {
  themeName: ThemeName;
  colors: ThemeColors;
  isDark: boolean;
  setDark: (value: boolean) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeName, setThemeName] = useState<ThemeName>("light");

  const value = useMemo<ThemeContextValue>(
    () => ({
      themeName,
      colors: palettes[themeName],
      isDark: themeName === "dark",
      setDark: (v) => setThemeName(v ? "dark" : "light"),
    }),
    [themeName]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
