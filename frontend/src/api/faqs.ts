import { apiClient } from "./client";
import type { FAQEntry, Paginated } from "../types";

export function listFAQs() {
  return apiClient.get<Paginated<FAQEntry>>("/faqs/");
}

export function createFAQ(data: { question: string; answer: string }) {
  return apiClient.post<FAQEntry>("/faqs/", data);
}

export function updateFAQ(id: number, data: { question: string; answer: string }) {
  return apiClient.put<FAQEntry>(`/faqs/${id}/`, data);
}

export function deleteFAQ(id: number) {
  return apiClient.delete(`/faqs/${id}/`);
}
