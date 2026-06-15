import { BUCKET_ORDER, SOFTMAX_BUCKETS } from "./constants";
import {
  cosineSimilarity,
  l2Normalize,
  softmaxWeights,
  weightedAverageVector,
} from "./math";

function bucketScore(entries, queryVector) {
  if (entries.length === 0) {
    return 0;
  }

  const similarities = entries.map((entry) =>
    cosineSimilarity(entry.vector, queryVector)
  );

  if (SOFTMAX_BUCKETS.has(entries[0].bucket)) {
    const normalizedWeights = softmaxWeights(entries.map((entry) => entry.weight));
    return entries.reduce((sum, entry, index) => {
      return sum + similarities[index] * normalizedWeights[index] * entry.weight;
    }, 0);
  }

  return entries.reduce((best, entry, index) => {
    return Math.max(best, similarities[index] * entry.weight);
  }, -Infinity);
}

function buildGlobalAverageScore(entries, queryVector) {
  const vectors = entries.map((entry) => entry.vector);
  const weights = entries.map((entry) => entry.weight);
  const averageVector = l2Normalize(weightedAverageVector(vectors, weights));
  return cosineSimilarity(averageVector, queryVector);
}

export async function loadSearchDataset() {
  const [manifestResponse, corpusResponse, metaResponse, binaryResponse] =
    await Promise.all([
      fetch("/search/manifest.json"),
      fetch("/search/corpus.json"),
      fetch("/search/embeddings.meta.json"),
      fetch("/search/embeddings.int8.bin"),
    ]);

  if (!manifestResponse.ok || !corpusResponse.ok || !metaResponse.ok || !binaryResponse.ok) {
    throw new Error("failed to load search assets");
  }

  const [manifestPayload, corpusPayload, metaPayload, binaryBuffer] =
    await Promise.all([
      manifestResponse.json(),
      corpusResponse.json(),
      metaResponse.json(),
      binaryResponse.arrayBuffer(),
    ]);

  const manifestMap = new Map(
    manifestPayload.images.map((item) => [item.image_id, item])
  );
  const corpusMap = new Map(corpusPayload.items.map((item) => [item.image_id, item]));
  const quantized = new Int8Array(binaryBuffer);
  const scale = metaPayload.format.scale;
  const dimension = metaPayload.format.dimension;

  const items = metaPayload.items.map((item) => {
    const manifestItem = manifestMap.get(item.image_id);
    const corpusItem = corpusMap.get(item.image_id);

    if (!manifestItem || !corpusItem) {
      throw new Error(`missing manifest/corpus item for ${item.image_id}`);
    }

    const entries = item.entries.map((entry, index) => {
      const offset = entry.byte_offset;
      const vectorSlice = quantized.subarray(offset, offset + dimension);
      const vector = Array.from(vectorSlice, (value) => value / scale);
      return {
        bucket: entry.bucket,
        weight: entry.weight,
        text: corpusItem.texts[index],
        vector,
      };
    });

    return {
      image_id: item.image_id,
      character: manifestItem.character,
      relative_path: manifestItem.relative_path,
      texts: corpusItem.texts,
      entries,
      entriesByBucket: new Map(
        BUCKET_ORDER.slice(0, 5).map((bucket) => [
          bucket,
          entries.filter((entry) => entry.bucket === bucket),
        ])
      ),
    };
  });

  return {
    manifest: manifestPayload,
    corpus: corpusPayload,
    meta: metaPayload,
    items,
    dimension,
  };
}

export function rankSearchResults(items, queryVector, modeWeights) {
  if (items.length > 0 && items[0].entries[0]?.vector.length !== queryVector.length) {
    throw new Error(
      `query embedding dimension ${queryVector.length} does not match index dimension ${items[0].entries[0].vector.length}`
    );
  }

  return items
    .map((item) => {
      const bucketScores = BUCKET_ORDER.slice(0, 5).map((bucket) =>
        bucketScore(item.entriesByBucket.get(bucket) || [], queryVector)
      );
      const globalScore = buildGlobalAverageScore(item.entries, queryVector);
      const scores = [...bucketScores, globalScore];
      const finalScore = scores.reduce(
        (sum, score, index) => sum + score * modeWeights[index],
        0
      );

      return {
        ...item,
        score: finalScore,
        scoreBreakdown: scores,
      };
    })
    .sort((left, right) => right.score - left.score);
}
