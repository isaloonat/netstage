import { useState } from 'react';
import type { ToolCallPart } from '../types';

interface Props {
  tool: ToolCallPart;
}

export default function ToolChip({ tool }: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasResult = tool.result !== undefined;

  return (
    <div className="tool-chip">
      <button
        className="tool-chip-header"
        onClick={() => setExpanded(e => !e)}
        disabled={!hasResult}
        aria-expanded={expanded}
      >
        <span className="tool-icon">&#x1F527;</span>
        <span className="tool-name">{tool.name}</span>
        {hasResult ? (
          <span className="tool-status tool-status-done">done</span>
        ) : (
          <span className="tool-status tool-status-running">running</span>
        )}
        {hasResult && (
          <span className="tool-toggle">{expanded ? '▲' : '▼'}</span>
        )}
      </button>
      {expanded && hasResult && (
        <div className="tool-body">
          {tool.input && Object.keys(tool.input).length > 0 && (
            <>
              <span className="tool-section-label">Input</span>
              <pre className="tool-json">{JSON.stringify(tool.input, null, 2)}</pre>
            </>
          )}
          <span className="tool-section-label">Result</span>
          <pre className="tool-json">{JSON.stringify(tool.result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
