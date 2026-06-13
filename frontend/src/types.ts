export interface TextPart {
  type: 'text';
  content: string;
}

export interface ToolCallPart {
  type: 'tool_call';
  name: string;
  input?: Record<string, unknown>;
  result?: unknown;
}

export type MessagePart = TextPart | ToolCallPart;

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  parts: MessagePart[];
}

export interface TextEvent {
  type: 'text';
  delta: string;
}

export interface ToolCallStartEvent {
  type: 'tool_call_start';
  name: string;
}

export interface ToolResultEvent {
  type: 'tool_result';
  name: string;
  input?: Record<string, unknown>;
  result: unknown;
}

export interface DoneEvent {
  type: 'done';
}

export interface ErrorEvent {
  type: 'error';
  message: string;
}

export type SSEEvent =
  | TextEvent
  | ToolCallStartEvent
  | ToolResultEvent
  | DoneEvent
  | ErrorEvent;
