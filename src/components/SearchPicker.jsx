import {
  ImageList,
  ImageListItem,
  Popover,
  Button,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  CircularProgress,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { MODE_WEIGHTS } from "../search/constants";
import { embedQueryText } from "../search/queryEmbedder";
import { rankSearchResults } from "../search/data";
import { assetUrl } from "../utils/assetPaths";

export default function SearchPicker({
  datasetState,
  query,
  mode,
  setMode,
  onPickResult,
}) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [queryState, setQueryState] = useState({ status: "idle", error: "" });
  const [results, setResults] = useState([]);

  const open = Boolean(anchorEl);
  const id = open ? "search-picker" : undefined;

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    if (datasetState.status !== "ready") {
      return undefined;
    }

    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setQueryState({ status: "idle", error: "" });
      return undefined;
    }

    let cancelled = false;
    setQueryState({ status: "embedding", error: "" });

    const timer = window.setTimeout(async () => {
      try {
        const vector = await embedQueryText(trimmed);
        if (cancelled) {
          return;
        }
        const ranked = rankSearchResults(
          datasetState.dataset.items,
          vector,
          MODE_WEIGHTS[mode]
        );
        setResults(ranked);
        setQueryState({ status: "ready", error: "" });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setQueryState({
          status: "error",
          error: error instanceof Error ? error.message : "failed to rank results",
        });
      }
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [datasetState, mode, open, query]);

  const visibleItems = useMemo(() => results, [results]);

  return (
    <div>
      <Button
        aria-describedby={id}
        variant="contained"
        color="secondary"
        onClick={(event) => setAnchorEl(event.currentTarget)}
        disabled={!query.trim()}
      >
        Search character
      </Button>
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "left",
        }}
        className="modal"
      >
        <div className="picker-search">
          <TextField
            label="Search query"
            size="small"
            color="secondary"
            value={query}
            multiline
            fullWidth
            disabled
          />
        </div>
        <div className="search-mode-row">
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
            <ToggleButton value="polite">礼貌</ToggleButton>
            <ToggleButton value="casual">轻松</ToggleButton>
          </ToggleButtonGroup>
          {queryState.status === "embedding" && (
            <div className="search-inline-status">
              <CircularProgress size={16} color="secondary" />
              <span>检索中</span>
            </div>
          )}
        </div>
        {queryState.status === "error" && (
          <div className="picker-error">{queryState.error}</div>
        )}
        <div className="image-grid-wrapper">
          <ImageList
            sx={{
              width: window.innerWidth < 600 ? 300 : 500,
              height: 450,
              overflow: "visible",
            }}
            cols={window.innerWidth < 600 ? 3 : 4}
            rowHeight={170}
            className="image-grid"
          >
            {visibleItems.map((item) => (
              <ImageListItem
                key={item.image_id}
                onClick={() => {
                  setAnchorEl(null);
                  onPickResult(item);
                }}
                sx={{
                  cursor: "pointer",
                  "&:hover": {
                    opacity: 0.75,
                  },
                  "&:active": {
                    opacity: 0.9,
                  },
                }}
              >
                <img
                  src={assetUrl(item.relative_path)}
                  alt={item.image_id}
                  loading="lazy"
                />
                <div className="search-card-meta">
                  <strong>{item.image_id}</strong>
                  <span>{item.score.toFixed(4)}</span>
                </div>
              </ImageListItem>
            ))}
          </ImageList>
        </div>
      </Popover>
    </div>
  );
}
