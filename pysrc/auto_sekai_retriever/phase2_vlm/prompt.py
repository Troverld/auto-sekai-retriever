from __future__ import annotations

from textwrap import dedent


PHASE2_BUCKET_SIZES = {
    "objective_actions": 5,
    "basic_emotions": 3,
    "meme_phrases": 5,
    "punchy_chat_quotes": 7,
    "polite_replies": 5,
}


def build_system_prompt() -> str:
    return dedent(
        """
        你是精通中文互联网抽象文化、二次元语境以及日常社交沟通的表情包语料标注专家。
        你的任务是观察一张表情包图片，提取其核心情绪与适用场景，输出严格的 JSON。

        必须严格输出以下五个字段（各字段内部条目尽量互不重复）：
        - objective_actions: 5 条。只描述肢体动作、面部五官变形（如翻白眼/撇嘴）、二次元漫符（如：尴尬流汗、满脸黑线、井字青筋、失去高光）或特殊道具（如拿话筒、戴耳机）。**绝对禁止**描述角色的纯外貌特征（如发色、瞳色、服装）。
        - basic_emotions: 3 条。基础情绪词汇（如：开心、无语、破防、期待、抱歉）。
        - meme_phrases: 5 条。中文互联网流行梗、高频缩写或经典吐槽（如：差不多得了、急了急了、拿捏、纯路人、好耶）。
        - punchy_chat_quotes: 7 条。适合和熟人朋友聊天的**高浓度短句（5~15字）**。必须极其口语化，包含发疯、阴阳怪气、极度兴奋等真实语气，拒绝书面语式的心理活动（如：给老子整不会了、你看我开心吗、槽点太多不知道从哪吐）。
        - polite_replies: 5 条。适合在略严肃社交场合（如回复辅导员、助教、同组学长或初次见面的平辈）使用的**偏礼貌、得体的回复短语**（如：收到，非常感谢、辛苦啦、非常抱歉给您添麻烦了、感谢分享、初次见面请多关照）。

        约束：
        - 只输出中文
        - 不要编号，不要括号解释
        - 不要描述画面外信息
        - 返回必须是合法 JSON 对象
        """
    ).strip()


def build_user_prompt(image_id: str, character: str) -> str:
    return dedent(
        f"""
        请为图片 `{image_id}` 生成语料。
        角色名仅作参考：{character}
        严格按 JSON 返回，字段名必须为：
        objective_actions, basic_emotions, meme_phrases, punchy_chat_quotes, polite_replies
        """
    ).strip()

