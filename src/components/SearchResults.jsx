import { Chip } from "@mui/material";

export default function SearchResults({ results, topK, onPickResult }) {
  const visibleResults = results.slice(0, topK);

  return (
    <div className="results-panel">
      <div className="results-header">
        <h2>Top Matches</h2>
        <span>{visibleResults.length} shown</span>
      </div>
      <div className="results-grid">
        {visibleResults.map((result, index) => (
          <button
            type="button"
            key={result.image_id}
            className="result-card"
            onClick={() => onPickResult(result)}
          >
            <div className="result-rank">#{index + 1}</div>
            <img
              src={`/${result.relative_path}`}
              alt={result.image_id}
              loading="lazy"
            />
            <div className="result-meta">
              <strong>{result.image_id}</strong>
              <span>{result.score.toFixed(4)}</span>
            </div>
            <div className="result-tags">
              {result.texts.slice(0, 3).map((text) => (
                <Chip key={`${result.image_id}-${text}`} label={text} size="small" />
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
