import type { Message, TextPart, ToolCallPart } from '../types';
import ToolChip from './ToolChip';

interface Props {
  message: Message;
  streaming: boolean;
}

export default function ChatMessage({ message, streaming }: Props) {
  const { role, parts } = message;
  const isEmpty = parts.length === 0;
  const lastPart = parts[parts.length - 1];
  const isLastPartText = !isEmpty && lastPart.type === 'text';

  return (
    <div className={`message message-${role}`}>
      <div className="message-label">{role === 'user' ? 'You' : 'NetSage'}</div>
      <div className="message-content">
        {isEmpty && streaming && (
          <div className="loading-dots">
            <div className="loading-dot" />
            <div className="loading-dot" />
            <div className="loading-dot" />
          </div>
        )}
        {parts.map((part, i) => {
          if (part.type === 'text') {
            const tp = part as TextPart;
            const isLast = i === parts.length - 1;
            return (
              <div
                key={i}
                className={`message-text${streaming && isLast ? ' cursor-blink' : ''}`}
              >
                {tp.content || ' '}
              </div>
            );
          }
          if (part.type === 'tool_call') {
            return <ToolChip key={i} tool={part as ToolCallPart} />;
          }
          return null;
        })}
        {!isEmpty && !isLastPartText && streaming && (
          <div className="loading-dots">
            <div className="loading-dot" />
            <div className="loading-dot" />
            <div className="loading-dot" />
          </div>
        )}
      </div>
    </div>
  );
}
