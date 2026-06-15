export const BUCKET_ORDER = [
  "objective_actions",
  "basic_emotions",
  "meme_phrases",
  "punchy_chat_quotes",
  "polite_replies",
  "global_weighted_average",
];

export const MODE_WEIGHTS = {
  polite: [0.2, 0.2, 0.1, 0.1, 0.3, 0.1],
  casual: [0.2, 0.2, 0.2, 0.2, 0.1, 0.1],
};

export const SOFTMAX_BUCKETS = new Set(["objective_actions", "basic_emotions"]);
export const SOFTMAX_TEMPERATURE = 0.5;
export const QUERY_MODEL_ID = "Xenova/bge-small-zh-v1.5";
