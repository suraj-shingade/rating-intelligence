import { useState } from 'react';
import type { MethodologyReference } from '../../types/api';
import './MethodologyReferences.css';

interface MethodologyReferencesProps {
  references: MethodologyReference[];
  title?: string;
}

export default function MethodologyReferences({
  references,
  title = 'Methodology References',
}: MethodologyReferencesProps) {
  const [expanded, setExpanded] = useState(false);

  if (!references || references.length === 0) {
    return null;
  }

  return (
    <div className="methodology-refs">
      <button
        className="methodology-refs__toggle"
        onClick={() => setExpanded((prev) => !prev)}
        type="button"
      >
        <span className="methodology-refs__toggle-title">
          {title} ({references.length})
        </span>
        <span
          className={`methodology-refs__chevron ${expanded ? 'methodology-refs__chevron--open' : ''}`}
        >
          &#9662;
        </span>
      </button>
      {expanded && (
        <div className="methodology-refs__list">
          {references.map((ref, idx) => (
            <div className="methodology-refs__item" key={idx}>
              <div className="methodology-refs__item-header">
                <span className="methodology-refs__source">
                  {ref.source_document}
                </span>
                {ref.section && (
                  <span className="methodology-refs__section">
                    {ref.section}
                  </span>
                )}
                <span className="methodology-refs__score">
                  Relevance: {(ref.relevance_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="methodology-refs__score-bar">
                <div
                  className="methodology-refs__score-fill"
                  style={{ width: `${ref.relevance_score * 100}%` }}
                />
              </div>
              <p className="methodology-refs__excerpt">{ref.content_excerpt}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
