import type { RefObject } from "react";
import type { Extraction, PredictResult, ProcessEvent, ToolCall } from "./predict";
import React from "react";

export interface Message {
  role: "user" | "assistant";
  content: string;
  extraction?: Extraction;
  result?: PredictResult;
  process?: ProcessEvent[];
  toolCalls?: ToolCall[];
  loading?: boolean;
}

export interface UseChatReturn {
  input: string;
  setInput: (value: string) => void;
  messages: Message[];
  loading: boolean;
  bottomRef: RefObject<HTMLDivElement | null>;
  handleSubmit: (e: React.FormEvent) => void;
}

export interface ChatInputProps {
  input: string;
  loading: boolean;
  onInputChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export interface ChatMessageProps {
  msg: Message;
}
