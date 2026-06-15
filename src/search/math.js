import { SOFTMAX_TEMPERATURE } from "./constants";

export function cosineSimilarity(left, right) {
  let dot = 0;
  let leftNorm = 0;
  let rightNorm = 0;

  for (let index = 0; index < left.length; index += 1) {
    const leftValue = left[index];
    const rightValue = right[index];
    dot += leftValue * rightValue;
    leftNorm += leftValue * leftValue;
    rightNorm += rightValue * rightValue;
  }

  if (leftNorm === 0 || rightNorm === 0) {
    return 0;
  }

  return dot / Math.sqrt(leftNorm * rightNorm);
}

export function softmaxWeights(weights, temperature = SOFTMAX_TEMPERATURE) {
  if (weights.length === 0) {
    return [];
  }

  const scaled = weights.map((weight) => weight / temperature);
  const maxValue = Math.max(...scaled);
  const exps = scaled.map((value) => Math.exp(value - maxValue));
  const total = exps.reduce((sum, value) => sum + value, 0);

  return exps.map((value) => value / total);
}

export function weightedAverageVector(vectors, weights) {
  if (vectors.length === 0) {
    return [];
  }

  const dimension = vectors[0].length;
  const result = new Float32Array(dimension);
  let weightTotal = 0;

  for (let index = 0; index < vectors.length; index += 1) {
    const vector = vectors[index];
    const weight = weights[index];
    weightTotal += weight;
    for (let inner = 0; inner < dimension; inner += 1) {
      result[inner] += vector[inner] * weight;
    }
  }

  if (weightTotal === 0) {
    return Array.from(result);
  }

  for (let index = 0; index < dimension; index += 1) {
    result[index] /= weightTotal;
  }

  return Array.from(result);
}

export function l2Normalize(vector) {
  let norm = 0;
  for (let index = 0; index < vector.length; index += 1) {
    norm += vector[index] * vector[index];
  }

  if (norm === 0) {
    return vector.slice();
  }

  const divisor = Math.sqrt(norm);
  return vector.map((value) => value / divisor);
}
