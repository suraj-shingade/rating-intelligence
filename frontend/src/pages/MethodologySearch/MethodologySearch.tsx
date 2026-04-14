import { useState, useEffect, useRef, useCallback } from 'react';
import Header from '../../components/Header/Header';
import Card from '../../components/common/Card';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import { apiClient } from '../../services/apiClient';
import { SECTOR_OPTIONS } from '../../types/api';
import type { MethodologySearchResponse } from '../../types/api';
import './MethodologySearch.css';

export default function MethodologySearch() {
  const [query, setQuery] = useState('');
  const [sector, setSector] = useState<string>('');
  const [limit, setLimit] = useState(10);
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const {
    data: results,
    loading,
    error,
    execute: doSearch,
  } = useApi<MethodologySearchResponse, [string, string, number]>(
    useCallback(
      (q: string, s: string, l: number) =>
        apiClient.searchMethodology({
          query: q,
          sector: s || null,
          limit: l,
        }),
      []
    )
  );

  useEffect(() => {
    if (!query.trim()) return;

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      doSearch(query.trim(), sector, limit);
    }, 500);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, sector, limit, doSearch]);

  const toggleExpand = (index: number) => {
    setExpandedCards((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  return (
    <>
      <Header
        title="Methodology Search"
        subtitle="Semantic search across rating methodologies"
      />
      <div className="method-search">
        {/* Search Controls */}
        <Card>
          <div className="method-search__controls">
            <div className="method-search__input-group">
              <label className="form-label" htmlFor="search-query">
                Search Query
              </label>
              <input
                id="search-query"
                className="form-input method-search__input"
                type="text"
                placeholder="e.g. debt service coverage ratio for manufacturing sector"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoFocus
              />
            </div>

            <div className="method-search__filters">
              <div className="form-group">
                <label className="form-label" htmlFor="search-sector">
                  Sector Filter
                </label>
                <select
                  id="search-sector"
                  className="form-select"
                  value={sector}
                  onChange={(e) => setSector(e.target.value)}
                >
                  <option value="">All Sectors</option>
                  {SECTOR_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="search-limit">
                  Results Limit: {limit}
                </label>
                <input
                  id="search-limit"
                  type="range"
                  min={1}
                  max={25}
                  value={limit}
                  onChange={(e) => setLimit(parseInt(e.target.value, 10))}
                  className="method-search__slider"
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Search Metadata */}
        {results && !loading && (
          <div className="method-search__meta">
            <span>
              {results.total_results} result
              {results.total_results !== 1 ? 's' : ''} found
            </span>
            <span className="method-search__meta-separator">|</span>
            <span>Search time: {results.search_time_ms.toFixed(1)} ms</span>
          </div>
        )}

        {/* Loading */}
        {loading && <LoadingSpinner message="Searching methodologies..." />}

        {/* Error */}
        {error && (
          <Card>
            <div className="method-search__error">
              <StatusBadge status="error" label="Search Failed" />
              <p>{error}</p>
            </div>
          </Card>
        )}

        {/* Results */}
        {results && !loading && results.results.length > 0 && (
          <div className="method-search__results">
            {results.results.map((result, index) => {
              const isExpanded = expandedCards.has(index);
              const contentPreview =
                result.content.length > 250 && !isExpanded
                  ? result.content.substring(0, 250) + '...'
                  : result.content;

              return (
                <Card key={index} className="method-search__result-card">
                  <div className="method-search__result-header">
                    <div className="method-search__result-badges">
                      {result.metadata.source_document && (
                        <span className="method-search__badge method-search__badge--source">
                          {result.metadata.source_document}
                        </span>
                      )}
                      {result.metadata.sector && (
                        <span className="method-search__badge method-search__badge--sector">
                          {result.metadata.sector}
                        </span>
                      )}
                      {result.metadata.sub_sector && (
                        <span className="method-search__badge method-search__badge--subsector">
                          {result.metadata.sub_sector}
                        </span>
                      )}
                    </div>
                    <span className="method-search__score-label">
                      {(result.score * 100).toFixed(0)}% match
                    </span>
                  </div>

                  <div className="method-search__score-bar">
                    <div
                      className="method-search__score-fill"
                      style={{ width: `${result.score * 100}%` }}
                    />
                  </div>

                  <p className="method-search__content">{contentPreview}</p>

                  {result.content.length > 250 && (
                    <button
                      className="method-search__expand-btn"
                      onClick={() => toggleExpand(index)}
                      type="button"
                    >
                      {isExpanded ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </Card>
              );
            })}
          </div>
        )}

        {/* Empty State */}
        {results && !loading && results.results.length === 0 && (
          <Card>
            <div className="method-search__empty">
              <p>
                No results found for &ldquo;{results.query}&rdquo;. Try
                broadening your search terms or adjusting the sector filter.
              </p>
            </div>
          </Card>
        )}

        {/* Initial State */}
        {!results && !loading && !error && (
          <Card>
            <div className="method-search__empty">
              <p>
                Enter a search query above to find relevant rating methodology
                content. Results are ranked by semantic relevance.
              </p>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
