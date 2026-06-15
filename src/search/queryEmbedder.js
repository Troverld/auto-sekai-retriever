import { env, pipeline } from "@huggingface/transformers";

import { QUERY_MODEL_ID } from "./constants";
import { l2Normalize } from "./math";
import { PUBLIC_BASE, assetUrl } from "../utils/assetPaths";

let extractorPromise = null;
let queryEmbedderConfig = null;

const LOCAL_MODEL_FILES = [
  "config.json",
  "tokenizer.json",
  "tokenizer_config.json",
  "special_tokens_map.json",
  "vocab.txt",
  "quantize_config.json",
  "onnx/model_quantized.onnx",
];
const localModelInventory = [...LOCAL_MODEL_FILES];

function toPlainArray(tensorLike) {
  if (Array.isArray(tensorLike)) {
    return tensorLike;
  }

  if (tensorLike?.data) {
    return Array.from(tensorLike.data);
  }

  return [];
}

async function assertLocalModelFiles(modelId) {
  const basePath = `${env.localModelPath}${modelId}/`;
  for (const file of LOCAL_MODEL_FILES) {
    const url = `${basePath}${file}`;
    const response = await fetch(url, { method: "GET" });
    const contentType = response.headers.get("content-type") || "";
    if (!response.ok) {
      throw new Error(`local model file request failed: ${url} status=${response.status}`);
    }
    if (file.endsWith(".json")) {
      const text = await response.text();
      const trimmed = text.trimStart();
      if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
        throw new Error(
          `local model json file returned non-json content: ${url} contentType=${contentType} prefix=${JSON.stringify(trimmed.slice(0, 40))}`
        );
      }
      continue;
    }
    if (file.endsWith(".onnx")) {
      const buffer = await response.arrayBuffer();
      if (buffer.byteLength < 1024) {
        throw new Error(
          `local model onnx file looks too small: ${url} bytes=${buffer.byteLength}`
        );
      }
      continue;
    }
    const text = await response.text();
    if (!text || text.startsWith("<!DOCTYPE")) {
      throw new Error(
        `local model text file returned invalid content: ${url} contentType=${contentType}`
      );
    }
  }
}

async function resetTransformersBrowserCache() {
  if (typeof caches === "undefined") {
    return;
  }
  try {
    await caches.delete("transformers-cache");
  } catch (error) {
    console.warn("failed to clear transformers cache", error);
  }
}

export async function getQueryEmbedder() {
  if (!extractorPromise) {
    env.allowLocalModels = true;
    env.allowRemoteModels = false;
    env.useBrowserCache = false;
    env.localModelPath = PUBLIC_BASE ? `${PUBLIC_BASE}/models/` : assetUrl("/models/");
    queryEmbedderConfig = {
      model: QUERY_MODEL_ID,
      allowLocalModels: env.allowLocalModels,
      allowRemoteModels: env.allowRemoteModels,
      useBrowserCache: env.useBrowserCache,
      remoteHost: env.remoteHost,
      remotePathTemplate: env.remotePathTemplate,
      localModelPath: env.localModelPath,
      wasmPaths: env.backends?.onnx?.wasm?.wasmPaths ?? null,
      expectedLocalFiles: localModelInventory,
    };
    extractorPromise = resetTransformersBrowserCache()
      .then(() => assertLocalModelFiles(QUERY_MODEL_ID))
      .then(() => pipeline("feature-extraction", QUERY_MODEL_ID))
      .catch((error) => {
      const details = [
        `model=${queryEmbedderConfig.model}`,
        `allowLocalModels=${String(queryEmbedderConfig.allowLocalModels)}`,
        `allowRemoteModels=${String(queryEmbedderConfig.allowRemoteModels)}`,
        `remoteHost=${queryEmbedderConfig.remoteHost}`,
        `remotePathTemplate=${queryEmbedderConfig.remotePathTemplate}`,
        `localModelPath=${queryEmbedderConfig.localModelPath}`,
        `wasmPaths=${queryEmbedderConfig.wasmPaths}`,
      ].join("\n");
      throw new Error(
        `query model bootstrap failed.\n${details}\nroot=${error instanceof Error ? error.message : String(error)}`
      );
      });
  }
  return extractorPromise;
}

export function getQueryEmbedderConfig() {
  return queryEmbedderConfig;
}

export async function embedQueryText(text) {
  const extractor = await getQueryEmbedder();
  const output = await extractor(text, {
    pooling: "mean",
    normalize: true,
  });

  const vector = toPlainArray(output);
  if (vector.length === 0) {
    throw new Error("query embedding returned empty vector");
  }
  return l2Normalize(vector.map((value) => Number(value)));
}
