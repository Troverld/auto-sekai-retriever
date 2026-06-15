import "./App.css";

import { useEffect, useMemo, useRef, useState } from "react";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";

import Canvas from "./components/Canvas";
import Picker from "./components/Picker";
import SearchPicker from "./components/SearchPicker";
import CHARACTER_COLOR_MAP from "./constants/characterColors";
import { loadSearchDataset } from "./search/data";

const { ClipboardItem } = window;
const DEFAULT_SPACE_SIZE = 25;
const DEFAULT_STROKE_WIDTH = 9;
const DEFAULT_POSITION = { x: 148, y: 58 };
const DEFAULT_FONT_SIZE = 47;
const DEFAULT_ROTATE = -2;
const FONT_STACKS = {
  yuruka: "YurukaStd, SSFangTangTi, sans-serif",
  fangtang: "SSFangTangTi, sans-serif",
  system:
    "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
};
const FONT_FAMILIES = {
  yuruka: "YurukaStd",
  fangtang: "SSFangTangTi",
  system: "system-ui",
};
const DEFAULT_FONT_KEY = "fangtang";
const DEFAULT_STROKE_COLOR = "#ffffff";

function buildCanvasPlaceholder(result) {
  return result?.buckets?.meme_phrases?.[0]?.text || "";
}

function resolveCanvasFontKey(preferredKey, text) {
  if (preferredKey === "fangtang" || preferredKey === "system") {
    return preferredKey;
  }

  const sample = text?.trim();
  if (!sample || !document.fonts?.check) {
    return preferredKey;
  }

  if (document.fonts.check(`16px "${FONT_FAMILIES.yuruka}"`, sample)) {
    return preferredKey;
  }

  return "fangtang";
}

