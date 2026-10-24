import { create } from "zustand";

type AppState = {
  sidebarOpen: boolean;
  favoriteHeroIds: number[];
  toggleSidebar: () => void;
  toggleFavorite: (id: number) => void;
};

const stored = JSON.parse(localStorage.getItem("aov-favorites") ?? "[]") as number[];

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: false,
  favoriteHeroIds: stored,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleFavorite: (id) => set((state) => {
    const next = state.favoriteHeroIds.includes(id)
      ? state.favoriteHeroIds.filter((item) => item !== id)
      : [...state.favoriteHeroIds, id];
    localStorage.setItem("aov-favorites", JSON.stringify(next));
    return { favoriteHeroIds: next };
  }),
}));

