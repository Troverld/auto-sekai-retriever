import {
  ImageList,
  ImageListItem,
  Popover,
  Button,
  TextField,
} from "@mui/material";
import { useMemo, useState } from "react";
import { assetUrl } from "../utils/assetPaths";

export default function Picker({ items, onPickItem }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [search, setSearch] = useState("");

  const open = Boolean(anchorEl);
  const id = open ? "picker" : undefined;

  const filteredItems = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return items.filter((item) => {
      if (!keyword) {
        return true;
      }
      return (
        item.image_id.toLowerCase().includes(keyword) ||
        item.relative_path.toLowerCase().includes(keyword)
      );
    });
  }, [items, search]);

  return (
    <div>
      <Button
        aria-describedby={id}
        variant="contained"
        color="secondary"
        onClick={(event) => setAnchorEl(event.currentTarget)}
      >
        Pick character
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
            label="Search character"
            size="small"
            color="secondary"
            value={search}
            multiline
            fullWidth
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="image-grid-wrapper">
          <ImageList
            sx={{
              width: window.innerWidth < 600 ? 300 : 500,
              height: 450,
              overflow: "visible",
            }}
            cols={window.innerWidth < 600 ? 3 : 4}
            rowHeight={140}
            className="image-grid"
          >
            {filteredItems.map((item) => (
              <ImageListItem
                key={item.image_id}
                onClick={() => {
                  setAnchorEl(null);
                  onPickItem(item);
                }}
                sx={{
                  cursor: "pointer",
                  "&:hover": {
                    opacity: 0.5,
                  },
                  "&:active": {
                    opacity: 0.8,
                  },
                }}
              >
                <img
                  src={assetUrl(item.relative_path)}
                  srcSet={assetUrl(item.relative_path)}
                  alt={item.image_id}
                  loading="lazy"
                />
              </ImageListItem>
            ))}
          </ImageList>
        </div>
      </Popover>
    </div>
  );
}
