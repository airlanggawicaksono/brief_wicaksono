import type { RefObject } from "react";
import type { Artifact, Extraction, PredictResult, ProcessEvent, ToolCall } from "./predict";
import React from "react";

export interface Message {
  role: "user" | "assistant";
  content: string;
  extraction?: Extraction;
  result?: PredictResult;
  process?: ProcessEvent[];
  toolCalls?: ToolCall[];
  artifacts?: Artifact[];
  loading?: boolean;
}

export interface UseChatReturn {
  input: string;
  setInput: (value: string) => void;
  messages: Message[];
  loading: boolean;
  bottomRef: RefObject<HTMLDivElement | null>;
  handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  handleReset: () => void;
}

export interface ChatInputProps {
  input: string;
  loading: boolean;
  onInputChange: (value: string) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
}

export interface ChatMessageProps {
  msg: Message;
}
