import * as SecureStore from "expo-secure-store";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Platform } from "react-native";
import { API_CONFIGURED, onUnauthorized, setToken } from "./api";

const TOKEN_KEY = "auth_token";
const PROFILE_KEY = "auth_profile";
const SIGNED_OUT = "__signed_out__";
const web = () => (globalThis as any).localStorage;
let pendingStorageWrite = Promise.resolve();

const storage = {
  async get(): Promise<string | null> {
    try {
      if (Platform.OS === "web") return web()?.getItem(TOKEN_KEY) ?? null;
      return await SecureStore.getItemAsync(TOKEN_KEY);
    } catch (e) {
      console.warn("Token read failed:", e);
      return null;
    }
  },
  set(value: string): Promise<void> {
    pendingStorageWrite = pendingStorageWrite.then(async () => {
      try {
        if (Platform.OS === "web") web()?.setItem(TOKEN_KEY, value);
        else await SecureStore.setItemAsync(TOKEN_KEY, value);
      } catch (e) {
        console.warn("Token write failed:", e);
      }
    });
    return pendingStorageWrite;
  },
};

export type AuthUser = {
  user_id: number;
  user_name: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  role: string;
};

const profileStorage = {
  async get(): Promise<AuthUser | null> {
    try {
      const value =
        Platform.OS === "web"
          ? web()?.getItem(PROFILE_KEY)
          : await SecureStore.getItemAsync(PROFILE_KEY);
      return value ? (JSON.parse(value) as AuthUser) : null;
    } catch {
      return null;
    }
  },
  async set(user: AuthUser | null): Promise<void> {
    try {
      if (Platform.OS === "web") {
        if (user) web()?.setItem(PROFILE_KEY, JSON.stringify(user));
        else web()?.removeItem(PROFILE_KEY);
      } else if (user) {
        await SecureStore.setItemAsync(PROFILE_KEY, JSON.stringify(user));
      } else {
        await SecureStore.deleteItemAsync(PROFILE_KEY);
      }
    } catch (e) {
      console.warn("Profile storage failed:", e);
    }
  },
};

type AuthContextValue = {
  ready: boolean;
  loggedIn: boolean;
  user: AuthUser | null;
  signIn: (token: string, user?: AuthUser) => Promise<void>;
  signOut: () => Promise<void>;
  setUserProfile: (user: AuthUser) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    onUnauthorized(() => {
      setToken("");
      setLoggedIn(false);
      setUser(null);
      void storage.set(SIGNED_OUT);
      void profileStorage.set(null);
    });

    (async () => {
      const [stored, storedProfile] = await Promise.all([
        storage.get(),
        profileStorage.get(),
      ]);
      const t = API_CONFIGURED && stored !== SIGNED_OUT
        ? stored || process.env.EXPO_PUBLIC_JWT_TOKEN || ""
        : "";
      setToken(t);
      setLoggedIn(t.length > 0);
      setUser(t.length > 0 ? storedProfile : null);
      setReady(true);
    })();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready,
      loggedIn,
      user,
      signIn: async (t, profile) => {
        await Promise.all([
          storage.set(t),
          profile ? profileStorage.set(profile) : Promise.resolve(),
        ]);
        setToken(t);
        setLoggedIn(true);
        if (profile) setUser(profile);
      },
      signOut: async () => {
        setToken("");
        setLoggedIn(false);
        setUser(null);
        await Promise.all([storage.set(SIGNED_OUT), profileStorage.set(null)]);
      },
      setUserProfile: async (profile) => {
        setUser(profile);
        await profileStorage.set(profile);
      },
    }),
    [ready, loggedIn, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
