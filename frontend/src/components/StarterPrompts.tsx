interface Prompt {
  text: string;
  send: boolean;
}

interface Props {
  prompts: Prompt[];
  onSelect: (text: string, sendImmediately: boolean) => void;
}

export default function StarterPrompts({ prompts, onSelect }: Props) {
  return (
    <div className="starter-wrapper">
      <div className="starter-icon">&#x2B21;</div>
      <h1 className="starter-title">NetSage</h1>
      <p className="starter-desc">
        Ask about network health, plan VLSM subnets, or audit Cisco IOS configs.
      </p>
      <div className="starter-chips">
        {prompts.map(p => (
          <button
            key={p.text}
            className="starter-chip"
            onClick={() => onSelect(p.text, p.send)}
          >
            {p.text}
          </button>
        ))}
      </div>
    </div>
  );
}
