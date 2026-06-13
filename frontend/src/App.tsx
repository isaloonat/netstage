import { useState, useRef, useCallback, useEffect } from 'react';
import type { Message, TextPart } from './types';
import { streamChat } from './api';
import ChatMessage from './components/ChatMessage';
import InputBar from './components/InputBar';
import StarterPrompts from './components/StarterPrompts';
import './index.css';

const STARTER_PROMPTS = [
  { text: "What's the health of my network?", send: true },
  { text: 'Why is any device down?', send: true },
  { text: 'Plan subnets for Staff 60 / Students 100 / IoT 20 on 192.168.1.0/24', send: true },
  { text: 'Audit this config: [paste]', send: false },
];

let _nextId = 0;
const makeId = () => String(++_nextId);

function buildApiHistory(messages: Message[]) {
  return messages.map(m => ({
    role: m.role,
    content: m.parts
      .filter((p): p is TextPart => p.type === 'text')
      .map(p => p.content)
      .join(''),
  }));
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesRef = useRef<Message[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Keep ref in sync so send() always reads the latest messages
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;

    const userMsg: Message = {
      id: makeId(),
      role: 'user',
      parts: [{ type: 'text', content: trimmed }],
    };
    const assistantMsg: Message = {
      id: makeId(),
      role: 'assistant',
      parts: [],
    };

    const history = [
      ...buildApiHistory(messagesRef.current),
      { role: 'user', content: trimmed },
    ];

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setInputValue('');
    setIsStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      for await (const event of streamChat(history, ctrl.signal)) {
        if (event.type === 'text') {
          setMessages(prev => {
            const msgs = [...prev];
            const last = { ...msgs[msgs.length - 1], parts: [...msgs[msgs.length - 1].parts] };
            const parts = last.parts;
            const tail = parts[parts.length - 1];
            if (!tail || tail.type !== 'text') {
              parts.push({ type: 'text', content: event.delta });
            } else {
              parts[parts.length - 1] = { type: 'text', content: tail.content + event.delta };
            }
            msgs[msgs.length - 1] = last;
            return msgs;
          });
        } else if (event.type === 'tool_call_start') {
          setMessages(prev => {
            const msgs = [...prev];
            const last = { ...msgs[msgs.length - 1], parts: [...msgs[msgs.length - 1].parts] };
            last.parts.push({ type: 'tool_call', name: event.name });
            msgs[msgs.length - 1] = last;
            return msgs;
          });
        } else if (event.type === 'tool_result') {
          setMessages(prev => {
            const msgs = [...prev];
            const last = { ...msgs[msgs.length - 1], parts: [...msgs[msgs.length - 1].parts] };
            for (let i = last.parts.length - 1; i >= 0; i--) {
              const p = last.parts[i];
              if (p.type === 'tool_call' && p.name === event.name && p.result === undefined) {
                last.parts[i] = { ...p, input: event.input, result: event.result };
                break;
              }
            }
            msgs[msgs.length - 1] = last;
            return msgs;
          });
        } else if (event.type === 'error') {
          setMessages(prev => {
            const msgs = [...prev];
            const last = { ...msgs[msgs.length - 1], parts: [...msgs[msgs.length - 1].parts] };
            last.parts.push({ type: 'text', content: `Error: ${event.message}` });
            msgs[msgs.length - 1] = last;
            return msgs;
          });
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        setMessages(prev => {
          const msgs = [...prev];
          const last = { ...msgs[msgs.length - 1], parts: [...msgs[msgs.length - 1].parts] };
          last.parts.push({ type: 'text', content: 'Could not reach the backend. Is it running?' });
          msgs[msgs.length - 1] = last;
          return msgs;
        });
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [isStreaming]);

  const handleStarterPrompt = useCallback((text: string, sendImmediately: boolean) => {
    if (sendImmediately) {
      send(text);
    } else {
      setInputValue(text.replace('[paste]', ''));
    }
  }, [send]);

  return (
    <div className="app">
      <header className="header">
        <span className="logo-mark">&#x2B21;</span>
        <span className="logo">NetSage</span>
        <span className="subtitle">AI Network Engineer</span>
        {isStreaming && <span className="streaming-badge">thinking…</span>}
      </header>
      <main className="chat-area">
        {messages.length === 0 && (
          <StarterPrompts prompts={STARTER_PROMPTS} onSelect={handleStarterPrompt} />
        )}
        {messages.map((msg, i) => (
          <ChatMessage
            key={msg.id}
            message={msg}
            streaming={isStreaming && i === messages.length - 1}
          />
        ))}
        <div ref={bottomRef} />
      </main>
      <InputBar value={inputValue} onChange={setInputValue} onSend={send} disabled={isStreaming} />
    </div>
  );
}
