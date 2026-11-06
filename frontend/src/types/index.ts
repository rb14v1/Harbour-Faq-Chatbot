export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  date_joined: string;
}

export interface FAQEntry {
  id: number;
  question: string;
  answer: string;
  created_at: string;
  updated_at: string;
}

export interface MatchedFAQ {
  id: number;
  question: string;
  answer: string;
  score: number;
}

export interface AskResponse {
  answer: string;
  matched_faqs: MatchedFAQ[];
}

export interface ChatLog {
  id: number;
  question_asked: string;
  generated_answer: string;
  matched_faq_ids: number[];
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
