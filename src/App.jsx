import "./App.css";

import { useEffect, useMemo, useState } from "react";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Slider from "@mui/material/Slider";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Alert from "@mui/material/Alert";

import Canvas from "./components/Canvas";
import Picker from "./components/Picker";
import SearchPicker from "./components/SearchPicker";
import characters from "./characters.json";
import { loadSearchDataset } from "./search/data";
import { normalizeImageKey, toImgNewPath } from "./utils/imagePath";

const { ClipboardItem } = window;
const CHARACTER_COLOR_MAP = Object.fromEntries(
  characters.map((item) => [item.character.toLowerCase(), item.color])
);

function resolveCharacterIndex(result) {
  if (!result) {
    return null;
  }
  const resultKey = normalizeImageKey(result.relative_path);
  return characters.findIndex((item) => normalizeImageKey(item.img) === resultKey);
}

function buildFallbackText(result) {
  return result?.texts?.[0] || "";
}

function App() {
  const [datasetState, setDatasetState] = useState({
    status: "loading",
    dataset: null,
    error: "",
  });
  const [mode, setMode] = useState("polite");
  const [character, setCharacter] = useState(49);
  const [selectedImage, setSelectedImage] = useState(null);
  const [searchText, setSearchText] = useState("");
  const [textInput, setTextInput] = useState("");
  const [position, setPosition] = useState({
    x: characters[49].defaultText.x,
    y: characters[49].defaultText.y,
  });
  const [fontSize, setFontSize] = useState(characters[49].defaultText.s);
  const [spaceSize, setSpaceSize] = useState(1);
  const [rotate, setRotate] = useState(characters[49].defaultText.r);
  const [curve, setCurve] = useState(false);
  const [loaded, setLoaded] = useState(false);

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
    const fallbackPath = `img_new/${characters[character].img.toLowerCase()}`;
    const matched = datasetState.dataset.items.find(
      (item) => item.relative_path === fallbackPath
    );
    if (matched) {
      setSelectedImage(matched);
    }
  }, [character, datasetState, selectedImage]);

  useEffect(() => {
    const defaults = characters[character].defaultText;
    setPosition({ x: defaults.x, y: defaults.y });
    setRotate(defaults.r);
    setFontSize(defaults.s);
    setLoaded(false);
  }, [character]);

  const displayText = textInput.trim()
    ? textInput
    : searchText.trim() || buildFallbackText(selectedImage);
  const isDerivedText = !textInput.trim() && Boolean(searchText.trim());
  const activeColor =
    CHARACTER_COLOR_MAP[selectedImage?.character || ""] ||
    characters[character].color;
  const img = useMemo(() => {
    const image = new Image();
    image.src = selectedImage ? `/${selectedImage.relative_path}` : toImgNewPath(characters[character].img);
    image.onload = () => setLoaded(true);
    return image;
  }, [character, selectedImage]);

  const angle = (Math.PI * (displayText || " ").length) / 7;

  const draw = (ctx) => {
    ctx.canvas.width = 296;
    ctx.canvas.height = 256;

    if (loaded && document.fonts.check("12px YurukaStd")) {
      const hRatio = ctx.canvas.width / img.width;
      const vRatio = ctx.canvas.height / img.height;
      const ratio = Math.min(hRatio, vRatio);
      const centerShiftX = (ctx.canvas.width - img.width * ratio) / 2;
      const centerShiftY = (ctx.canvas.height - img.height * ratio) / 2;

      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
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

      if (!displayText) {
        return;
      }

      ctx.font = `${fontSize}px YurukaStd, SSFangTangTi`;
      ctx.lineWidth = 9;
      ctx.save();
      ctx.translate(position.x, position.y);
      ctx.rotate(rotate / 10);
      ctx.textAlign = "center";
      ctx.strokeStyle = "white";
      ctx.fillStyle = activeColor;
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
      } else {
        for (let index = 0, offset = 0; index < lines.length; index += 1) {
          ctx.strokeText(lines[index], 0, offset);
          ctx.fillText(lines[index], 0, offset);
          offset += spaceSize;
        }
      }
      ctx.restore();
    }
  };

  const onPickSearchResult = (result) => {
    setSelectedImage(result);
    const nextIndex = resolveCharacterIndex(result);
    if (nextIndex !== null && nextIndex >= 0) {
      setCharacter(nextIndex);
    }
  };

  const onPickManifestImage = (item) => {
    setSelectedImage(item);
    const nextIndex = resolveCharacterIndex(item);
    if (nextIndex !== null && nextIndex >= 0) {
      setCharacter(nextIndex);
    }
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
    link.download = `${characters[character].name}_st.ayaka.one.png`;
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
              label="检索框"
              size="small"
              color="secondary"
              value={searchText}
              multiline
              fullWidth
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="为空时沿用原始 Pick character 模式"
            />
            {datasetState.status === "loading" && (
              <div className="search-inline-status">
                <CircularProgress size={16} color="secondary" />
                <span>加载检索索引中</span>
              </div>
            )}
          </div>
          <div className="settings">
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
              <label>Curve (Beta): </label>
              <Switch
                checked={curve}
                onChange={(event) => setCurve(event.target.checked)}
                color="secondary"
              />
            </div>
          </div>
          <div className="text">
            <TextField
              label="实际文字框"
              size="small"
              color="secondary"
              value={isDerivedText ? searchText : textInput}
              multiline
              fullWidth
              onChange={(event) => setTextInput(event.target.value)}
              placeholder={
                selectedImage?.texts?.[0] || characters[character].defaultText.text
              }
              InputProps={{
                sx: isDerivedText
                  ? {
                      "& textarea": {
                        color: "rgba(255, 255, 255, 0.52)",
                      },
                    }
                  : undefined,
              }}
              helperText={
                textInput.trim()
                  ? "当前使用实际文字框内容"
                  : searchText.trim()
                    ? "当前为空，将使用检索框内容"
                    : "当前为空，将只切换图片不覆写默认文案"
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
        </div>
      </div>
    </div>
  );
}

export default App;
