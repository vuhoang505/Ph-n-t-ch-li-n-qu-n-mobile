import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import type { Hero } from "../types";

export function useHeroes() {
  return useQuery({
    queryKey: ["heroes"],
    queryFn: () => api<{ items: Hero[]; total: number }>("/heroes"),
    staleTime: 5 * 60_000,
  });
}