function App() {
  const [datasetState, setDatasetState] = useState({
    status: "loading",
    dataset: null,
    error: "",
  });
  const [mode, setMode] = useState("polite");
  const [selectedImage, setSelectedImage] = useState(null);
  const [searchText, setSearchText] = useState("");
  const [textInput, setTextInput] = useState("");
  const [position, setPosition] = useState(DEFAULT_POSITION);
  const [fontSize, setFontSize] = useState(DEFAULT_FONT_SIZE);
  const [spaceSize, setSpaceSize] = useState(DEFAULT_SPACE_SIZE);
  const [rotate, setRotate] = useState(DEFAULT_ROTATE);
  const [curve, setCurve] = useState(false);
  const [vertical, setVertical] = useState(false);
  const [textColor, setTextColor] = useState(CHARACTER_COLOR_MAP.airi || "#ffffff");
  const [strokeWidth, setStrokeWidth] = useState(DEFAULT_STROKE_WIDTH);
  const [strokeColor, setStrokeColor] = useState(DEFAULT_STROKE_COLOR);
  const [fontKey, setFontKey] = useState(DEFAULT_FONT_KEY);
  const [textBehind, setTextBehind] = useState(false);
  const [letterSpacing, setLetterSpacing] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [fontsReady, setFontsReady] = useState(false);
  const [customImage, setCustomImage] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      try {
        const dataset = await loadSearchDataset();
        if (!cancelled) {
          setDatasetState({ status: "ready", dataset, error: "" });
        }
      } catch (error) {
        if (!cancelled) {
          setDatasetState({
            status: "error",
            dataset: null,
            error: error instanceof Error ? error.message : "failed to load search dataset",
          });
        }
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (datasetState.status !== "ready") {
      return;
    }
    if (selectedImage) {
      return;
    }
    setSelectedImage(datasetState.dataset.items[0] || null);
  }, [datasetState, selectedImage]);

  useEffect(() => {
    setPosition(DEFAULT_POSITION);
    setRotate(DEFAULT_ROTATE);
    setFontSize(DEFAULT_FONT_SIZE);
    setSpaceSize(DEFAULT_SPACE_SIZE);
    setCurve(false);
    setVertical(false);
    setTextColor(
      CHARACTER_COLOR_MAP[selectedImage?.character || ""] || CHARACTER_COLOR_MAP.airi || "#ffffff"
    );
    setStrokeWidth(DEFAULT_STROKE_WIDTH);
    setStrokeColor(DEFAULT_STROKE_COLOR);
    setLoaded(false);
  }, [selectedImage]);

  const canvasPlaceholder = buildCanvasPlaceholder(selectedImage);
  const canvasInputPlaceholder = searchText.trim() || canvasPlaceholder;
  const displayText = textInput.trim()
    ? textInput
    : searchText.trim() || canvasPlaceholder;
  const activeColor =
    CHARACTER_COLOR_MAP[selectedImage?.character || ""] ||
    CHARACTER_COLOR_MAP.airi ||
    "#ffffff";
  const img = useMemo(() => {
    const image = new Image();
    image.src = customImage
      ? customImage
      : selectedImage
        ? `/${selectedImage.relative_path}`
        : "";
    image.onload = () => setLoaded(true);
    return image;
  }, [customImage, selectedImage]);

  const angle = (Math.PI * (displayText || " ").length) / 7;
  const resolvedFontKey = useMemo(
    () => resolveCanvasFontKey(fontKey, displayText),
    [displayText, fontKey]
  );

  useEffect(() => {
    let active = true;

    async function ensureFontsReady() {
      if (!document.fonts?.load) {
        if (active) {
          setFontsReady(true);
        }
        return;
      }

      setFontsReady(false);

      const fontLoads = [];
      if (resolvedFontKey === "fangtang") {
        fontLoads.push(document.fonts.load(`16px "${FONT_FAMILIES.fangtang}"`, displayText || "测"));
      } else if (resolvedFontKey === "yuruka") {
        fontLoads.push(document.fonts.load(`16px "${FONT_FAMILIES.yuruka}"`, displayText || "a"));
        fontLoads.push(document.fonts.load(`16px "${FONT_FAMILIES.fangtang}"`, displayText || "测"));
      }

      try {
        await Promise.all(fontLoads);
        await document.fonts.ready;
      } finally {
        if (active) {
          setFontsReady(true);
        }
      }
    }

    ensureFontsReady();

    return () => {
      active = false;
    };
  }, [displayText, resolvedFontKey]);

  const resetSettings = () => {
    setTextInput("");
    setPosition(DEFAULT_POSITION);
    setRotate(DEFAULT_ROTATE);
    setFontSize(DEFAULT_FONT_SIZE);
    setSpaceSize(DEFAULT_SPACE_SIZE);
    setCurve(false);
    setVertical(false);
    setTextColor(activeColor);
    setStrokeWidth(DEFAULT_STROKE_WIDTH);
    setStrokeColor(DEFAULT_STROKE_COLOR);
    setFontKey(DEFAULT_FONT_KEY);
    setTextBehind(false);
    setLetterSpacing(0);
    setCustomImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.onload = (loadEvent) => {
      const result = loadEvent.target?.result;
      if (typeof result === "string") {
        setLoaded(false);
        setCustomImage(result);
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    };
    reader.readAsDataURL(file);
  };

  const clearUpload = () => {
    setLoaded(false);
    setCustomImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const drawText = (ctx) => {
    if (!displayText) {
      return;
    }

    ctx.font = `${fontSize}px ${FONT_STACKS[resolvedFontKey]}`;
    ctx.lineWidth = strokeWidth;
    ctx.lineJoin = "round";
    ctx.miterLimit = 2;
    ctx.save();
    ctx.translate(position.x, position.y);
    ctx.rotate(rotate / 10);
    ctx.textAlign = "center";
    ctx.strokeStyle = strokeColor;
    ctx.fillStyle = textColor;

    const lines = displayText.split("\n");
    if (curve) {
      for (const line of lines) {
        for (let index = 0; index < line.length; index += 1) {
          ctx.rotate(angle / line.length / 2.5);
          ctx.save();
          ctx.translate(0, -1 * fontSize * 3.5);
          ctx.strokeText(line[index], 0, 0);
          ctx.fillText(line[index], 0, 0);
          ctx.restore();
        }
      }
    } else if (vertical) {
      const letterStep = fontSize + letterSpacing;
      const lineStep = fontSize + spaceSize - 40;
      let xOffset = 0;
      for (const line of lines) {
        let yOffset = 0;
        for (let index = 0; index < line.length; index += 1) {
          ctx.strokeText(line[index], xOffset, yOffset);
          ctx.fillText(line[index], xOffset, yOffset);
          yOffset += letterStep;
        }
        xOffset += lineStep;
      }
    } else {
      if (letterSpacing === 0) {
        for (let index = 0, offset = 0; index < lines.length; index += 1) {
          ctx.strokeText(lines[index], 0, offset);
          ctx.fillText(lines[index], 0, offset);
          offset += spaceSize;
        }
      } else {
        ctx.textAlign = "left";
        for (let index = 0; index < lines.length; index += 1) {
          const line = lines[index];
          const lineY = index * spaceSize;
          const metrics = ctx.measureText(line);
          let charX = -metrics.width / 2;
          for (let charIndex = 0; charIndex < line.length; charIndex += 1) {
            ctx.strokeText(line[charIndex], charX, lineY);
            ctx.fillText(line[charIndex], charX, lineY);
            charX += ctx.measureText(line[charIndex]).width + letterSpacing;
          }
        }
        ctx.textAlign = "center";
      }
    }
    ctx.restore();
  };

  const draw = (ctx) => {
    ctx.canvas.width = 296;
    ctx.canvas.height = 256;
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    if (!loaded || !img.width || !img.height) {
      return;
    }

    const hRatio = ctx.canvas.width / img.width;
    const vRatio = ctx.canvas.height / img.height;
    const ratio = Math.min(hRatio, vRatio);
    const centerShiftX = (ctx.canvas.width - img.width * ratio) / 2;
    const centerShiftY = (ctx.canvas.height - img.height * ratio) / 2;

    if (textBehind && fontsReady) {
      drawText(ctx);
    }

    ctx.drawImage(
      img,
      0,
      0,
      img.width,
      img.height,
      centerShiftX,
      centerShiftY,
      img.width * ratio,
      img.height * ratio
    );
    if (!textBehind && fontsReady) {
      drawText(ctx);
    }
  };

  const onPickSearchResult = (result) => {
    setSelectedImage(result);
  };

  const onPickManifestImage = (item) => {
    setSelectedImage(item);
  };

  function b64toBlob(b64Data, contentType = "image/png", sliceSize = 512) {
    const byteCharacters = atob(b64Data);
    const byteArrays = [];
    for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
      const slice = byteCharacters.slice(offset, offset + sliceSize);
      const byteNumbers = new Array(slice.length);
      for (let index = 0; index < slice.length; index += 1) {
        byteNumbers[index] = slice.charCodeAt(index);
      }
      byteArrays.push(new Uint8Array(byteNumbers));
    }
    return new Blob(byteArrays, { type: contentType });
  }

  const copy = async () => {
    const canvas = document.getElementsByTagName("canvas")[0];
    await navigator.clipboard.write([
      new ClipboardItem({
        "image/png": b64toBlob(canvas.toDataURL().split(",")[1]),
      }),
    ]);
  };

  const download = () => {
    const canvas = document.getElementsByTagName("canvas")[0];
    const link = document.createElement("a");
    link.download = `${selectedImage?.image_id || "sekai-sticker"}_st.ayaka.one.png`;
    link.href = canvas.toDataURL();
    link.click();
  };

  return (
    <div className="App">
      {datasetState.status === "error" && (
        <Alert severity="error" className="top-alert">
          {datasetState.error}
        </Alert>
      )}
      <div className="container">
        <div className="vertical">
          <div className="canvas">
            <Canvas draw={draw} />
          </div>
          <Slider
            value={curve ? 256 - position.y + fontSize * 3 : 256 - position.y}
            onChange={(_, value) =>
              setPosition({
                ...position,
                y: curve ? 256 + fontSize * 3 - value : 256 - value,
              })
            }
            min={0}
            max={256}
            step={1}
            orientation="vertical"
            track={false}
            color="secondary"
          />
        </div>
        <div className="horizontal">
          <Slider
            className="slider-horizontal"
            value={position.x}
            onChange={(_, value) => setPosition({ ...position, x: value })}
            min={0}
            max={296}
            step={1}
            track={false}
            color="secondary"
          />
          <div className="search-box">
            <TextField
              label="检索文本"
              size="small"
              color="secondary"
              value={searchText}
              multiline
              fullWidth
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="为空时不检索"
            />
            {datasetState.status === "loading" && (
              <div className="search-inline-status">
                <CircularProgress size={16} color="secondary" />
                <span>加载检索索引中</span>
              </div>
            )}
          </div>
          <div className="search-box">
            <TextField
              label="画布文本"
              size="small"
              color="secondary"
              value={textInput}
              multiline
              fullWidth
              onChange={(event) => setTextInput(event.target.value)}
              placeholder={canvasInputPlaceholder}
              helperText={
                textInput.trim()
                  ? "当前使用画布文本内容"
                  : searchText.trim()
                    ? "当前为空，画布将使用检索文本"
                    : "当前为空，画布将使用默认占位短句"
              }
            />
          </div>
          <div className="picker">
            {datasetState.status === "ready" && (
              <Picker
                items={datasetState.dataset.items}
                onPickItem={onPickManifestImage}
              />
            )}
            <SearchPicker
              datasetState={datasetState}
              query={searchText}
              mode={mode}
              setMode={setMode}
              onPickResult={onPickSearchResult}
            />
          </div>
          <div className="buttons">
            <Button color="secondary" onClick={copy}>
              copy
            </Button>
            <Button color="secondary" onClick={download}>
              download
            </Button>
          </div>
          <div className="settings">
            <div>
              <label>Font: </label>
              <TextField
                select
                size="small"
                color="secondary"
                value={fontKey}
                onChange={(event) => setFontKey(event.target.value)}
                className="compact-select"
              >
                <MenuItem value="yuruka">YurukaStd</MenuItem>
                <MenuItem value="fangtang">SSFangTangTi</MenuItem>
                <MenuItem value="system">System Sans</MenuItem>
              </TextField>
            </div>
            <div>
              <label>Rotate: </label>
              <Slider
                value={rotate}
                onChange={(_, value) => setRotate(value)}
                min={-10}
                max={10}
                step={0.2}
                track={false}
                color="secondary"
              />
            </div>
            <div>
              <label>
                <nobr>Font size: </nobr>
              </label>
              <Slider
                value={fontSize}
                onChange={(_, value) => setFontSize(value)}
                min={10}
                max={100}
                step={1}
                track={false}
                color="secondary"
              />
            </div>
            <div>
              <label>
                <nobr>Spacing: </nobr>
              </label>
              <Slider
                value={spaceSize}
                onChange={(_, value) => setSpaceSize(value)}
                min={18}
                max={100}
                step={1}
                track={false}
                color="secondary"
              />
            </div>
            <div>
              <label>
                <nobr>Letter spacing: </nobr>
              </label>
              <Slider
                value={letterSpacing}
                onChange={(_, value) => setLetterSpacing(value)}
                min={-10}
                max={30}
                step={1}
                track={false}
                color="secondary"
              />
            </div>
            <div>
              <label>
                <nobr>Stroke width: </nobr>
              </label>
              <Slider
                value={strokeWidth}
                onChange={(_, value) => setStrokeWidth(value)}
                min={0}
                max={30}
                step={0.5}
                track={false}
                color="secondary"
              />
            </div>
            <div>
              <label>Curve (Beta): </label>
              <Switch
                checked={curve}
                onChange={(event) => setCurve(event.target.checked)}
                color="secondary"
              />
            </div>
            <div>
              <label>Vertical text: </label>
              <Switch
                checked={vertical}
                onChange={(event) => setVertical(event.target.checked)}
                color="secondary"
              />
            </div>
            <div>
              <label>Text behind image: </label>
              <Switch
                checked={textBehind}
                onChange={(event) => setTextBehind(event.target.checked)}
                color="secondary"
              />
            </div>
            <div className="color-row">
              <label>Text color: </label>
              <input
                type="color"
                value={textColor}
                onChange={(event) => setTextColor(event.target.value)}
                aria-label="Text color"
              />
              <Button
                color="secondary"
                variant="outlined"
                size="small"
                onClick={() => setTextColor(activeColor)}
              >
                Reset
              </Button>
            </div>
            <div className="color-row">
              <label>Stroke color: </label>
              <input
                type="color"
                value={strokeColor}
                onChange={(event) => setStrokeColor(event.target.value)}
                aria-label="Stroke color"
              />
              <Button
                color="secondary"
                variant="outlined"
                size="small"
                onClick={() => setStrokeColor(DEFAULT_STROKE_COLOR)}
              >
                Reset
              </Button>
            </div>
            <div className="upload-row">
              <label>Custom image: </label>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleUpload}
                aria-label="Custom image upload"
                hidden
              />
              <Button
                color="secondary"
                variant="outlined"
                size="small"
                onClick={() => fileInputRef.current?.click()}
              >
                Upload
              </Button>
              {customImage && (
                <Button
                  color="secondary"
                  variant="outlined"
                  size="small"
                  onClick={clearUpload}
                >
                  Clear
                </Button>
              )}
            </div>
            <div>
              <Button color="secondary" variant="outlined" onClick={resetSettings}>
                Reset All
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
