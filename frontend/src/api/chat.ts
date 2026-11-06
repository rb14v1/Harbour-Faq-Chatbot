import { apiClient } from "./client";
import type { AskResponse, ChatLog, Paginated } from "../types";

export function askQuestion(question: string) {
  return apiClient.post<AskResponse>("/ask/", { question });
}

export function listChatLogs() {
  return apiClient.get<Paginated<ChatLog>>("/chat-logs/");
}
