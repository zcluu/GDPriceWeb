import { create } from "zustand";
import { clearToken, getToken, setToken } from "./api/client";

type AuthState = {
  token: string | null;
  isAuthed: boolean;
  signIn: (token: string) => void;
  signOut: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  token: getToken(),
  isAuthed: Boolean(getToken()),
  signIn: (token) => {
    setToken(token);
    set({ token, isAuthed: true });
  },
  signOut: () => {
    clearToken();
    set({ token: null, isAuthed: false });
  }
}));

