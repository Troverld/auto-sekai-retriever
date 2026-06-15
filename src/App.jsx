import "./App.css";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Chip,
  CircularProgress,
  Slider,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";

import SearchResults from "./components/SearchResults";
import { MODE_WEIGHTS } from "./search/constants";
import { loadSearchDataset, rankSearchResults } from "./search/data";
import { embedQueryText, getQueryEmbedderConfig } from "./search/queryEmbedder";

const DEFAULT_QUERY = "礼貌地说先这样吧";
const DEFAULT_TOP_K = 12;

function App() {
  const [datasetState, setDatasetState] = useState({
    status: "loading",
    dataset: null,
    error: "",
  });
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [mode, setMode] = useState("polite");
  const [topK, setTopK] = useState(DEFAULT_TOP_K);
  const [queryState, setQueryState] = useState({
    status: "idle",
    error: "",
  });
  const [results, setResults] = useState([]);
  const [selectedResult, setSelectedResult] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const dataset = await loadSearchDataset();
        if (cancelled) {
          return;
        }
        setDatasetState({ status: "ready", dataset, error: "" });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setDatasetState({
          status: "error",
          dataset: null,
          error: error instanceof Error ? error.message : "failed to load search dataset",
        });
      }
    }

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (datasetState.status !== "ready") {
      return undefined;
    }

    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setSelectedResult(null);
      setQueryState({ status: "idle", error: "" });
      return undefined;
    }

    let cancelled = false;
    setQueryState({ status: "embedding", error: "" });

    const timer = window.setTimeout(async () => {
      try {
        const queryVector = await embedQueryText(trimmed);
        if (cancelled) {
          return;
        }

        const ranked = rankSearchResults(
          datasetState.dataset.items,
          queryVector,
          MODE_WEIGHTS[mode]
        );

        setResults(ranked);
        setSelectedResult((current) =>
          current
            ? ranked.find((item) => item.image_id === current.image_id) || ranked[0] || null
            : ranked[0] || null
        );
        setQueryState({ status: "ready", error: "" });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setQueryState({
          status: "error",
          error: error instanceof Error ? error.message : "failed to embed query",
        });
      }
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [datasetState, mode, query]);

  const selectedTexts = useMemo(() => {
    return selectedResult ? selectedResult.texts.slice(0, 8) : [];
  }, [selectedResult]);

  return (
    <div className="search-app">
      <div className="search-shell">
        <header className="hero-panel">
          <div className="hero-copy">
            <p className="eyebrow">Phase 4 Retrieval</p>
            <h1>用一句话，从 787 张表情里检索最贴切的那张。</h1>
            <p className="hero-description">
              前端直接消费 `manifest.json`、`corpus.json`、`embeddings.int8.bin` 和
              `embeddings.meta.json`，浏览器侧只负责 query embedding 与排序。
            </p>
          </div>
          <div className="hero-controls">
            <TextField
              label="Query"
              color="secondary"
              value={query}
              multiline
              minRows={3}
              fullWidth
              onChange={(event) => setQuery(event.target.value)}
            />
            <div className="toolbar-row">
              <ToggleButtonGroup
                exclusive
                color="secondary"
                value={mode}
                onChange={(_, nextMode) => {
                  if (nextMode) {
                    setMode(nextMode);
                  }
                }}
              >
                <ToggleButton value="polite">礼貌模式</ToggleButton>
                <ToggleButton value="casual">轻松模式</ToggleButton>
              </ToggleButtonGroup>
              <Button color="secondary" onClick={() => setQuery(DEFAULT_QUERY)}>
                Reset Query
              </Button>
            </div>
            <div className="topk-row">
              <span>Top-K</span>
              <Slider
                value={topK}
                onChange={(_, value) => setTopK(value)}
                min={6}
                max={24}
                step={1}
                color="secondary"
              />
              <strong>{topK}</strong>
            </div>
            {datasetState.status === "loading" && (
              <div className="status-inline">
                <CircularProgress size={18} color="secondary" />
                <span>Loading search assets…</span>
              </div>
            )}
            {queryState.status === "embedding" && datasetState.status === "ready" && (
              <div className="status-inline">
                <CircularProgress size={18} color="secondary" />
                <span>Embedding query and ranking…</span>
              </div>
            )}
            {datasetState.status === "ready" && (
              <div className="dataset-stats">
                <Chip
                  label={`${datasetState.dataset.meta.format.item_count} images`}
                  size="small"
                />
                <Chip
                  label={`${datasetState.dataset.meta.format.entry_count} vectors`}
                  size="small"
                />
                <Chip
                  label={`${datasetState.dataset.meta.format.dimension} dims`}
                  size="small"
                />
              </div>
            )}
          </div>
        </header>

        {datasetState.status === "error" && (
          <Alert severity="error">{datasetState.error}</Alert>
        )}
        {queryState.status === "error" && <Alert severity="error">{queryState.error}</Alert>}
        {queryState.status === "error" && getQueryEmbedderConfig() && (
          <Alert severity="info">
            <pre className="debug-block">
              {JSON.stringify(getQueryEmbedderConfig(), null, 2)}
            </pre>
          </Alert>
        )}

        <main className="search-main">
          <section className="preview-panel">
            <div className="preview-frame">
              {selectedResult ? (
                <img
                  src={`/${selectedResult.relative_path}`}
                  alt={selectedResult.image_id}
                />
              ) : (
                <div className="preview-empty">输入一句话开始检索</div>
              )}
            </div>
            <div className="preview-meta">
              <div>
                <p className="eyebrow">Current Pick</p>
                <h2>{selectedResult ? selectedResult.image_id : "No selection"}</h2>
              </div>
              <div className="score-card">
                <span>Final score</span>
                <strong>{selectedResult ? selectedResult.score.toFixed(4) : "--"}</strong>
              </div>
            </div>
            <div className="preview-tags">
              {selectedTexts.map((text) => (
                <Chip key={text} label={text} />
              ))}
            </div>
          </section>

          <SearchResults
            results={results}
            topK={topK}
            onPickResult={setSelectedResult}
          />
        </main>
      </div>
    </div>
  );
}

export default App;
